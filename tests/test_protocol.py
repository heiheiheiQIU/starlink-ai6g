"""Actual deterministic protocol execution using synthetic inputs."""
import copy
import pytest

from backend.contracts import Action
from backend.simulator.engine import create_state, observe, step
from tests.test_simulator import scenario_data, idle_action


def config(payload=1024, deadline=20.0):
    data = scenario_data()
    data['tasks'][0].update(payload_bytes=payload, remaining_bytes=payload, deadline_s=deadline)
    data['protocol'] = dict(data_propagation_s=0.0, ack_propagation_s=0.0,
                            control_bps=1024.0, ack_rx_W=8.0)
    return data


def send(size=1024):
    return Action(task_id='T1', mode='robust', scheduled_bytes=size, fallback=False, reason_codes=[])


def test_block_split_and_validation():
    from backend.simulator.protocol import split_payload
    assert split_payload(2500) == (1024, 1024, 452)
    for bad in (0, -1, True, 1.5):
        with pytest.raises(ValueError): split_payload(bad)


def test_receive_does_not_ack_until_delay_and_only_ack_decrements_cache():
    state = create_state(config())
    result = step(state, send(), 1.5)
    assert [e.event_type for e in result.events].count('received') == 1
    assert observe(result.next_state).tasks[0].remaining_bytes == 1024
    assert result.next_state.inflight is not None
    done = step(result.next_state, idle_action(), 1.0)
    assert sum(e.event_type == 'acked' for e in done.events) == 1
    assert done.next_state.inflight is None
    assert done.next_state.tasks[0].remaining_bytes == 0
    assert observe(done.next_state).tasks == []
    assert state.tasks[0].remaining_bytes == 1024 and state.sim_time_s == 0


def test_multiblock_last_short_block_ids_and_energy_accounting():
    state = create_state(config(2500))
    events = []
    for size in (1024, 1024, 452):
        result = step(state, send(size), 3.0)
        state = result.next_state; events.extend(result.events)
    sent = [e for e in events if e.event_type == 'sent']
    assert [(e.block_id, e.payload_bytes) for e in sent] == [(0,1024),(1,1024),(2,452)]
    assert state.tasks[0].remaining_bytes == 0
    expected = (36*9 + 36*(1056+1056+484)*8/8192 + 8*3*0.125)/3600
    assert 10-state.energy_Wh == pytest.approx(expected)
    assert sum(e.energy_Wh for e in events) == pytest.approx(expected)
    assert sum(r.entry.receive_Wh for r in state.energy_ledger) == pytest.approx(3/3600)
    assert not any('gateway' in key for key in observe(state).model_dump())


def test_idle_split_equivalent_and_single_inflight():
    data = config()
    whole = step(create_state(data), send(), 4.0)
    first = step(create_state(data), send(), 1.5)
    blocked = step(first.next_state, send(), 0.25)
    assert any(e.reason_code == 'INFLIGHT_BLOCK' for e in blocked.events)
    split = step(blocked.next_state, idle_action(), 2.25)
    assert whole.next_state.energy_Wh == pytest.approx(split.next_state.energy_Wh)
    assert whole.next_state.tasks == split.next_state.tasks
    assert all(e.sim_time_s <= split.next_state.sim_time_s for e in split.events)


def test_protocol_rejects_impossible_control_budget_and_nonfinite_config():
    for change in ({'control_bps': 1.0}, {'ack_rx_W': float('nan')}, {'data_propagation_s': -1.0}):
        data = config(); data['protocol'].update(change)
        with pytest.raises(ValueError): create_state(data)


def loss_config():
    from tests.test_simulator import window
    data = config(deadline=20.0)
    data['true_windows'] = [window(0.0,2.0).model_dump(), window(4.0,20.0).model_dump()]
    data['true_windows'][1]['window_id'] = 'W2'
    return data


def test_window_loss_timeout_retry_gateway_dedup_and_energy():
    state = create_state(loss_config()); events = []
    first = step(state, send(), 4.0); state=first.next_state; events.extend(first.events)
    assert state.tasks[0].remaining_bytes == 1024 and state.inflight is None
    assert any(e.reason_code == 'ACK_LOST_WINDOW_CLOSED' for e in events)
    assert any(e.reason_code == 'ACK_TIMEOUT' for e in events)
    second = step(state, send(), 3.0); state=second.next_state; events.extend(second.events)
    assert [e.block_id for e in events if e.event_type == 'sent'] == [0,0]
    assert [e.reason_code for e in events if e.event_type == 'received'] == [None,'DUPLICATE_BLOCK']
    assert state.tasks[0].remaining_bytes == 0 and state.inflight is None
    assert len(state.protocol_state.gateway) == 1
    assert sum(e.energy_Wh for e in events) == pytest.approx(10-state.energy_Wh)


def test_close_does_not_destroy_propagating_data_and_no_send_after_deadline():
    from tests.test_simulator import window
    data=config(deadline=2.03125); data['protocol']['data_propagation_s']=1.0
    data['true_windows']=[window(0.0,1.5).model_dump()]
    result=step(create_state(data),send(),4.0)
    received=[e for e in result.events if e.event_type=='received']
    assert [e.sim_time_s for e in received]==[2.03125] # exactly deadline
    assert any(e.reason_code=='ACK_LOST_WINDOW_CLOSED' for e in result.events)
    late=step(result.next_state,send(),2.0)
    assert not any(e.event_type=='sent' for e in late.events)


def test_ack_timeout_equality_prioritizes_ack():
    data=config(); data['protocol']['data_propagation_s']=1.0
    result=step(create_state(data),send(),4.0)
    assert any(e.event_type=='acked' and e.sim_time_s==3.03125 for e in result.events)
    assert not any(e.reason_code=='ACK_TIMEOUT' for e in result.events)


def test_old_ack_during_retry_confirms_once_and_keeps_block_identity():
    data=config(2500); data['protocol']['data_propagation_s']=3.0
    first=step(create_state(data),send(),3.5)
    assert first.next_state.inflight is None
    second=step(first.next_state,send(),2.5)
    assert second.next_state.tasks[0].remaining_bytes==1476
    assert second.next_state.inflight is None
    third=step(second.next_state,idle_action(),4.0)
    assert third.next_state.tasks[0].remaining_bytes==1476
    # Both ACKs are observable, but the second carries no additional confirmation.
    assert any(e.event_type=='acked' and e.reason_code=='DUPLICATE_ACK' for e in third.events)


def test_protocol_rejects_invalid_dt_and_excludes_future_health():
    state=create_state(config())
    for bad in (0.0,-1.0,float('inf'),float('nan'),True):
        with pytest.raises(ValueError): step(state, idle_action(),bad)
    assert state.sim_time_s==0 and state.protocol_state.pending==[]
