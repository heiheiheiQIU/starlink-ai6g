import copy
import pytest

from backend.simulator.channel import ChannelConfig, uniform_at
from backend.simulator.engine import create_state,observe,step
from tests.test_protocol import config,send
from tests.test_simulator import idle_action


def noisy(data_loss=0.0,ack_loss=0.0,seed=1):
    data=config(deadline=20.0)
    data['channel']=dict(seed=seed,step_s=.25,ack_loss_prob=ack_loss,version='time-indexed-sha256-v1')
    for windows in ('true_windows','forecast_windows'):
        data[windows][0]['loss_profile'][0].update(robust_loss_prob=data_loss,fast_loss_prob=data_loss)
    return data


def test_time_indexed_uniform_independent_of_calls_and_streams():
    cfg=ChannelConfig(seed=123)
    target=uniform_at(cfg,8.0,'data')
    for t in range(30): uniform_at(cfg,float(t),'data')
    assert uniform_at(cfg,8.0,'data')==target==uniform_at(cfg,8.1,'data')
    assert uniform_at(cfg,8.0,'ack')!=target
    assert uniform_at(ChannelConfig(seed=124),8.0,'data')!=target
    assert 0<=target<1
    with pytest.raises(ValueError): uniform_at(cfg,-1.0,'data')


def test_total_data_loss_has_no_gateway_receive_or_ack_but_timeout_and_energy():
    state=create_state(noisy(data_loss=1.0))
    result=step(state,send(),4.0)
    assert not any(e.event_type in ('received','acked') for e in result.events)
    assert any(e.reason_code=='DATA_LOST_CHANNEL' for e in result.events)
    assert any(e.reason_code=='ACK_TIMEOUT' for e in result.events)
    assert result.next_state.tasks[0].remaining_bytes==1024
    assert result.next_state.energy_Wh<state.energy_Wh
    assert sum(row.entry.receive_Wh for row in result.next_state.energy_ledger)==0


def test_total_ack_loss_retries_dedup_and_charges_receiver():
    state=create_state(noisy(ack_loss=1.0));events=[]
    for _ in range(2):
        result=step(state,send(),4.0);state=result.next_state;events+=result.events
    assert sum(e.event_type=='received' and e.reason_code is None for e in events)==1
    assert sum(e.reason_code=='DUPLICATE_BLOCK' for e in events)==1
    assert any(e.reason_code=='ACK_LOST_CHANNEL' for e in events)
    assert not any(e.event_type=='acked' for e in events)
    assert sum(row.entry.receive_Wh for row in state.energy_ledger)>0
    assert state.tasks[0].remaining_bytes==1024


def test_optional_channel_legacy_compatibility_and_observation_isolation():
    plain=config();data=copy.deepcopy(plain);data['channel']=ChannelConfig(seed=7).model_dump()
    old=step(create_state(plain),send(),4.0);new=step(create_state(data),send(),4.0)
    assert [e.model_dump() for e in old.events]==[e.model_dump() for e in new.events]
    assert observe(create_state(data)).model_dump()==observe(create_state(plain)).model_dump()
    invalid=noisy(data_loss=.5);invalid.pop('channel')
    with pytest.raises(ValueError):create_state(invalid)


def test_prior_idle_or_other_packets_do_not_shift_data_draw():
    data=noisy(data_loss=.5,seed=99)
    fresh=step(create_state(data),idle_action(),4.0).next_state
    earlier=step(create_state(data),send(),4.0).next_state
    # Both send attempts at t4 use the same public-time external sample, regardless of history.
    a=step(fresh,send(),4.0);b=step(earlier,send(),4.0)
    def outcome(result):return any(e.reason_code=='DATA_LOST_CHANNEL' and e.sim_time_s>4 for e in result.events)
    # If the earlier packet was confirmed, use a new same-sized task at this public time.
    if earlier.tasks[0].remaining_bytes==0:
        earlier.tasks[0].remaining_bytes=1024;earlier.protocol_state.confirmed.clear()
        b=step(earlier,send(),4.0)
    assert outcome(a)==outcome(b)


def test_decimal_time_grid_boundary_is_stable_for_equivalent_float_times():
    cfg=ChannelConfig(seed=7,step_s=.1)
    assert uniform_at(cfg,.3,'data')==uniform_at(cfg,.1+.2,'data')
