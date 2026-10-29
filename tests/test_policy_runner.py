import json,threading,time
import pytest
from backend.policies.runner import ScorerGateway, run_policy
from backend.policies.common import PolicyConfig
from backend.policies import edf
from tests.test_policies import obs
from tests.test_run_export import run_config
from tests.test_protocol import config


def test_missing_nan_and_bounded_timeout_use_explicit_fallback():
    observed=obs()
    assert 'MODEL_UNAVAILABLE' in ScorerGateway(None).decide(observed).action.reason_codes
    assert 'INVALID_SCORE' in ScorerGateway(lambda o:[dict(task_id=None,mode='idle',score=float('nan'))]).decide(observed).action.reason_codes
    release=threading.Event(); started=threading.Event()
    def blocked(o): started.set();release.wait(2);return edf.score_actions(o)
    gateway=ScorerGateway(blocked,budget_ms=10.0)
    before=time.perf_counter(); decision=gateway.decide(observed)
    assert 'MODEL_TIMEOUT' in decision.action.reason_codes and time.perf_counter()-before<0.5
    assert 'MODEL_BUSY' in gateway.decide(observed).action.reason_codes
    release.set(); gateway.worker.join(1)
    assert not gateway.worker.is_alive()


@pytest.mark.parametrize('policy',['edf','value'])
def test_rule_runs_complete_multiblock_with_decisions_and_separate_state(tmp_path,policy):
    data=run_config(config(2500,deadline=10.0),actions=[],end=10.0)
    left=run_policy(data,tmp_path/policy,policy_id=policy,run_id='rules')
    right=run_policy(data,tmp_path/(policy+'2'),policy_id=policy,run_id='rules')
    assert left['by_policy'][0]['success_payload_bytes']==2500
    assert left['by_policy'][0]['weighted_on_time_rate']==1.0
    assert left['by_policy'][0]['decision_p95_ms'] is not None
    events=[json.loads(line) for line in (tmp_path/policy/'events.jsonl').read_text().splitlines()]
    assert [e['event_id'] for e in events]==list(range(1,len(events)+1))
    assert all(e['policy_id']==policy for e in events)
    assert any(e['event_type']=='decision' for e in events)
    assert all(e['data']['policy_version'].startswith(policy) for e in events if e['event_type']=='snapshot')
    for e in events:
        if e['event_type']=='decision':
            sent=[s for s in events if s['event_type']=='sent' and s['sim_time_s']==e['sim_time_s']]
            if sent: assert sent[0]['task_id']==e['data']['action']['task_id']
    assert left['by_policy'][0]['success_payload_bytes']==right['by_policy'][0]['success_payload_bytes']


def test_actual_window_disagreement_and_low_energy_leave_evidence(tmp_path):
    data=run_config();data['scenario']['true_windows']=[]
    result=run_policy(data,tmp_path/'no_actual',policy_id='edf')
    events=[json.loads(line) for line in (tmp_path/'no_actual/events.jsonl').read_text().splitlines()]
    assert result['by_policy'][0]['success_payload_bytes']==0
    assert any(e['reason_code']=='NO_VISIBLE_WINDOW' for e in events)
    data=run_config();data['scenario']['health_observations'][0].update(soc_est=0.01,soc_lower=0.01,energy_lower_Wh=0.2)
    result=run_policy(data,tmp_path/'low',policy_id='value')
    assert result['by_policy'][0]['success_payload_bytes']==0


def test_rule_cli_entry_runs_without_manual_actions(tmp_path):
    import subprocess,sys
    path=tmp_path/'input.json';path.write_text(json.dumps(run_config()),encoding='utf-8')
    result=subprocess.run([sys.executable,'-m','backend.cli','policy-run','--config',str(path),'--policy','edf','--output',str(tmp_path/'run')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
