"""B local engineering probe: real sockets/processes; development inputs only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import zipfile

import httpx


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def verify_zip(raw, policies, expected_input):
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        names=bundle.namelist()
        assert len(names)==len(set(names))
        for name in names:
            assert not name.startswith(('/', '\\')) and '..' not in Path(name).parts
        meta=json.loads(bundle.read('manifest.json'))
        for name,digest in meta['artifacts_sha256'].items():
            assert hashlib.sha256(bundle.read(name)).hexdigest()==digest,name
        for policy in policies:
            child=json.loads(bundle.read(policy+'/manifest.json'))
            assert child['input_hash']==expected_input
            for name,digest in child['artifacts_sha256'].items():
                assert hashlib.sha256(bundle.read(policy+'/'+name)).hexdigest()==digest
        return dict(files=len(names),root_hashed_files=len(meta['artifacts_sha256']),zip_sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--proxy',action='store_true')
    parser.add_argument('--without-git',action='store_true')
    args=parser.parse_args(); root=args.workspace.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONIOENCODING']='utf-8'
    if args.without_git: env['PATH']=str(args.python.resolve().parent)
    with socket.socket() as check:check.bind(('127.0.0.1',args.port))
    log=(out/'server.log').open('w',encoding='utf-8');process=None;proxy=None;proxy_log=None
    checks=[]
    try:
        process=subprocess.Popen([str(args.python.resolve()),'-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port',str(args.port),'--workers','1'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        base=f'http://127.0.0.1:{args.port}'
        with httpx.Client(base_url=base,timeout=10,trust_env=False) as client:
            for _ in range(150):
                if process.poll() is not None: raise RuntimeError('API process exited; see server.log')
                try:
                    if client.get('/openapi.json').status_code==200:break
                except httpx.TransportError:pass
                time.sleep(.1)
            else:raise TimeoutError('API startup')
            if args.proxy:
                assert args.port==8000
                node=__import__('shutil').which('node');assert node
                proxy_log=(out/'proxy.log').open('w',encoding='utf-8')
                proxy=subprocess.Popen([node,str(root/'frontend/node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port','4178','--strictPort'],cwd=root/'frontend',stdout=proxy_log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                for _ in range(100):
                    try:
                        if httpx.get('http://127.0.0.1:4178',trust_env=False).status_code==200:break
                    except httpx.TransportError:pass
                    time.sleep(.1)
                else:raise TimeoutError('Vite preview startup')
            config=json.loads((root/'configs/scenarios/r3_normal.json').read_text(encoding='utf-8'))
            config['actions']=[]
            scenario_seed=config['scenario'].get('channel',{}).get('seed',7)
            for policies in [('edf','value'),('edf','learned')]:
                payload=dict(schema_version='1.0',config=config,policy_ids=list(policies),seed=scenario_seed)
                if args.proxy:
                    response=httpx.post('http://127.0.0.1:4178/runs',json=payload,trust_env=False,timeout=15)
                else:response=client.post('/runs',json=payload)
                assert response.status_code==202,response.text
                identity=response.json()['run_id'];path='/runs/'+identity
                write(out/(identity+'_request.json'),payload)
                before=client.get(path+'/results');assert before.status_code in (200,409)
                for _ in range(300):
                    state=client.get(path).json()
                    if state['status'] in ('completed','failed'):break
                    time.sleep(.05)
                assert state['status']=='completed',state
                result=client.get(path+'/results');assert result.status_code==200
                data=result.json();assert {r['policy_id'] for r in data['by_policy']}==set(policies)
                assert client.get(path).json()['run_id']==identity
                # Re-open a client to emulate reconnect by run_id without creating another run.
                with httpx.Client(base_url=base,trust_env=False) as reconnect:
                    assert reconnect.get(path).json()['status']=='completed'
                events=[];after=0;pages=0
                while True:
                    response=client.get(path+'/events',params={'after':after,'limit':3});assert response.status_code==200
                    page=response.json();events+=page['events'];pages+=1
                    if not page['has_more']:break
                    assert page['next_after']>after;after=page['next_after']
                ids=[e['event_id'] for e in events];assert ids==sorted(set(ids))
                assert set(e['policy_id'] for e in events)==set(policies)
                raw=client.get(path+'/export');assert raw.status_code==200
                verified=verify_zip(raw.content,policies,data['input_hash'])
                (out/(identity+'.zip')).write_bytes(raw.content)
                write(out/(identity+'_results.json'),data);write(out/(identity+'_events.json'),events)
                if 'learned' in policies:
                    assert any(e['event_type']=='decision' and e['policy_id']=='learned' and not e['data']['fallback'] for e in events)
                    model=next(r['model_hash'] for r in data['by_policy'] if r['policy_id']=='learned');assert len(model)==64
                if args.without_git:assert data['code_revision'].startswith('unversioned-source-sha256:')
                checks.append(dict(policies=policies,run_id=identity,input_hash=data['input_hash'],code_revision=data['code_revision'],events=len(events),pages=pages,export=verified))
            assert len({r['input_hash'] for r in checks})==1
            assert client.get('/runs/run_'+'0'*32).status_code==404
            assert client.get(path+'/events',params={'after':-1}).status_code==422
            assert client.post('/runs',json=dict(payload,policy_ids=['edf','value','learned'])).status_code==422
            if args.without_git:
                weights=root/'artifacts/models/a_n3_policy_v1/weights.npz';backup=weights.read_bytes()
                faults=[]
                try:
                    for mode in ('missing','corrupt'):
                        if weights.exists():weights.unlink()
                        if mode=='corrupt':weights.write_bytes(b'PK\x03\x04broken-local-acceptance')
                        response=client.post('/runs',json=dict(payload,policy_ids=['learned']))
                        assert response.status_code==422,response.text
                        assert response.json()['details']['reason']=='MODEL_UNAVAILABLE'
                        faults.append(dict(mode=mode,http_status=422,body=response.json()))
                finally:weights.write_bytes(backup)
                write(out/'model_faults.json',faults)
            write(out/'verification.json',dict(status='passed',scope='local_development_HTTP_not_formal',without_git=args.without_git,via_vite_proxy=args.proxy,runs=checks,checks=['real HTTP creation/status/results','small-page event completeness','reconnect read-only by run_id','ZIP root and child SHA verification','invalid input and unknown run rejection'],limitations=['No browser visual or click acceptance','No other physical machine','No formal holdout inputs used']))
    finally:
        for child in (proxy,process):
            if child is not None and child.poll() is None:
                child.terminate()
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        log.close()
        if proxy_log:proxy_log.close()


if __name__=='__main__':main()
