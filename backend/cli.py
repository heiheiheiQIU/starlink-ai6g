"""CPU-only single-policy synthetic validation runner. No HTTP or learned policy."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Literal
from uuid import uuid4

from pydantic import model_validator
from backend.contracts import Action, ContractModel, JsonValue, NonNegativeFloat, NonNegativeInt, PositiveFloat, RunResult, RunStatusResponse
from backend.evaluation import evaluate
from backend.simulator.engine import ScenarioConfig, create_state, step


class TimedAction(ContractModel):
    time_s: NonNegativeFloat
    action: Action


class RunConfig(ContractModel):
    schema_version: Literal['1.0']
    kind: Literal['manual_validation','rule_validation']
    scenario: ScenarioConfig
    evaluation_end_s: PositiveFloat
    actions: list[TimedAction]
    policy_runtime: dict[str,JsonValue] | None = None
    code_revision: str | None = None
    seed: NonNegativeInt | None = None

    @model_validator(mode='after')
    def executable_script(self):
        if self.seed is not None and self.scenario.channel is not None and self.seed != self.scenario.channel.seed:
            raise ValueError('run seed must equal channel.seed')
        if self.scenario.protocol is None:
            raise ValueError('Formal R3 run requires explicit protocol config')
        times = [a.time_s for a in self.actions]
        if any(t >= self.evaluation_end_s for t in times) or any(a >= b for a,b in zip(times,times[1:])):
            raise ValueError('Actions must increase strictly before evaluation end')
        return self


def _json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def _hash(value):
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _write_json(path: Path, value):
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def run_experiment(config: RunConfig | dict, output: Path, *, run_id: str | None = None,
                   _policy_id='manual', _executor=None, _runtime=None) -> dict:
    parsed = RunConfig.model_validate(config)
    if parsed.kind=='rule_validation' and _executor is None:
        raise ValueError('Use policy-run for automatic rule configurations')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output directory must be new or empty')
    output.mkdir(parents=True,exist_ok=True)
    identity = run_id if run_id is not None else 'r3_'+uuid4().hex
    state = create_state(parsed.scenario,run_id=identity,policy_id=_policy_id)
    config_data = parsed.model_dump()
    seed = parsed.seed if parsed.seed is not None else parsed.scenario.channel.seed if parsed.scenario.channel else 0
    config_data['seed'] = seed
    if _runtime is not None: config_data['policy_runtime']=_runtime
    def status(value,error=None):
        model = RunStatusResponse(run_id=identity,status=value,progress=1.0 if value=='completed' else None,
            active_policies=[_policy_id] if value=='running' else [],error=error)
        _write_json(output/'status.json',model.model_dump())
    events = []
    log = output/'execution.log'
    status('running')
    try:
        _write_json(output/'config.json',config_data)
        log.write_text('R4 synthetic validation started\n',encoding='utf-8',newline='\n')
        script = list(parsed.actions) if _executor is None else []
        if _executor is None and (not script or script[0].time_s > 0):
            script.insert(0,TimedAction(time_s=0.0,action=Action(task_id=None,mode='idle',scheduled_bytes=0,
                reason_codes=[],fallback=False)))
        for index,item in enumerate(script):
            end = script[index+1].time_s if index+1 < len(script) else parsed.evaluation_end_s
            result = step(state,item.action,end-item.time_s)
            state = result.next_state
            events.extend(result.events)
        if _executor is not None:
            state,events=_executor(state,parsed.evaluation_end_s)
        (output/'events.jsonl').write_text(''.join(e.model_dump_json()+'\n' for e in events),
            encoding='utf-8',newline='\n')
        _write_json(output/'energy_ledger.json',[asdict(row) for row in state.energy_ledger])
        metrics = evaluate(events,dict(scenario=parsed.scenario.model_dump(),
            evaluation_end_s=parsed.evaluation_end_s,policy_id=_policy_id))
        root = Path(__file__).resolve().parents[1]
        files = [root/'backend/contracts.py',root/'backend/evaluation.py',root/'backend/cli.py',
                 *sorted((root/'backend/simulator').glob('*.py'))]
        if _executor is not None: files.extend(sorted((root/'backend/policies').glob('*.py')))
        source_hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        try:
            if not (root/'.git').exists():
                raise OSError('Release root has no Git metadata')
            git = subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=False)
            revision = git.stdout.strip() if git.returncode == 0 else None
        except OSError:
            revision = None
        revision = revision or parsed.code_revision or 'unversioned-source-sha256:'+_hash(source_hashes)
        external = parsed.scenario.model_dump()
        config_hash,input_hash = _hash(config_data),_hash(external)
        definitions = dict(weighted_on_time_rate='Sum on-time complete task weights / all arrived due task weights',
            success_payload_bytes='Unique received payload bytes including partial tasks and late data',
            goodput_bps='Unique payload bits / evaluation_end_s',
            joule_per_success_bit='All satellite consumption J / unique received payload bits',
            energy_violation_count='Count of negative unclipped energy ledger segments; not independent episodes',
            pending_task_count='Arrived tasks with deadline after evaluation end, regardless of early receipt',
            details='docs/metrics.md; synthetic manual validation; no comparative performance claim')
        paths = {name:name for name in ('config.json','manifest.json','status.json','events.jsonl',
                                        'results.json','execution.log','energy_ledger.json')}
        result = RunResult(schema_version='1.0',run_id=identity,status='completed',config_hash=config_hash,
            input_hash=input_hash,model_hash=None,code_revision=revision,seed=seed,by_policy=[metrics],
            metric_definitions=definitions,artifact_paths=paths).model_dump()
        _write_json(output/'results.json',result)
        with log.open('a',encoding='utf-8',newline='\n') as stream:
            stream.write(f'validated {len(events)} events through {state.sim_time_s} seconds\n')
        manifest = dict(kind=parsed.kind,source='synthetic',run_id=identity,policy_id=_policy_id,
            seed=seed,
            protocol_stage='receive_ack_retry_dedup',is_real_satellite_measurement=False,
            is_policy_benchmark=False,config_hash=config_hash,input_hash=input_hash,trace_hash=_hash(external),
            channel=parsed.scenario.channel.model_dump() if parsed.scenario.channel else None,
            model_hash=None,policy_version=_runtime['policy_version'] if _runtime else 'manual-r3-v1',code_revision=revision,
            source_sha256=source_hashes,
            artifacts_sha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in
                ('config.json','events.jsonl','results.json','energy_ledger.json','execution.log')},
            status_hash_note='status written last; manifest and status excluded from self-referential hashes')
        _write_json(output/'manifest.json',manifest)
        # Successful status is the final write, after all required artifacts validate.
        status('completed')
        return result
    except BaseException as error:
        if (output/'results.json').exists():
            (output/'results.json').replace(output/'results.partial.json')
        with log.open('a',encoding='utf-8',newline='\n') as stream:
            stream.write(f'failed: {type(error).__name__}\n')
        status('failed',dict(code='INTERNAL_RUN_ERROR',message='Run execution failed',
                            details={'exception_type':type(error).__name__}))
        raise


def main():
    parser = argparse.ArgumentParser(description='R3 synthetic manual protocol validation')
    commands = parser.add_subparsers(dest='command',required=True)
    command = commands.add_parser('run')
    command.add_argument('--config',type=Path,required=True)
    command.add_argument('--output',type=Path,required=True)
    rule=commands.add_parser('policy-run')
    rule.add_argument('--config',type=Path,required=True)
    rule.add_argument('--policy',choices=['edf','value'],required=True)
    rule.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    if args.command=='policy-run':
        from backend.policies.runner import run_policy
        result=run_policy(config,args.output,policy_id=args.policy)
    else: result=run_experiment(config,args.output)
    print(json.dumps(dict(run_id=result['run_id'],status=result['status']),ensure_ascii=False))


if __name__ == '__main__':
    main()
