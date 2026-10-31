import sys
from pathlib import Path
ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / 'pyproject.toml').is_file()
            and (parent / 'backend/api/main.py').is_file())
sys.path.insert(0,str(ROOT))
import hashlib,io,json,zipfile,time
from fastapi.testclient import TestClient
from backend.api.main import create_app
from tests.test_api import request

def main():
    output=ROOT/'runs/seed_p2_reproduction/actual';output.mkdir(parents=True,exist_ok=True)
    payload=request()
    with TestClient(create_app(output/'runs')) as c:
        response=c.post('/runs',json=payload);assert response.status_code==202
        identity=response.json()['run_id'];url='/runs/'+identity
        for _ in range(500):
            status=c.get(url).json()
            if status['status'] in ('completed','failed'):break
            time.sleep(.02)
        assert status['status']=='completed',status
        result=c.get(url+'/results').json()
        zipped=c.get(url+'/export');assert zipped.status_code==200
        with zipfile.ZipFile(io.BytesIO(zipped.content)) as z:
            for policy in ('edf','value'):
                for name in ('config.json','results.json','manifest.json'):
                    assert json.loads(z.read(f'{policy}/{name}'))['seed']==7
        folder=output/'runs'/identity
        for mf in [folder/'manifest.json',folder/'edf/manifest.json',folder/'value/manifest.json']:
            for name,digest in json.loads(mf.read_text())['artifacts_sha256'].items():
                assert hashlib.sha256((mf.parent/name).read_bytes()).hexdigest()==digest,name
        assert 'seed' not in payload['config']
        record=dict(run_id=identity,source_revision=result['code_revision'],seed=result['seed'],status='completed',
            child_seed_checked=True,zip_seed_checked=True,artifact_hashes_verified=True,request_unmodified=True,
            synthetic_only=True)
        (output/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record))
if __name__=='__main__':main()
