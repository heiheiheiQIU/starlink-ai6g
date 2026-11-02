"""Full-score validation and shared executable block decoder using Observation only."""
from time import perf_counter
from backend.contracts import (Action, ContractViolation, Decision, Observation,
                               validate_candidate_scores)
from .common import plan_candidate, settings


def decode_safe(obs: Observation, scores, *, config=None) -> Decision:
    start=perf_counter(); cfg=settings(config)
    try:
        observed=Observation.model_validate(obs)
    except (ValueError,TypeError) as error:
        raise ContractViolation('INVALID_OBSERVATION',str(error)) from error
    reason=None
    try:
        parsed=validate_candidate_scores(observed,scores)
    except ContractViolation:
        from .edf import score_actions
        parsed=score_actions(observed); reason='INVALID_SCORE'
    task_map={t.task_id:t for t in observed.tasks}
    choices=[]; checks=[]; blocked=[]
    for candidate in parsed:
        if candidate.mode=='idle':
            action=Action(task_id=None,mode='idle',scheduled_bytes=0,reason_codes=[],fallback=False)
            choices.append(((-candidate.score,0.0,float('inf'),'','',0.0),action))
            continue
        plan=plan_candidate(observed,task_map[candidate.task_id],candidate.mode,cfg)
        checks.extend(plan.checks)
        if plan.feasible:
            key=(-candidate.score,plan.cost_Wh,task_map[candidate.task_id].deadline_s,
                 candidate.task_id,plan.airtime_s,candidate.mode)
            choices.append((key,plan.action))
        else:
            blocked.extend(c.code for c in plan.checks if not c.passed)
    action=min(choices,key=lambda item:item[0])[1]
    if reason:
        action=action.model_copy(update={'fallback':True,'reason_codes':[reason]})
    elif action.mode=='idle' and blocked:
        action=action.model_copy(update={'reason_codes':list(dict.fromkeys(blocked))})
    return Decision(action=action,candidate_scores=parsed,constraint_checks=checks,
        decision_latency_ms=(perf_counter()-start)*1000,fallback=action.fallback,
        model_version=None,policy_version='guard-r4-v1')


def fallback_decision(obs: Observation, reason: str, *, config=None) -> Decision:
    from .edf import score_actions
    decision=decode_safe(obs,score_actions(obs),config=config)
    action=decision.action.model_copy(update={'fallback':True,
        'reason_codes':list(dict.fromkeys([reason,*decision.action.reason_codes]))})
    return decision.model_copy(update={'action':action,'fallback':True})
