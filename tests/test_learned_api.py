import io
import json
import time
import zipfile

from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.service import RunService
from tests.test_api import request, wait


def test_learned_five_interfaces_pairing_and_model_identity(tmp_path):
    app = create_app(tmp_path/'runs')
    with TestClient(app) as client:
        payload = request(['edf','learned'])
        created = client.post('/runs', json=payload)
        assert created.status_code == 202, created.text
        identity = created.json()['run_id']; path = '/runs/'+identity
        state = wait(client, identity)
        assert state['status'] == 'completed', state
        result = client.get(path+'/results').json()
        assert result['model_hash'] is None
        by = {r['policy_id']: r for r in result['by_policy']}
        assert by['edf']['model_hash'] is None and len(by['learned']['model_hash']) == 64
        events=[]; after=0
        while True:
            page=client.get(path+'/events', params={'after':after,'limit':2}).json()
            events.extend(page['events'])
            if not page['has_more']: break
            assert page['next_after']>after
            after=page['next_after']
        scores = [e['data'] for e in events if e['policy_id']=='learned' and e['event_type']=='decision']
        assert any(d['model_version']=='a-n3-mlp-v1' and not d['fallback'] for d in scores)
        exported=client.get(path+'/export'); assert exported.status_code==200
        with zipfile.ZipFile(io.BytesIO(exported.content)) as bundle:
            hashes=[]
            for policy in ('edf','learned'):
                child=json.loads(bundle.read(policy+'/results.json')); hashes.append(child['input_hash'])
                assert child['seed']==payload['seed']
            assert len(set(hashes))==1
            manifest=json.loads(bundle.read('learned/manifest.json'))
            assert manifest['inference']['successful_model_decisions']>0
            assert manifest['model_hash']==by['learned']['model_hash']
        assert client.post('/runs', json=request(['edf','value','learned'])).status_code==422
    assert not app.state.service.jobs and not app.state.service.inference_jobs


def test_learned_only_common_model_hash(tmp_path):
    with TestClient(create_app(tmp_path/'runs')) as client:
        response=client.post('/runs',json=request(['learned']));assert response.status_code==202
        identity=response.json()['run_id'];assert wait(client,identity)['status']=='completed'
        result=client.get('/runs/'+identity+'/results').json()
        assert result['model_hash']==result['by_policy'][0]['model_hash']


def test_missing_server_model_rejected_before_run_created(tmp_path):
    service=RunService(tmp_path/'runs', model_config={'enabled': False})
    try:
        try: service.submit(request(['learned']))
        except ValueError: pass
        else: raise AssertionError('Invalid model must reject submit')
        assert not list((tmp_path/'runs').iterdir())
    finally: service.close()


def test_inference_timeout_falls_back_but_run_completes_and_process_dies(tmp_path):
    from functools import partial
    from backend.api.inference import InferenceSupervisor
    from backend.api.processes import pid_alive
    from tests.test_inference_lifecycle import hanging_score
    service=RunService(tmp_path/'runs', inference_factory=partial(InferenceSupervisor,scorer=hanging_score,budget_ms=20))
    service.start()
    try:
        identity=service.submit(request(['learned']))['run_id']
        pid=service.inference_jobs[identity].process.pid
        for _ in range(500):
            service.reap(); state=service.status(identity)
            if state['status'] in ('completed','failed'): break
            time.sleep(.01)
        assert state['status']=='completed'
        events=[json.loads(l) for l in (service.root/identity/'events.jsonl').read_text().splitlines()]
        decisions=[e['data'] for e in events if e['event_type']=='decision']
        assert 'MODEL_TIMEOUT' in decisions[0]['action']['reason_codes']
        assert all(d['fallback'] for d in decisions)
        assert not pid_alive(pid)
        manifest=json.loads((service.root/identity/'learned/manifest.json').read_text())
        assert manifest['inference']['fallback_count']==len(decisions)
    finally: service.close()


def test_service_close_and_run_timeout_reap_both_processes(tmp_path):
    from backend.api.processes import pid_alive
    from tests.test_api import held_worker
    for case in ('close','timeout'):
        service=RunService(tmp_path/case,worker=held_worker,timeout_s=.2 if case=='timeout' else 20)
        service.start()
        identity=service.submit(request(['learned']))['run_id']
        pids=[service.jobs[identity][0].pid,service.inference_jobs[identity].process.pid]
        try:
            if case=='timeout':
                for _ in range(200):
                    service.reap()
                    if service.status(identity)['status']=='failed': break
                    time.sleep(.01)
                assert service.status(identity)['error']['details']['reason']=='WORKER_TIMEOUT'
            else: service.close()
            assert all(not pid_alive(pid) for pid in pids)
        finally: service.close()


def test_cleanup_survives_persistent_status_read_failure(tmp_path, monkeypatch):
    import pytest
    from backend.api.processes import pid_alive
    from tests.test_api import held_worker
    service=RunService(tmp_path/'runs', worker=held_worker)
    identity=service.submit(request(['learned']))['run_id']
    pids=[service.jobs[identity][0].pid,service.inference_jobs[identity].process.pid]
    def denied(identity): raise PermissionError('persistent status sharing violation')
    monkeypatch.setattr(service,'status',denied)
    with pytest.raises(PermissionError): service.close()
    assert not service.jobs and not service.inference_jobs
    assert all(not pid_alive(pid) for pid in pids)


def test_worker_crash_reaps_inference_and_never_publishes_results(tmp_path):
    from backend.api.processes import pid_alive
    from tests.test_api import crashed_worker
    service=RunService(tmp_path/'runs',worker=crashed_worker)
    identity=service.submit(request(['learned']))['run_id']
    pid=service.inference_jobs[identity].process.pid
    try:
        for _ in range(300):
            service.reap()
            if service.status(identity)['status']=='failed': break
            time.sleep(.01)
        assert service.status(identity)['status']=='failed'
        assert not (service.root/identity/'results.json').exists()
        assert not pid_alive(pid)
    finally: service.close()

