import copy,json,subprocess
import pytest
from backend.simulator.engine import create_state,observe,step
from tests.test_protocol import config,send
from tests.test_simulator import idle_action
from tests.test_run_export import run_config
from backend.contracts import Action
from backend.cli import run_experiment


def test_timeout_requires_same_task_block_until_ack_or_retirement():
    data=config(deadline=20.0);data['protocol']['data_propagation_s']=3.0
    second=copy.deepcopy(data['tasks'][0]);second['task_id']='T2';data['tasks'].append(second)
    state=step(create_state(data),send(),3.5).next_state
    other=Action(task_id='T2',mode='robust',scheduled_bytes=1024,reason_codes=[],fallback=False)
    rejected=step(state,other,1.5)
    assert not any(e.event_type=='sent' for e in rejected.events)
    assert any(e.reason_code=='RETRY_REQUIRED' for e in rejected.events)
    retry=step(state,send(),1.5)
    assert any(e.event_type=='sent' and e.block_id==0 for e in retry.events)
    cleared=step(retry.next_state,idle_action(),1.0).next_state
    assert cleared.protocol_state.retry_required_key is None


def test_stale_health_lower_bound_accumulates_consumption_without_truth_oracle():
    data=config(2048);data['powers']['base_W']=0.0;data['initial_energy_Wh']=0.52
    data['health_observations'][0].update(soc_est=0.026,soc_lower=0.026,energy_lower_Wh=0.52)
    first=step(create_state(data),send(),3.0)
    assert observe(first.next_state).health.energy_lower_Wh<0.52
    second=step(first.next_state,send(),3.0)
    assert not any(e.event_type=='sent' for e in second.events)
    assert any(e.reason_code=='ENERGY_RESERVE' for e in second.events)
    assert second.next_state.energy_Wh>=0.5
    # A different hidden initial energy cannot change the public propagated bound.
    data['initial_energy_Wh']=10.0
    alternate=step(create_state(data),send(),3.0)
    assert observe(alternate.next_state).health==observe(first.next_state).health


def test_health_update_reanchors_at_observed_time_and_solar_is_counted():
    data=config();data['powers']['solar_W']=72.0
    fresh=copy.deepcopy(data['health_observations'][0]);fresh.update(observed_at_s=1.0,available_at_s=2.0,soc_est=0.4,soc_lower=0.4,energy_lower_Wh=8.0)
    data['health_observations'].append(fresh)
    state=step(create_state(data),idle_action(),3.0).next_state
    assert observe(state).health.energy_lower_Wh==pytest.approx(8.02)


@pytest.mark.parametrize('missing',[False,True])
def test_release_runs_without_git_and_has_honest_source_revision(tmp_path,monkeypatch,missing):
    import backend.cli as cli
    def git_failure(*args,**kwargs):
        if missing: raise FileNotFoundError('git unavailable')
        return subprocess.CompletedProcess(args[0],128,'','not a repository')
    monkeypatch.setattr(cli.subprocess,'run',git_failure)
    result=run_experiment(run_config(),tmp_path/'release')
    assert result['code_revision'].startswith('unversioned-source-sha256:')
    assert json.loads((tmp_path/'release/status.json').read_text())['status']=='completed'
    assert b'\r\n' not in (tmp_path/'release/execution.log').read_bytes()


def test_input_hash_covers_power_and_capacity(tmp_path):
    left=run_experiment(run_config(),tmp_path/'a')
    data=run_config();data['scenario']['tx_power_W']['robust']=30.0
    right=run_experiment(data,tmp_path/'b')
    assert left['input_hash']!=right['input_hash']
