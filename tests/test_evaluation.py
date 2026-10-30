"""Hand-computable metrics from actual R3 events, independent of state truth."""
import copy
import pytest
from backend.contracts import Event, PolicyResult
from backend.evaluation import evaluate
from backend.simulator.engine import create_state, step
from tests.test_protocol import config, send, loss_config
from tests.test_simulator import idle_action


def run(data, actions):
    state=create_state(data,run_id='test_run',policy_id='manual'); events=[]
    for action,dt in actions:
        result=step(state,action,dt); state=result.next_state; events.extend(result.events)
    return events


def metrics(data,events,end):
    return evaluate(events,dict(scenario=data,evaluation_end_s=end,policy_id='manual'))


def test_weighted_denominator_failure_and_pending_future():
    data=config(deadline=5.0); data['tasks'][0]['priority_weight']=2.0
    for name,arrival,deadline in [('T2',0.0,5.0),('pending',0.0,20.0),('future',20.0,30.0)]:
        t=copy.deepcopy(data['tasks'][0]); t.update(task_id=name,arrival_s=arrival,deadline_s=deadline,priority_weight=1.0)
        data['tasks'].append(t)
    result=metrics(data,run(data,[(send(),6.0)]),6.0)
    assert result['weighted_on_time_rate']==pytest.approx(2/3)
    assert result['sample_count']==2 and result['pending_task_count']==1
    assert result['success_payload_bytes']==1024
    PolicyResult.model_validate(result)


def test_partial_task_and_dedup_bytes_are_distinct_from_complete_tasks():
    data=config(2500,deadline=5.0)
    result=metrics(data,run(data,[(send(),6.0)]),6.0)
    assert result['weighted_on_time_rate']==0.0
    assert result['success_payload_bytes']==1024
    assert result['goodput_bps']==pytest.approx(1024*8/6)
    assert 'weighted_on_time_rate' not in result['metric_reasons']


def test_ack_loss_dedup_and_joule_per_bit_include_retry():
    data=loss_config(); events=run(data,[(send(),4.0),(send(),3.0)])
    result=metrics(data,events,7.0)
    assert result['success_payload_bytes']==1024
    assert result['joule_per_success_bit']==pytest.approx(sum(e.energy_Wh for e in events)*3600/(1024*8))


def test_receive_at_deadline_with_late_ack_still_succeeds():
    data=config(deadline=1.03125)
    result=metrics(data,run(data,[(send(),4.0)]),4.0)
    assert result['weighted_on_time_rate']==1.0


def test_no_delivery_and_empty_denominator_reasons():
    data=config(deadline=5.0)
    result=metrics(data,run(data,[(idle_action(),6.0)]),6.0)
    assert result['joule_per_success_bit'] is None
    assert result['metric_reasons']['joule_per_success_bit']=='NO_DELIVERY'
    assert result['weighted_on_time_rate']==0.0
    result=metrics(data,run(data,[(idle_action(),1.0)]),1.0)
    assert result['weighted_on_time_rate'] is None
    assert result['metric_reasons']['weighted_on_time_rate']=='NO_ELIGIBLE_TASKS'


def test_evaluator_rejects_mixed_runs_duplicate_ids_and_bad_blocks():
    data=config(deadline=5.0); events=run(data,[(send(),6.0)])
    for mutation in ('run','id','payload','late'):
        bad=copy.deepcopy(events)
        if mutation=='run': bad[-1].run_id='other'
        elif mutation=='id': bad[-1].event_id=bad[0].event_id
        elif mutation=='payload': next(e for e in bad if e.event_type=='received').payload_bytes=999
        else: bad[-1].sim_time_s=10.0
        with pytest.raises(ValueError): metrics(data,bad,6.0)
    with pytest.raises(ValueError): metrics(data,events,0.0)
