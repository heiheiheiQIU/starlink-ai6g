"""Single-policy, event-only evaluation for deterministic synthetic validation."""
from backend.contracts import Event, PolicyResult
from backend.simulator.engine import ScenarioConfig
from backend.simulator.energy import finite_number


def _percentile(values, fraction):
    if not values: return None
    ordered = sorted(values)
    index = (len(ordered)-1)*fraction
    low = int(index); high = min(low+1, len(ordered)-1)
    return ordered[low]+(ordered[high]-ordered[low])*(index-low)


def evaluate(events: list[Event], config: dict) -> dict:
    scenario = ScenarioConfig.model_validate(config['scenario'])
    end = finite_number(config['evaluation_end_s'], 'evaluation_end_s', positive=True)
    policy = config['policy_id']
    parsed = [Event.model_validate(e) for e in events]
    if not parsed or len({e.run_id for e in parsed}) != 1 or any(e.policy_id != policy for e in parsed):
        raise ValueError('Evaluation needs exactly one run and policy')
    if any(a.event_id >= b.event_id or a.sim_time_s > b.sim_time_s for a,b in zip(parsed,parsed[1:])):
        raise ValueError('Events must have increasing IDs and nondecreasing times')
    if any(e.sim_time_s > end for e in parsed):
        raise ValueError('Events exceed evaluation horizon')
    tasks = {t.task_id:t for t in scenario.tasks}
    received, complete, sent, waits = {}, {}, {}, {}
    for event in parsed:
        if event.event_type == 'sent':
            if event.task_id not in tasks or event.block_id is None:
                raise ValueError('Unknown sent block')
            sent.setdefault((event.task_id,event.block_id),event.sim_time_s)
            waits.setdefault(event.task_id,event.sim_time_s-tasks[event.task_id].arrival_s)
        if event.event_type != 'received': continue
        task = tasks.get(event.task_id)
        if task is None or event.block_id is None:
            raise ValueError('Unknown received task/block')
        offset = event.block_id*1024
        expected = min(1024,task.payload_bytes-offset)
        key = (task.task_id,event.block_id)
        if (expected <= 0 or event.payload_bytes != expected or event.sim_time_s < task.arrival_s
                or key not in sent or event.sim_time_s < sent[key]):
            raise ValueError('Invalid or causally unsupported received block')
        if key not in received:
            received[key] = (event.payload_bytes,event.sim_time_s)
            total = sum(n for (task_id,_),(n,_) in received.items() if task_id == task.task_id)
            if total == task.payload_bytes: complete[task.task_id] = event.sim_time_s
    eligible = [t for t in tasks.values() if t.arrival_s <= end and t.deadline_s <= end]
    pending = [t for t in tasks.values() if t.arrival_s <= end < t.deadline_s]
    denominator = sum(t.priority_weight for t in eligible)
    numerator = sum(t.priority_weight for t in eligible if complete.get(t.task_id,float('inf')) <= t.deadline_s)
    byte_count = sum(n for n,_ in received.values())
    snapshots = [e.data.evaluation_truth for e in parsed if e.event_type == 'snapshot'
                 and e.data.evaluation_truth is not None]
    if not any(e.event_type == 'snapshot' and e.sim_time_s == end for e in parsed):
        raise ValueError('Evaluation requires a final snapshot at the configured horizon')
    values = dict(policy_id=policy,model_hash=None,sample_count=len(eligible),evaluation_end_s=end,
        pending_task_count=len(pending),weighted_on_time_rate=numerator/denominator if denominator else None,
        critical_task_success_rate=None,goodput_bps=byte_count*8/end,
        minimum_soc_true=min([scenario.initial_energy_Wh/scenario.capacity_Wh]+[s.soc_true for s in snapshots]),
        energy_violation_count=sum(s.energy_true_Wh < 0 for s in snapshots),
        energy_violation_duration_s=None,success_payload_bytes=byte_count,
        joule_per_success_bit=sum(e.energy_Wh for e in parsed)*3600/(byte_count*8) if byte_count else None,
        wait_p50_s=_percentile(list(waits.values()),0.5),wait_p95_s=_percentile(list(waits.values()),0.95),
        decision_p50_ms=None,decision_p95_ms=None,timeout_rate=None,parameter_count=None,memory_bytes=None)
    reasons = {name:'NOT_MEASURED_MANUAL_VALIDATION' for name,value in values.items() if value is None}
    if denominator == 0: reasons['weighted_on_time_rate']='NO_ELIGIBLE_TASKS'
    if byte_count == 0: reasons['joule_per_success_bit']='NO_DELIVERY'
    reasons.pop('model_hash', None)  # Provenance field, not a nullable metric.
    reasons['critical_task_success_rate']='NO_CRITICAL_TASK_SET'
    reasons['energy_violation_duration_s']='EXACT_DURATION_NOT_MEASURED'
    decisions=[e.data for e in parsed if e.event_type=='decision']
    if decisions:
        values['decision_p50_ms']=_percentile([d.latency_ms for d in decisions],0.5)
        values['decision_p95_ms']=_percentile([d.latency_ms for d in decisions],0.95)
        values['timeout_rate']=sum('MODEL_TIMEOUT' in d.action.reason_codes for d in decisions)/len(decisions)
        for key in ('decision_p50_ms','decision_p95_ms','timeout_rate'): reasons.pop(key,None)
    return PolicyResult.model_validate(dict(**values,metric_reasons=reasons)).model_dump()
