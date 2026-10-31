"""One disposable process per comparison; no shared simulator or scorer state."""
import hashlib
import json
import time
from pathlib import Path

from backend.cli import _hash, _json_bytes
from backend.contracts import Event, RunRequest, RunResult, RunStatusResponse
from backend.policies.runner import run_policy


def publish(temporary, target):
    # Windows readers may briefly deny delete sharing during an atomic replacement.
    deadline=time.monotonic()+2.0
    while True:
        try:
            temporary.replace(target)
            return
        except PermissionError:
            if time.monotonic()>=deadline: raise
            time.sleep(.01)


def _write_json(path,value):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_bytes(_json_bytes(value))
    publish(temporary,path)


def read_text(path):
    deadline=time.monotonic()+2.0
    while True:
        try:return path.read_text(encoding='utf-8')
        except PermissionError:
            if time.monotonic()>=deadline:raise
            time.sleep(.01)


def write_status(folder, status, *, progress=None, active=None, error=None):
    value=RunStatusResponse(run_id=folder.name,status=status,progress=progress,
                            active_policies=active or [],error=error)
    _write_json(folder/'status.json',value.model_dump())


def fail_run(folder, reason):
    if (folder/'results.json').exists():
        (folder/'results.json').replace(folder/'results.partial.json')
    write_status(folder,'failed',error=dict(code='INTERNAL_RUN_ERROR',
        message='Run execution failed',details={'reason':reason}))


def execute_run(folder: Path, payload: dict):
    request=RunRequest.model_validate(payload)
    try:
        events=[];results=[]
        config=dict(request.config,seed=request.seed)
        for index,policy in enumerate(request.policy_ids):
            write_status(folder,'running',progress=index/len(request.policy_ids),active=[policy])
            result=run_policy(config,folder/policy,policy_id=policy,run_id=folder.name)
            results.append(result)
            for line in (folder/policy/'events.jsonl').read_text(encoding='utf-8').splitlines():
                event=Event.model_validate_json(line)
                event.event_id=len(events)+1
                events.append(event)
            # Whole completed policy batches are visible during a comparison.
            temporary=folder/'events.jsonl.tmp'
            temporary.write_text(''.join(e.model_dump_json()+'\n' for e in events),encoding='utf-8',newline='\n')
            publish(temporary,folder/'events.jsonl')
        base=results[0]
        result=RunResult(schema_version='1.0',run_id=folder.name,status='completed',
            config_hash=_hash(request.model_dump()),input_hash=base['input_hash'],
            model_hash=None,code_revision=base['code_revision'],seed=request.seed,
            by_policy=[r['by_policy'][0] for r in results],metric_definitions=base['metric_definitions'],
            artifact_paths={n:n for n in ('config.json','status.json','events.jsonl','results.json','manifest.json')})
        _write_json(folder/'results.json',result.model_dump())
        names=['config.json','events.jsonl','results.json']
        for policy in request.policy_ids:
            names += [f'{policy}/{n}' for n in ('config.json','manifest.json','status.json','results.json',
                      'events.jsonl','execution.log','energy_ledger.json')]
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        root=Path(__file__).resolve().parents[2]
        _write_json(folder/'manifest.json',dict(kind='synthetic_rule_comparison',
            run_id=folder.name,policy_ids=request.policy_ids,seed=request.seed,
            seed_semantics='Optional channel uses time-indexed draws; without channel seed is recorded only',
            config_hash=result.config_hash,input_hash=result.input_hash,code_revision=result.code_revision,
            source_sha256={p.relative_to(root).as_posix():sha(p) for p in sorted((root/'backend/api').glob('*.py'))},
            artifacts_sha256={n:sha(folder/n) for n in names},
            note='Status written last; manifest/status excluded from recursive hashes. No AI performance claim.'))
        write_status(folder,'completed',progress=1.0)
    except BaseException as error:
        fail_run(folder,type(error).__name__)
