import io
import json
import os
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from backend.api.main import create_app
from backend.api.worker import execute_run
from backend.contracts import EventsPage, RunResult, RunStatusResponse
from tests.test_run_export import run_config


def request(policies=None):
    return dict(schema_version='1.0',config=run_config(actions=[]),policy_ids=policies or ['edf','value'],seed=7)


def test_internal_seed_conflict_rejected(tmp_path):
    payload=request(['edf']);payload['config']['seed']=8
    with TestClient(create_app(tmp_path/'runs')) as client:
        assert client.post('/runs',json=payload).status_code==422


def test_direct_seed_metadata_preserves_deterministic_physics(tmp_path):
    from backend.cli import RunConfig
    from backend.policies.runner import run_policy
    from pydantic import ValidationError
    from backend.simulator.channel import ChannelConfig
    config=run_config(actions=[])
    for invalid in (-1,1.5,True):
        with pytest.raises(ValidationError):RunConfig.model_validate(dict(config,seed=invalid))
    config['scenario']['channel']=ChannelConfig(seed=7).model_dump()
    with pytest.raises(ValidationError):RunConfig.model_validate(dict(config,seed=8))
    config['scenario'].pop('channel')
    outcomes=[]
    for seed in (0,7):
        folder=tmp_path/str(seed)
        result=run_policy(dict(config,seed=seed),folder,policy_id='edf')
        assert result['seed']==seed
        assert json.loads((folder/'manifest.json').read_text())['seed']==seed
        assert json.loads((folder/'config.json').read_text())['seed']==seed
        outcomes.append(result)
    assert outcomes[0]['config_hash']!=outcomes[1]['config_hash']
    assert outcomes[0]['input_hash']==outcomes[1]['input_hash']
    for key in ('weighted_on_time_rate','success_payload_bytes','goodput_bps','joule_per_success_bit'):
        assert outcomes[0]['by_policy'][0][key]==outcomes[1]['by_policy'][0][key]


def wait(client,identity):
    for _ in range(300):
        response=client.get('/runs/'+identity)
        if response.json()['status'] in ('completed','failed'):
            return response.json()
        time.sleep(.02)
    pytest.fail('worker did not finish')


def held_worker(folder,payload):
    while not (folder.parent/'release').exists(): time.sleep(.02)
    execute_run(folder,payload)


def crashed_worker(folder,payload): os._exit(9)


def test_real_comparison_paging_export_and_refresh(tmp_path):
    with TestClient(create_app(tmp_path/'runs')) as client:
        created=client.post('/runs',json=request())
        assert created.status_code==202 and created.json()['status']=='queued'
        identity=created.json()['run_id'];url='/runs/'+identity
        assert wait(client,identity)['status']=='completed'
        result=client.get(url+'/results').json();RunResult.model_validate(result)
        assert result['seed']==7
        assert [p['policy_id'] for p in result['by_policy']]==['edf','value']
        cursor=0;events=[]
        while True:
            response=client.get(url+'/events',params={'after':cursor,'limit':3})
            assert response.status_code==200
            page=EventsPage.model_validate(response.json());events+=page.events
            cursor=page.next_after
            if not page.has_more: break
        assert [e.event_id for e in events]==list(range(1,len(events)+1))
        assert {e.policy_id for e in events}=={'edf','value'}
        assert all(e.run_id==identity for e in events)
        assert client.get(url+'/events',params={'after':cursor}).json()['events']==[]
        assert client.get(url).json()['run_id']==identity
        (tmp_path/'runs'/identity/'private.txt').write_text('not exported')
        download=client.get(url+'/export');assert download.status_code==200
        with zipfile.ZipFile(io.BytesIO(download.content)) as package:
            assert 'results.json' in package.namelist()
            assert not any('private' in n or '..' in n or n.startswith('/') for n in package.namelist())
            assert json.loads(package.read('results.json'))==result
            for policy in ('edf','value'):
                for artifact in ('config.json','results.json','manifest.json'):
                    assert json.loads(package.read(f'{policy}/{artifact}'))['seed']==7
        again=client.post('/runs',json=request()).json()['run_id']
        assert again!=identity and wait(client,again)['status']=='completed'
        repeated=client.get('/runs/'+again+'/results').json()
        for left,right in zip(result['by_policy'],repeated['by_policy']):
            for key in ('weighted_on_time_rate','success_payload_bytes','goodput_bps','joule_per_success_bit'):
                assert left[key]==right[key]


def test_capacity_running_incomplete_validation_and_missing(tmp_path):
    with TestClient(create_app(tmp_path/'runs',worker=held_worker)) as client:
        identity=client.post('/runs',json=request()).json()['run_id'];url='/runs/'+identity
        RunStatusResponse.model_validate(client.get(url).json())
        assert client.post('/runs',json=request()).status_code==429
        for suffix in ('results','export'):
            response=client.get(url+'/'+suffix)
            assert response.status_code==409 and response.json()['code']=='RUN_NOT_COMPLETE'
        assert client.get(url+'/events').status_code==200
        assert client.get(url+'/events?after=-1').status_code==422
        assert client.get(url+'/events?limit=2001').status_code==422
        assert client.get('/runs/no_such_run').status_code==404
        for bad in (dict(request(),policy_ids=['edf','edf']),dict(request(),policy_ids=['learned']),dict(request(),config={} )):
            response=client.post('/runs',json=bad)
            assert response.status_code==422 and response.json()['code']=='INVALID_CONFIG'
        (tmp_path/'runs/release').touch()
        assert wait(client,identity)['status']=='completed'


def test_crashed_worker_is_failed_and_results_never_published(tmp_path):
    with TestClient(create_app(tmp_path/'runs',worker=crashed_worker)) as client:
        identity=client.post('/runs',json=request()).json()['run_id']
        status=wait(client,identity)
        assert status['status']=='failed' and status['error']['code']=='INTERNAL_RUN_ERROR'
        assert client.get('/runs/'+identity+'/results').status_code==409
        # A crashed run releases the sole capacity slot.
        assert client.post('/runs',json=request()).status_code==202


def test_timeout_kills_worker_and_restart_preserves_terminal_state(tmp_path):
    root=tmp_path/'runs'
    with TestClient(create_app(root,worker=held_worker,timeout_s=.2)) as client:
        identity=client.post('/runs',json=request()).json()['run_id']
        assert wait(client,identity)['status']=='failed'
    with TestClient(create_app(root)) as client:
        assert client.get('/runs/'+identity).json()['status']=='failed'


def test_export_path_containment(tmp_path):
    with TestClient(create_app(tmp_path/'runs')) as client:
        identity=client.post('/runs',json=request(['edf'])).json()['run_id']
        assert wait(client,identity)['status']=='completed'
        # Path containment is also enforced for an in-tree artifact pointing outside.
        from backend.api.service import checked_file
        folder=tmp_path/'runs'/identity
        with pytest.raises(ValueError): checked_file(folder,'../outside')


def test_linked_policy_directory_is_not_exported(tmp_path):
    import subprocess
    with TestClient(create_app(tmp_path/'runs')) as client:
        identity=client.post('/runs',json=request(['edf'])).json()['run_id']
        assert wait(client,identity)['status']=='completed'
        folder=tmp_path/'runs'/identity
        original=folder/'edf';outside=tmp_path/'outside'
        original.rename(outside)
        try: original.symlink_to(outside,target_is_directory=True)
        except OSError:
            assert os.name=='nt'
            result=subprocess.run(['cmd','/c','mklink','/J',str(original),str(outside)],capture_output=True)
            assert result.returncode==0
        response=client.get('/runs/'+identity+'/export')
        assert response.status_code==500 and response.json()['code']=='INTERNAL_RUN_ERROR'


def test_worker_exception_retains_failure_and_restart_marks_orphan(tmp_path,monkeypatch):
    import backend.api.worker as module
    from backend.cli import _write_json
    folder=tmp_path/('run_'+'a'*32);folder.mkdir()
    _write_json(folder/'config.json',request())
    def broken(*args,**kwargs): raise RuntimeError('simulated failure')
    monkeypatch.setattr(module,'run_policy',broken)
    execute_run(folder,request())
    assert json.loads((folder/'status.json').read_text())['status']=='failed'
    assert not (folder/'results.json').exists()
    module.write_status(folder,'running',active=['edf'])
    with TestClient(create_app(tmp_path)) as client:
        status=client.get('/runs/'+folder.name).json()
        assert status['status']=='failed' and status['error']['details']['reason']=='SERVICE_RESTARTED'


def test_immutable_request_and_simultaneous_submits(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    payload=request()
    with TestClient(create_app(tmp_path/'runs',worker=held_worker)) as client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:client.post('/runs',json=payload),range(2)))
        assert sorted(r.status_code for r in responses)==[202,429]
        identity=next(r.json()['run_id'] for r in responses if r.status_code==202)
        payload['seed']=99
        saved=json.loads((tmp_path/'runs'/identity/'config.json').read_text())
        assert saved['seed']==7
        assert not client.post('/runs',json=dict(request(),config=run_config())).status_code==202
        (tmp_path/'runs/release').touch()
        assert wait(client,identity)['status']=='completed'


def test_status_publish_retries_transient_windows_reader_lock(tmp_path,monkeypatch):
    from pathlib import Path
    from backend.api.worker import write_status
    folder=tmp_path/('run_'+'b'*32);folder.mkdir()
    original=Path.replace;calls=[]
    def locked_once(path,target):
        if path.name=='status.json.tmp' and not calls:
            calls.append(True)
            raise PermissionError('Windows reader sharing violation')
        return original(path,target)
    monkeypatch.setattr(Path,'replace',locked_once)
    write_status(folder,'running',active=['edf'])
    assert json.loads((folder/'status.json').read_text())['status']=='running'
    assert calls


def test_restart_recovers_directory_created_before_first_status(tmp_path):
    identity='run_'+'c'*32
    (tmp_path/identity).mkdir()
    with TestClient(create_app(tmp_path)) as client:
        status=client.get('/runs/'+identity).json()
        assert status['status']=='failed'
        assert status['error']['details']['reason']=='INCOMPLETE_RUN_RECORD'


def test_api_channel_seed_matches_request_seed(tmp_path):
    from backend.simulator.channel import ChannelConfig
    payload=request(['edf']);payload['config']['scenario']['channel']=ChannelConfig(seed=8).model_dump()
    with TestClient(create_app(tmp_path/'runs')) as client:
        assert client.post('/runs',json=payload).status_code==422
        payload['config']['scenario']['channel']['seed']=7
        created=client.post('/runs',json=payload)
        assert created.status_code==202
        identity=created.json()['run_id']
        assert wait(client,identity)['status']=='completed'
        assert client.get('/runs/'+identity+'/results').json()['seed']==7


def test_status_read_retries_windows_atomic_replace_lock(tmp_path,monkeypatch):
    from pathlib import Path
    from backend.api.worker import write_status
    folder=tmp_path/('run_'+'d'*32);folder.mkdir();write_status(folder,'completed',progress=1.0)
    with TestClient(create_app(tmp_path)) as client:
        original=Path.read_text;blocked=[]
        def locked_once(path,*args,**kwargs):
            if path.name=='status.json' and not blocked:
                blocked.append(True);raise PermissionError('replace sharing violation')
            return original(path,*args,**kwargs)
        monkeypatch.setattr(Path,'read_text',locked_once)
        assert client.get('/runs/'+folder.name).json()['status']=='completed'
        assert blocked
