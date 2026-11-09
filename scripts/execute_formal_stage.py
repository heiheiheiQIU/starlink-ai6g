"""Record wall time while invoking the original, frozen formal CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execution-root', type=Path, required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--stage', choices=['smoke', 'cell', 'coverage', 'full', 'retry', 'analysis'], required=True)
    args = parser.parse_args()
    execution = args.execution_root.resolve()
    root = args.run_root.resolve()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=execution, text=True).strip()
    if revision != '48157a8f4a1cdd7770685b79deb3fe4524b1bf7d':
        raise ValueError('Formal execution requires the registered frozen commit')
    manifest = root/'frozen/manifest.json'
    logs = root/'stage_logs'
    logs.mkdir(parents=True, exist_ok=True)
    if args.stage == 'analysis':
        command = [sys.executable, '-m', 'experiments.analyze_formal', '--manifest', str(manifest),
                   '--run-index', str(root/'batch/run_index.jsonl'), '--output', str(root/'analysis')]
    else:
        command = [sys.executable, '-m', 'backend.formal_experiments', '--manifest', str(manifest),
                   '--output', str(root/'batch'), '--stage', 'full' if args.stage == 'retry' else args.stage]
        if args.stage != 'smoke':
            command.append('--resume')
    started = time.perf_counter()
    with (logs/(args.stage+'.log')).open('wb') as stream:
        result = subprocess.run(command, cwd=execution, stdout=stream, stderr=subprocess.STDOUT)
    record = dict(stage=args.stage, command=command, execution_root=str(execution),
                  code_revision=revision, wall_seconds=time.perf_counter()-started, exit_code=result.returncode)
    (logs/(args.stage+'.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record))
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
