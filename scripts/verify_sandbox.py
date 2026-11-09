"""Run real HTTP golden scenes, health pair and deterministic replay verification."""
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import httpx

from backend.sandbox import GOLDEN_AXES, compile_sandbox_axes
from backend.simulator.engine import create_state, observe


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def semantic(events):
    rows = json.loads(json.dumps(events))
    for row in rows:
        row.pop('run_id')
        if row['event_type'] == 'decision':
            row['data'].pop('latency_ms', None)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8019)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    log = (out/'server.log').open('w', encoding='utf-8')
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.api.main:app',
        '--host', '127.0.0.1', '--port', str(args.port), '--workers', '1'],
        cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = []
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{args.port}', trust_env=False, timeout=30) as client:
            for _ in range(150):
                if server.poll() is not None:
                    raise RuntimeError('Server exited')
                try:
                    if client.get('/openapi.json').status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise TimeoutError('Server startup')
            scenes = dict(GOLDEN_AXES, health_control=dict(GOLDEN_AXES['S2'], health='healthy'),
                          S3_repeat=GOLDEN_AXES['S3'])
            for name, axes in scenes.items():
                started = time.perf_counter()
                payload = dict(schema_version='1.0', seed=7, policy_ids=['edf', 'learned'],
                    config=dict(kind='sandbox_axes', compiler_version='sandbox-axis-v1', axes=axes))
                response = client.post('/runs', json=payload)
                assert response.status_code == 202, response.text
                identity = response.json()['run_id']
                url = '/runs/'+identity
                cursor = 0
                events = []
                running_partial = False
                while time.perf_counter()-started < 120:
                    status = client.get(url).json()
                    while True:
                        page = client.get(url+'/events', params=dict(after=cursor, limit=7)).json()
                        events.extend(page['events'])
                        cursor = page['next_after']
                        if not page['has_more']:
                            break
                    if status['status'] == 'running' and events:
                        running_partial = True
                    if status['status'] in ('completed','failed','cancelled'):
                        break
                    time.sleep(0.01)
                assert status['status'] == 'completed', status
                # Final drain after completion publication.
                while True:
                    page = client.get(url+'/events', params=dict(after=cursor, limit=7)).json()
                    events.extend(page['events'])
                    cursor = page['next_after']
                    if not page['has_more']:
                        break
                assert [e['event_id'] for e in events] == list(range(1,len(events)+1))
                result = client.get(url+'/results').json()
                export = client.get(url+'/export')
                assert export.status_code == 200, export.text
                raw = export.content
                with zipfile.ZipFile(io.BytesIO(raw)) as package:
                    manifest = json.loads(package.read('manifest.json'))
                    for path, digest in manifest['artifacts_sha256'].items():
                        assert hashlib.sha256(package.read(path)).hexdigest() == digest
                    exported = [json.loads(line) for line in package.read('events.jsonl').splitlines()]
                    assert exported == events
                    assert json.loads(package.read('config.json')) == payload
                    assert json.loads(package.read('compiled_config.json')) == compile_sandbox_axes(axes,7)
                folder = out/name
                folder.mkdir()
                (folder/'export.zip').write_bytes(raw)
                write(folder/'request.json',payload)
                write(folder/'results.json',result)
                write(folder/'events.json',events)
                write(folder/'initial_observation.json',
                      observe(create_state(compile_sandbox_axes(axes,7)['scenario'])).model_dump())
                rows.append(dict(scene=name,run_id=identity,input_hash=result['input_hash'],
                    config_hash=result['config_hash'],wall_seconds=time.perf_counter()-started,
                    events=len(events),types=dict(Counter(e['event_type'] for e in events)),
                    reasons=dict(Counter(e['reason_code'] for e in events if e['reason_code'])),
                    running_partial_observed=running_partial,zip_bytes=len(raw),
                    zip_sha256=hashlib.sha256(raw).hexdigest(),metrics=result['by_policy']))
            assert len({r['input_hash'] for r in rows[:3]}) == 3
            s3 = json.loads((out/'S3/events.json').read_text(encoding='utf-8'))
            assert any(e['reason_code'] == 'ACK_TIMEOUT' for e in s3)
            assert any(e['reason_code'] == 'DUPLICATE_BLOCK' for e in s3), {e['reason_code'] for e in s3}
            repeat = json.loads((out/'S3_repeat/events.json').read_text(encoding='utf-8'))
            assert semantic(s3) == semantic(repeat)
            write(out/'verification.json',dict(status='passed',scope='synthetic_sandbox',
                semantic_replay='same events excluding run_id and measured decision latency',
                runs=rows))
            print(json.dumps(rows,ensure_ascii=False,indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        log.close()


if __name__ == '__main__':
    main()

