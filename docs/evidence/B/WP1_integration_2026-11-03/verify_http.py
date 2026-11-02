"""WP1 smoke: real HTTP + Vite proxy + frozen scorer, no training or learned run."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import os
import socket
import subprocess
import sys
import time
import zipfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT))
import httpx
from backend.contracts import EventsPage, Observation, RunResult
from backend.policies.learned import score_actions
from tests.test_api import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for port in (8000, 4179):
        with socket.socket() as check:
            check.bind(('127.0.0.1', port))
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    record = {'kind': 'WP1_synthetic_integration_not_AI_benchmark', 'checks': {}}
    try:
        for name, command, cwd in [
            ('backend', [sys.executable, '-m', 'uvicorn', 'backend.api.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1'], ROOT),
            ('frontend', ['node', 'node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '4179', '--strictPort'], ROOT / 'frontend'),
        ]:
            log = (output / (name + '.log')).open('wb')
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            processes.append((process, log))
        with httpx.Client(timeout=10.0) as client:
            for url in ('http://127.0.0.1:8000/openapi.json', 'http://127.0.0.1:4179/'):
                for attempt in range(100):
                    try:
                        response = client.get(url)
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if any(p.poll() is not None for p, _ in processes):
                        raise RuntimeError('Smoke server exited; inspect logs')
                    time.sleep(0.1)
                else:
                    raise RuntimeError('Smoke server startup timed out')
            record['checks']['frontend_html'] = '<html' in response.text
            base = 'http://127.0.0.1:4179'
            payload = request()
            response = client.post(base + '/runs', json=payload)
            assert response.status_code == 202, response.text
            identity = response.json()['run_id']
            path = '/runs/' + identity
            for attempt in range(300):
                state = client.get(base + path).json()
                if state['status'] in ('completed', 'failed'):
                    break
                time.sleep(0.1)
            assert state['status'] == 'completed', state
            response = client.get(base + path + '/results')
            response.raise_for_status()
            result = RunResult.model_validate(response.json())
            assert result.run_id == identity and result.seed == payload['seed']
            assert {p.policy_id for p in result.by_policy} == {'edf', 'value'}
            events, after, pages = [], 0, 0
            while True:
                response = client.get(base + path + '/events', params={'after': after, 'limit': 2})
                response.raise_for_status()
                page = EventsPage.model_validate(response.json())
                events.extend(e.model_dump() for e in page.events)
                pages += 1
                if not page.has_more:
                    break
                assert page.next_after > after
                after = page.next_after
            ids = [e['event_id'] for e in events]
            assert ids == sorted(set(ids)) and events
            assert all(e['run_id'] == identity for e in events)
            response = client.get(base + path + '/export')
            response.raise_for_status()
            (output / 'run.zip').write_bytes(response.content)
            with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
                assert json.loads(bundle.read('results.json')) == result.model_dump()
                zipped_events = [json.loads(line) for line in bundle.read('events.jsonl').splitlines()]
                assert zipped_events == events
                for prefix in ('', 'edf/', 'value/'):
                    manifest = json.loads(bundle.read(prefix + 'manifest.json'))
                    for name, digest in manifest['artifacts_sha256'].items():
                        assert hashlib.sha256(bundle.read(prefix + name)).hexdigest() == digest
            for policy in ('edf', 'value'):
                with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
                    assert json.loads(bundle.read(policy + '/config.json'))['seed'] == payload['seed']
            reject = client.post(base + '/runs', json={**payload, 'policy_ids': ['learned']})
            assert reject.status_code == 422
            record.update(run_id=identity, code_revision=result.code_revision, input_hash=result.input_hash,
                          event_count=len(events), event_pages=pages, seed=result.seed,
                          zip_sha256=hashlib.sha256(response.content).hexdigest())
            record['checks'].update(real_http=True, vite_proxy=True, completed_results=True,
                                    paging_matches_zip=True, artifact_hashes=True, child_seeds=True,
                                    learned_api_explicitly_unavailable=True)
        sample = json.loads((ROOT / 'data/teacher/a_n3_20_v2/samples.jsonl').read_text(encoding='utf-8').splitlines()[0])
        obs = Observation.model_validate(sample['observation'])
        scores = score_actions(obs)
        keys = {(s.task_id, s.mode) for s in scores}
        expected = {(t.task_id, m) for t in obs.tasks for m in ('robust', 'fast')} | {(None, 'idle')}
        assert keys == expected and len(keys) == len(scores)
        assert all(math.isfinite(s.score) for s in scores)
        record['checks']['frozen_model_complete_finite_scores'] = True
        package = ROOT / 'artifacts/models/a_n3_policy_v1'
        manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
        for name, digest in manifest['artifacts_sha256'].items():
            assert hashlib.sha256((package / name).read_bytes()).hexdigest() == digest
        record['checks']['frozen_model_hashes'] = True
        assert all(record['checks'].values())
    finally:
        for process, log in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            log.close()
        record['smoke_servers_stopped'] = all(p.poll() is not None for p, _ in processes)
        (output / 'verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
