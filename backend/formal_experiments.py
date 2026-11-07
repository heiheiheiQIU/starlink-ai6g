"""Paired runs with an append-only attempt journal and immutable input envelope."""
import argparse
from collections import defaultdict
from contextlib import contextmanager
import json
import os
from pathlib import Path
from uuid import uuid4

from backend.api.inference import InferenceSupervisor
from backend.formal_freeze import (POLICIES, file_hash, frozen_model_config, local_file,
                                   read_json, verify_frozen, write_json)
from backend.policies.runner import run_policy


@contextmanager
def _batch_lock(root):
    # OS-held locks disappear on process termination; no stale-lock deletion.
    with (root/'.writer.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0: stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error: raise ValueError('Batch already has an active writer') from error
        else:
            import fcntl
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error: raise ValueError('Batch already has an active writer') from error
        try: yield
        finally:
            stream.seek(0)
            if os.name == 'nt': msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(stream, fcntl.LOCK_UN)


def _append(path, record):
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False)+'\n')
        stream.flush(); os.fsync(stream.fileno())


def _artifacts(folder):
    if not folder.exists(): return {}
    return {p.relative_to(folder).as_posix(): file_hash(local_file(folder, p.relative_to(folder).as_posix()))
            for p in sorted(folder.rglob('*')) if p.is_file()}


def _load_index(frozen, manifest_path, path):
    root = path.parent
    batch = read_json(root/'batch.json')
    if (batch.get('schema_version') != 'formal-batch-v1'
            or batch.get('frozen_manifest_sha256') != file_hash(manifest_path)
            or batch.get('data_scope') != frozen['data_scope']):
        raise ValueError('Batch binding mismatch')
    trajectories = {r['trajectory_id']: r for r in frozen['trajectories']}
    started, ended = {}, {}
    if not path.exists(): raise ValueError('Run index missing')
    try:
        records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    except (ValueError, UnicodeError) as error:
        raise ValueError('Truncated or invalid run journal; preserve and inspect before recovery') from error
    for row in records:
        trace = trajectories.get(row.get('trajectory_id'))
        policy = row.get('policy_id'); attempt = row.get('attempt')
        if trace is None or policy not in POLICIES or type(attempt) is not int or attempt not in (1, 2):
            raise ValueError('Unknown run identity')
        key = (row['trajectory_id'], policy, attempt)
        expected = dict(trajectory_id=trace['trajectory_id'], cell_id=trace['cell_id'], seed=trace['seed'],
                        policy_id=policy, attempt=attempt, input_hash=trace['input_hash'],
                        model_hash=frozen['binding']['model_artifacts_sha256']['weights.npz'] if policy == 'learned' else None,
                        run_id=f'{batch["batch_id"]}_{trace["trajectory_id"]}_{policy}_{attempt}',
                        run_path=f'runs/{trace["trajectory_id"]}/{policy}/attempt_{attempt}')
        if any(row.get(k) != v for k, v in expected.items()): raise ValueError('Run identity mismatch')
        if row.get('status') == 'started':
            if key in started: raise ValueError('Duplicate started attempt')
            prior = (key[0], key[1], attempt-1)
            if attempt == 2 and (prior not in ended or ended[prior]['status'] == 'completed'):
                raise ValueError('Retry without failed prior attempt')
            started[key] = row
        elif row.get('status') in ('completed', 'failed', 'interrupted'):
            if key not in started or key in ended: raise ValueError('Duplicate or unstarted terminal attempt')
            folder = root/row['run_path']
            if _artifacts(folder) != row.get('artifacts_sha256'): raise ValueError('Run artifact hash mismatch')
            if row['status'] == 'completed':
                required = {'results.json', 'manifest.json', 'events.jsonl', 'energy_ledger.json', 'config.json', 'status.json', 'execution.log'}
                if not required <= set(row['artifacts_sha256']): raise ValueError('Incomplete successful run')
                result = read_json(folder/'results.json'); meta = read_json(folder/'manifest.json')
                status = read_json(folder/'status.json')
                metrics = result['by_policy']
                if (status.get('status') != 'completed' or result.get('status') != 'completed'
                        or len(metrics) != 1 or metrics[0]['policy_id'] != policy
                        or result['run_id'] != expected['run_id'] or result['input_hash'] != expected['input_hash']
                        or result['model_hash'] != expected['model_hash'] or result['seed'] != trace['seed']
                        or meta['input_hash'] != expected['input_hash'] or meta['policy_id'] != policy
                        or meta['config_hash'] != result['config_hash']):
                    raise ValueError('Successful result identity mismatch')
                for name, digest in meta['artifacts_sha256'].items():
                    if file_hash(local_file(folder, name)) != digest: raise ValueError('Run manifest mismatch')
            ended[key] = row
        else: raise ValueError('Invalid journal status')
    # A truncated journal must not silently orphan existing attempts.
    actual_dirs = {p.relative_to(root).as_posix() for p in (root/'runs').glob('*/*/attempt_*')}
    if not actual_dirs <= {r['run_path'] for r in started.values()}: raise ValueError('Unindexed run directory')
    return batch, started, ended


def read_run_index(manifest_path: Path, run_index: Path) -> list[dict]:
    frozen = verify_frozen(manifest_path)
    _, started, ended = _load_index(frozen, manifest_path, Path(run_index))
    return [ended.get(key, row) for key, row in sorted(started.items())]


def _summary(frozen, rows):
    completed = {(r['trajectory_id'], r['policy_id']) for r in rows if r['status'] == 'completed'}
    touched = {(r['trajectory_id'], r['policy_id']) for r in rows}
    return dict(status='runs_complete' if len(completed) == 540 else 'incomplete',
                data_scope=frozen['data_scope'], expected_policy_runs=540,
                completed_policy_runs=len(completed), missing_policy_runs=540-len(touched),
                failed_policy_runs=len(touched-completed), attempt_count=len(rows),
                formal_verdict='未完成', result_signoff='pending')


def run_formal(manifest_path: Path, output: Path, *, trajectory_ids: list[str] | None = None,
               resume: bool = False) -> dict:
    manifest_path = Path(manifest_path); output = Path(output)
    frozen = verify_frozen(manifest_path)
    traces = {r['trajectory_id']: r for r in frozen['trajectories']}
    selected = sorted(traces) if trajectory_ids is None else trajectory_ids
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(traces):
        raise ValueError('Expected unique known trajectory selection')
    selected = sorted(selected)
    if resume:
        if not output.is_dir(): raise ValueError('Resume requires existing batch')
    else:
        output.mkdir(parents=True, exist_ok=False)
    with _batch_lock(output):
        index = output/'run_index.jsonl'
        if not resume:
            write_json(output/'batch.json', dict(schema_version='formal-batch-v1', batch_id='formal_'+uuid4().hex,
                       frozen_manifest_sha256=file_hash(manifest_path), data_scope=frozen['data_scope']))
            index.touch(exist_ok=False)
        batch, started, ended = _load_index(frozen, manifest_path, index)
        for key, record in started.items():
            if key not in ended:
                terminal = dict(record, status='interrupted', error_type='InterruptedAttempt',
                                artifacts_sha256=_artifacts(output/record['run_path']))
                _append(index, terminal); ended[key] = terminal
        for identity in selected:
            trace = traces[identity]
            for policy in POLICIES:
                prior = [r for key, r in ended.items() if key[:2] == (identity, policy)]
                if any(r['status'] == 'completed' for r in prior) or len(prior) >= 2: continue
                attempt = len(prior)+1
                run_id = f'{batch["batch_id"]}_{identity}_{policy}_{attempt}'
                path = f'runs/{identity}/{policy}/attempt_{attempt}'
                record = dict(trajectory_id=identity, cell_id=trace['cell_id'], seed=trace['seed'],
                              policy_id=policy, attempt=attempt, input_hash=trace['input_hash'],
                              model_hash=frozen['binding']['model_artifacts_sha256']['weights.npz'] if policy == 'learned' else None,
                              run_id=run_id, run_path=path, status='started')
                _append(index, record)
                config = read_json(local_file(manifest_path.parent/'candidate', trace['config_path']))
                try:
                    if policy == 'learned':
                        with InferenceSupervisor(model_config=frozen_model_config(manifest_path.parent), identity=run_id) as owner:
                            run_policy(config, output/path, policy_id=policy, run_id=run_id,
                                       inference_client=owner.client, model_metadata=owner.metadata,
                                       inference_load_ms=owner.load_ms)
                    else: run_policy(config, output/path, policy_id=policy, run_id=run_id)
                    terminal = dict(record, status='completed', artifacts_sha256=_artifacts(output/path))
                except Exception as error:
                    terminal = dict(record, status='failed', error_type=type(error).__name__,
                                    artifacts_sha256=_artifacts(output/path))
                _append(index, terminal); ended[(identity, policy, attempt)] = terminal
        # Detect invalid outputs immediately rather than accepting an in-memory return.
        _, _, ended = _load_index(frozen, manifest_path, index)
        summary = _summary(frozen, list(ended.values()))
        write_json(output/'batch_status.json', summary)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['smoke', 'cell', 'coverage', 'full'], default='smoke')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    traces = verify_frozen(args.manifest)['trajectories']
    selectors = dict(smoke=[traces[0]['trajectory_id']], cell=[r['trajectory_id'] for r in traces[:10]],
                     coverage=[r['trajectory_id'] for r in traces[::10]], full=[r['trajectory_id'] for r in traces])
    print(json.dumps(run_formal(args.manifest, args.output, trajectory_ids=selectors[args.stage], resume=args.resume), ensure_ascii=False))


if __name__ == '__main__': main()
