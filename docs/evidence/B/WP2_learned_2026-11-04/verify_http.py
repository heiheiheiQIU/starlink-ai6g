"""Real learned five-API/proxy comparison; deterministic synthetic inputs only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT))
import httpx
from backend.api.processes import ProcessGroup
from backend.contracts import RunResult, EventsPage
from tests.test_api import request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output.resolve();output.mkdir(parents=True,exist_ok=False)
    for port in (8000,4179):
        with socket.socket() as probe: probe.bind(('127.0.0.1',port))
    (output/'server_app.py').write_text(
        'from backend.api.main import create_app\napp=create_app('+repr(str(output/'runs'))+')\n',encoding='utf-8')
    env=dict(os.environ,PYTHONPATH=str(output)+os.pathsep+str(ROOT))
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    processes=[];group=ProcessGroup();record={'kind':'synthetic_WP2_integration_not_formal_AI_benchmark','runs':[]}
    try:
        for name,command,cwd in [
            ('backend',[sys.executable,'-m','uvicorn','server_app:app','--host','127.0.0.1','--port','8000'],ROOT),
            ('frontend',['node','node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','4179','--strictPort'],ROOT/'frontend')]:
            log=(output/(name+'.log')).open('wb')
            process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
            processes.append((process,log));group.add(process)
        with httpx.Client(timeout=20) as client:
            for url in ('http://127.0.0.1:8000/openapi.json','http://127.0.0.1:4179/'):
                for _ in range(150):
                    try:
                        response=client.get(url)
                        if response.status_code==200: break
                    except httpx.TransportError: pass
                    assert all(p.poll() is None for p,_ in processes),'server exited'
                    time.sleep(.1)
                else: raise RuntimeError('HTTP startup timed out')
            base='http://127.0.0.1:4179'
            for policies in (['edf','value'],['edf','learned']):
                response=client.post(base+'/runs',json=request(policies));assert response.status_code==202,response.text
                identity=response.json()['run_id'];path='/runs/'+identity
                for _ in range(500):
                    status=client.get(base+path).json()
                    if status['status'] in ('completed','failed'):break
                    time.sleep(.02)
                assert status['status']=='completed',status
                response=client.get(base+path+'/results');response.raise_for_status()
                result=RunResult.model_validate(response.json());events=[];after=0;pages=0
                while True:
                    response=client.get(base+path+'/events',params={'after':after,'limit':2});response.raise_for_status()
                    page=EventsPage.model_validate(response.json());events.extend(e.model_dump() for e in page.events);pages+=1
                    if not page.has_more:break
                    assert page.next_after>after;after=page.next_after
                response=client.get(base+path+'/export');response.raise_for_status()
                raw=response.content;(output/(identity+'.zip')).write_bytes(raw)
                with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
                    assert json.loads(bundle.read('results.json'))==result.model_dump()
                    assert [json.loads(l) for l in bundle.read('events.jsonl').splitlines()]==events
                    for prefix in ['',*(p+'/' for p in policies)]:
                        manifest=json.loads(bundle.read(prefix+'manifest.json'))
                        for name,digest in manifest['artifacts_sha256'].items():
                            assert hashlib.sha256(bundle.read(prefix+name)).hexdigest()==digest
                    model=None;inference=None
                    if 'learned' in policies:
                        manifest=json.loads(bundle.read('learned/manifest.json'));model=manifest['model'];inference=manifest['inference']
                        assert inference['successful_model_decisions']>0
                        assert any(e['event_type']=='decision' and e['policy_id']=='learned' and
                                   e['data']['model_version']=='a-n3-mlp-v1' and not e['data']['fallback'] for e in events)
                record['runs'].append(dict(run_id=identity,policies=policies,input_hash=result.input_hash,
                    seed=result.seed,code_revision=result.code_revision,by_policy=[p.model_dump() for p in result.by_policy],
                    model=model,inference=inference,event_count=len(events),event_pages=pages,
                    zip_sha256=hashlib.sha256(raw).hexdigest()))
            assert len({r['input_hash'] for r in record['runs']})==1
            assert client.post(base+'/runs',json=request(['edf','value','learned'])).status_code==422
            record['paired_inputs']=True;record['max_two_policies_preserved']=True
            record['all_artifact_hashes_verified']=True;record['real_http_and_vite_proxy']=True
    finally:
        group.close()  # On Windows this also kills descendants on exceptional paths.
        for process,log in reversed(processes):
            if process.poll() is None:process.terminate()
            try:process.wait(5)
            except subprocess.TimeoutExpired:process.kill();process.wait(5)
            log.close()
        record['owned_servers_stopped']=all(p.poll() is not None for p,_ in processes)
        (output/'verification.json').write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'runs':[r['run_id'] for r in record['runs']], 'paired_inputs':True,
                      'successful_learned_decisions':record['runs'][1]['inference']['successful_model_decisions']},ensure_ascii=False))


if __name__=='__main__':main()
