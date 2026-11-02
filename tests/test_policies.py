import copy
import pytest
from backend.contracts import CandidateScore, ContractViolation
from backend.policies.guard import decode_safe
from backend.policies.common import PolicyConfig
from backend.policies import edf, value
from backend.simulator.engine import create_state, observe
from tests.test_protocol import config


def obs(data=None): return observe(create_state(config() if data is None else data))


def scores(task_id='T1',score=10.0):
    return [dict(task_id=task_id,mode='robust',score=score),dict(task_id=None,mode='idle',score=0.0)]


def test_empty_queue_idle_and_all_candidates_unique():
    data=config(); data['tasks']=[]; observed=obs(data)
    for module in (edf,value):
        output=module.score_actions(observed)
        assert len(output)==1 and output[0].mode=='idle'
        assert decode_safe(observed,output).action.mode=='idle'


@pytest.mark.parametrize('change,reason', [('window','NO_VISIBLE_WINDOW'),('energy','ENERGY_RESERVE'),('power','POWER_LIMIT'),('deadline','DEADLINE_UNREACHABLE')])
def test_high_score_cannot_override_constraints(change,reason):
    data=config()
    settings=PolicyConfig()
    if change=='window': data['forecast_windows']=[]
    elif change=='energy': data['health_observations'][0].update(soc_est=0.01,soc_lower=0.01,energy_lower_Wh=0.2)
    elif change=='power': settings=settings.model_copy(update={'max_power_W':40.0})
    else: data['tasks'][0]['deadline_s']=0.5
    decision=decode_safe(obs(data),scores(),config=settings)
    assert decision.action.mode=='idle' and decision.action.scheduled_bytes==0
    assert reason in decision.action.reason_codes
    assert any(c.code==reason and not c.passed for c in decision.constraint_checks)


@pytest.mark.parametrize('bad', [[],[dict(task_id=None,mode='idle',score=float('nan'))],scores('unknown'),scores()+[dict(task_id=None,mode='idle',score=0.0)]])
def test_invalid_full_scores_fall_back_to_edf_with_reason(bad):
    decision=decode_safe(obs(),bad)
    assert decision.fallback and decision.action.fallback
    assert 'INVALID_SCORE' in decision.action.reason_codes
    assert decision.action.mode in ('fast','robust')


def test_modes_tie_prefers_energy_then_finish_and_full_short_block():
    data=config(payload=452)
    decision=decode_safe(obs(data),edf.score_actions(obs(data)))
    assert decision.action.mode=='fast' and decision.action.scheduled_bytes==452
    parsed=decision.to_event_data()
    assert parsed.latency_ms>=0 and parsed.policy_version


def test_edf_and_value_differ_under_same_guard():
    data=config(deadline=10.0)
    t=copy.deepcopy(data['tasks'][0]);t.update(task_id='T2',deadline_s=20.0,priority_weight=10.0)
    data['tasks'].append(t); observed=obs(data)
    assert decode_safe(observed,edf.score_actions(observed)).action.task_id=='T1'
    assert decode_safe(observed,value.score_actions(observed)).action.task_id=='T2'
    assert len(edf.score_actions(observed))==5


def test_forecast_rate_change_deadline_and_no_future_mutation():
    data=config(); data['true_windows']=[]
    observed=obs(data); frozen=observed.model_dump()
    decision=decode_safe(observed,scores())
    assert decision.action.mode=='robust' # guard only sees forecast
    assert observed.model_dump()==frozen
    assert decode_safe(observed,scores()).action==decision.action
    bad=observed.model_copy(deep=True);bad.sim_time_s=-1.0
    with pytest.raises(ContractViolation): decode_safe(bad,scores())


def test_inflight_blocks_even_expired_metadata_and_piecewise_rate_counts_header():
    from backend.simulator.engine import step
    from tests.test_protocol import send
    state=step(create_state(config()),send(),1.5).next_state
    decision=decode_safe(observe(state),scores())
    assert decision.action.mode=='idle' and 'INFLIGHT_BLOCK' in decision.action.reason_codes
    data=config();data['forecast_windows'][0]['rate_profile'].append(dict(time_s=0.5,robust_bps=1.0,fast_bps=1.0))
    decision=decode_safe(obs(data),scores())
    assert decision.action.mode=='idle'
    assert 'INSUFFICIENT_LINK_TIME' in decision.action.reason_codes
