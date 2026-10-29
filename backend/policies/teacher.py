"""Budgeted exact tree enumeration on the public zero-loss forecast model.

Scores are feasible incumbent utility lower bounds unless status is OPTIMAL.
This is an auditable small-case teacher, not a MILP/CP-SAT implementation.
"""
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
import math
import subprocess
from pathlib import Path
from time import perf_counter as _clock, process_time
from typing import Annotated
from pydantic import Field
from backend.contracts import (Action, ContractModel, ContractViolation, Observation,
    TeacherCandidateScore, TeacherResult, validate_teacher_result)
from backend.simulator.engine import ScenarioConfig, create_state, observe, step
from .common import PolicyConfig, plan_candidate, settings


class TeacherConfig(ContractModel):
    version: str = 'bounded-forecast-r4-v1'
    policy: PolicyConfig = Field(default_factory=settings)
    max_tasks: Annotated[int,Field(ge=1,le=12)] = 12
    max_steps: Annotated[int,Field(ge=1,le=120)] = 120
    max_windows: Annotated[int,Field(ge=1,le=3)] = 3
    max_nodes: Annotated[int,Field(ge=1,le=100000)] = 20000
    candidate_budget_ms: Annotated[float,Field(gt=0,le=200)] = 200.0
    horizon_s: Annotated[float,Field(gt=0,le=240)] = 240.0


def _config(config):
    if config is not None: return TeacherConfig.model_validate(config)
    path=Path(__file__).resolve().parents[2]/'configs/teacher.json'
    return TeacherConfig.model_validate_json(path.read_text(encoding='utf-8'))


def _idle(): return Action(task_id=None,mode='idle',scheduled_bytes=0,reason_codes=[],fallback=False)


def _predicted_state(obs,cfg):
    """All environment fields here are constructed solely from public inputs."""
    public=cfg.policy
    health=obs.health.model_copy(update={'observed_at_s':0.0,'available_at_s':0.0})
    windows=[w.model_copy(update={'source':'synthetic'}) for w in obs.forecast_windows]
    scenario=ScenarioConfig(schema_version='1.0',scenario_id='teacher_public_forecast',source='synthetic',
        capacity_Wh=obs.health.capacity_Wh_est,initial_energy_Wh=obs.health.energy_lower_Wh,
        reserve_Wh=public.reserve_Wh,max_power_W=public.max_power_W,
        powers=dict(base_W=public.base_W,compute_W=public.compute_W,solar_W=public.solar_W),
        tx_power_W=public.tx_power_W.model_dump(),slot_s=public.slot_s,protocol=public.protocol,
        forecast_version=obs.forecast_version,true_windows=windows,forecast_windows=windows,
        health_observations=[health],tasks=[t.model_copy(update={'remaining_bytes':t.payload_bytes}) for t in obs.tasks])
    state=create_state(scenario,run_id='teacher_forecast',policy_id='teacher')
    state.sim_time_s=obs.sim_time_s
    state.tasks=copy.deepcopy(obs.tasks)
    state.announced={t.task_id for t in obs.tasks}
    for task in obs.tasks:
        for block in range((task.payload_bytes-task.remaining_bytes)//1024):
            state.protocol_state.confirmed.add((task.task_id,block))
            state.protocol_state.gateway.add((task.task_id,block))
    return state


def _projection(state):
    # This is the forecast-model energy, not actual environment truth supplied by a caller.
    state=copy.deepcopy(state)
    cap=state.config.capacity_Wh
    lower=state.energy_Wh/cap
    h=state.config.health_observations[0].model_copy(update=dict(soc_est=lower,soc_lower=lower,
        capacity_Wh_est=cap,capacity_lower_Wh=cap,energy_lower_Wh=state.energy_Wh,
        observed_at_s=state.sim_time_s,available_at_s=state.sim_time_s))
    state.config.health_observations=[h]
    return state


def solve_teacher(obs: Observation, budget_ms: int, *, config=None, diagnostics=None) -> TeacherResult:
    start=_clock()
    if isinstance(budget_ms,bool) or not isinstance(budget_ms,int) or not 1 <= budget_ms <= 5000:
        raise ContractViolation('INVALID_TEACHER_BUDGET','budget_ms must be an integer in 1..5000')
    cfg=_config(config)
    try: observed=Observation.model_validate(obs)
    except (ValueError,TypeError) as error: raise ContractViolation('INVALID_OBSERVATION',str(error)) from error
    candidates=[TeacherCandidateScore(task_id=t.task_id,mode=m,score=0.0,feasible=False)
                for t in observed.tasks for m in ('robust','fast')]
    candidates.append(TeacherCandidateScore(task_id=None,mode='idle',score=0.0,feasible=True))
    diag={'teacher_version':cfg.version,'candidates':[]}
    def finish(status,gap):
        if diagnostics is not None: diagnostics.update(diag)
        result=TeacherResult(candidate_scores=candidates,solver_status=status,gap=gap,
                             elapsed_ms=max(0.0,(_clock()-start)*1000))
        return validate_teacher_result(observed,result)
    if len(observed.tasks)>cfg.max_tasks: return finish('UNSUPPORTED_TASK_COUNT',None)
    if observed.inflight is not None: return finish('UNSUPPORTED_INFLIGHT',None)
    if len(observed.forecast_windows)>cfg.max_windows: return finish('UNSUPPORTED_WINDOW_COUNT',None)
    if any(p.robust_loss_prob or p.fast_loss_prob for w in observed.forecast_windows for p in w.loss_profile):
        return finish('UNSUPPORTED_LOSS',None)
    if not observed.tasks: return finish('OPTIMAL',0.0)
    total=sum(t.priority_weight for t in observed.tasks)
    if not math.isfinite(total): raise ContractViolation('TEACHER_INPUT_RANGE','Task weight sum overflow')
    end=max(t.deadline_s for t in observed.tasks)
    if end-observed.sim_time_s > min(cfg.horizon_s,cfg.max_steps*cfg.policy.decision_dt_s):
        return finish('UNSUPPORTED_HORIZON',None)
    try: initial=_predicted_state(observed,cfg)
    except ValueError: return finish('UNSUPPORTED_FORECAST_CONFIG',None)
    tasks={t.task_id:t for t in observed.tasks}
    initial_received=set(initial.protocol_state.gateway)
    deadline=start+budget_ms/1000
    limits=[]

    def credit(events,received,delivered):
        received=set(received);delivered=set(delivered)
        for event in events:
            if event.event_type!='received': continue
            received.add((event.task_id,event.block_id));task=tasks[event.task_id]
            if event.sim_time_s <= task.deadline_s and all((task.task_id,b) in received for b in range(math.ceil(task.payload_bytes/1024))):
                delivered.add(task.task_id)
        return received,delivered
    def utility(delivered): return min(1.0,sum(tasks[t].priority_weight for t in delivered)/total)

    for candidate in candidates:
        before=_clock();stop=min(deadline,before+cfg.candidate_budget_ms/1000)
        if candidate.mode=='idle': action=_idle()
        else:
            plan=plan_candidate(observed,tasks[candidate.task_id],candidate.mode,cfg.policy)
            candidate.feasible=plan.feasible
            if not plan.feasible: continue
            action=plan.action
        candidate.feasible=True
        best=0.0;nodes=0;limited=None

        def visit(state,received,delivered,forced=None):
            nonlocal best,nodes,limited
            best=max(best,utility(delivered))
            potential=delivered|{t.task_id for t in tasks.values() if t.deadline_s >= state.sim_time_s}
            if utility(potential) <= best or state.sim_time_s >= end: return
            if _clock() >= stop:
                limited='TIME_LIMIT_FEASIBLE';return
            if nodes >= cfg.max_nodes:
                limited='NODE_LIMIT_FEASIBLE';return
            nodes+=1
            current=_projection(state)
            interval=min(cfg.policy.decision_dt_s,end-current.sim_time_s)
            local=cfg.policy.model_copy(update={'decision_dt_s':interval})
            visible=observe(current)
            if forced is not None: actions=[forced]
            else:
                plans=[plan_candidate(visible,t,m,local) for t in visible.tasks for m in ('robust','fast')]
                valid=[p for p in plans if p.feasible]
                valid.sort(key=lambda p:(-tasks[p.action.task_id].priority_weight,p.cost_Wh,
                    tasks[p.action.task_id].deadline_s,p.action.task_id,p.airtime_s))
                actions=[p.action for p in valid]+[_idle()]
            for command in actions:
                if _clock() >= stop:
                    limited='TIME_LIMIT_FEASIBLE';return
                result=step(current,command,interval)
                rx,done=credit(result.events,received,delivered)
                visit(result.next_state,rx,done)
                if best >= utility(potential): return
                if limited: return
        if end <= observed.sim_time_s:
            candidate.feasible=candidate.mode=='idle'
        else: visit(initial,initial_received,set(),action)
        candidate.score=best
        if limited: limits.append((limited,1.0-best))
        diag['candidates'].append(dict(task_id=candidate.task_id,mode=candidate.mode,nodes=nodes,
            elapsed_ms=max(0.0,(_clock()-before)*1000),limited=limited))
    status='TIME_LIMIT_FEASIBLE' if any(s=='TIME_LIMIT_FEASIBLE' for s,_ in limits) else ('NODE_LIMIT_FEASIBLE' if limits else 'OPTIMAL')
    return finish(status,max((gap for _,gap in limits),default=0.0))


def preflight(output: Path):
    if output.exists() and any(output.iterdir()): raise ValueError('Output must be new or empty')
    output.mkdir(parents=True,exist_ok=True)
    base=json.loads((Path(__file__).resolve().parents[2]/'configs/scenarios/r3_normal.json').read_text(encoding='utf-8'))['scenario']
    rows=[];details=[];cpu=process_time()
    for index in range(20):
        data=copy.deepcopy(base);data['scenario_id']=f'teacher_synthetic_{index:02d}'
        data['tasks'][0].update(deadline_s=4.0,priority_weight=float(index%3+1))
        variant=index%4
        if variant==0:
            data['tasks'][0]['deadline_s']=1.0
            second=copy.deepcopy(data['tasks'][0]);second.update(task_id='T2',deadline_s=4.0,priority_weight=1.0)
            data['tasks'].append(second)
        elif variant==1:
            data['health_observations'][0].update(soc_est=0.01,soc_lower=0.01,energy_lower_Wh=0.2)
        elif variant==2:
            for windows in ('true_windows','forecast_windows'):
                data[windows][0].update(start_s=2.0,end_s=6.0)
                for name in ('rate_profile','loss_profile'): data[windows][0][name][0]['time_s']=2.0
        else: data['tasks'][0].update(payload_bytes=2500,remaining_bytes=2500,deadline_s=2.0)
        observed=observe(create_state(data,run_id=f'preflight_{index:02d}',policy_id='teacher'))
        diagnostic={};result=solve_teacher(observed,1000,diagnostics=diagnostic)
        row=dict(sample_id=f'r4_{index:02d}',scenario_id=data['scenario_id'],observation=observed.model_dump(),
            **result.model_dump(),teacher_version=_config(None).version,forecast_version=observed.forecast_version)
        rows.append(row);details.append(dict(sample_id=row['sample_id'],label_eligible=result.solver_status=='OPTIMAL',**diagnostic))
    text=''.join(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n' for row in rows)
    (output/'samples.jsonl').write_text(text,encoding='utf-8',newline='\n')
    summary=dict(kind='teacher_preflight_synthetic',count=len(rows),cpu_seconds=process_time()-cpu,
        optimal=sum(r['solver_status']=='OPTIMAL' for r in rows),timeouts=sum(r['solver_status']=='TIME_LIMIT_FEASIBLE' for r in rows),
        failed_or_unsupported=sum(r['solver_status'].startswith('UNSUPPORTED') for r in rows),
        all_zero_labels=sum(all(s['score']==0 for s in r['candidate_scores']) for r in rows),
        total_elapsed_ms=sum(r['elapsed_ms'] for r in rows),diagnostics=details,
        samples_sha256=hashlib.sha256((output/'samples.jsonl').read_bytes()).hexdigest(),config=_config(None).model_dump())
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    root=Path(__file__).resolve().parents[2]
    files=[root/'backend/contracts.py',root/'backend/cli.py',root/'backend/evaluation.py',
           *sorted((root/'backend/policies').glob('*.py')),*sorted((root/'backend/simulator').glob('*.py'))]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=dict(kind='teacher_preflight_synthetic',teacher_version=_config(None).version,
        solver='bounded_tree_enumeration',source='synthetic',model_hash=None,
        code_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        source_sha256={p.relative_to(root).as_posix():sha(p) for p in files},
        configuration_sha256={p.relative_to(root).as_posix():sha(p) for p in
            (root/'configs/teacher.json',root/'configs/policy.json')},
        observations_sha256=hashlib.sha256(json.dumps([r['observation'] for r in rows],sort_keys=True).encode()).hexdigest(),
        artifacts_sha256={name:sha(output/name) for name in ('samples.jsonl','summary.json')},
        note='20 initial synthetic states; no batch training or policy performance claim')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description='20 synthetic teacher preflight states, no training')
    parser.add_argument('--preflight',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=preflight(args.output)
    print(json.dumps({k:summary[k] for k in ('count','optimal','timeouts','cpu_seconds')},ensure_ascii=False))


if __name__=='__main__': main()
