import json

import pytest

from backend.policies import edf
from backend.policies.runner import ScorerGateway, run_policy
from tests.test_policies import obs
from tests.test_protocol import config
from tests.test_run_export import run_config


@pytest.mark.parametrize('bad', ['missing', 'duplicate', 'unknown', 'nan'])
def test_learned_gateway_rejects_incomplete_or_invalid_candidates(bad):
    observed = obs()
    scores = [s.model_dump() for s in edf.score_actions(observed)]
    if bad == 'missing': scores.pop(0)
    if bad == 'duplicate': scores.append(scores[0])
    if bad == 'unknown': scores[0]['task_id'] = 'unknown'
    if bad == 'nan': scores[0]['score'] = float('nan')
    decision = ScorerGateway(lambda o: scores, require_complete=True).decide(observed)
    assert decision.fallback and 'INVALID_SCORE' in decision.action.reason_codes
    assert decision.action.mode != 'idle'


def test_learned_gateway_keeps_normal_idle_and_model_identity():
    observed = obs()
    scores = [s.model_copy(update={'score': 1.0 if s.mode == 'idle' else 0.0})
              for s in edf.score_actions(observed)]
    result = ScorerGateway(lambda o: scores, require_complete=True, model_version='frozen-test').decide(observed)
    assert result.action.mode == 'idle' and not result.fallback
    assert result.model_version == 'frozen-test'


def test_all_structurally_masked_tasks_fall_back_but_empty_queue_does_not():
    from backend.policies.learned import score_actions
    from backend.simulator.engine import create_state, observe, step
    from tests.test_protocol import send
    observed=observe(step(create_state(config()),send(),1.5).next_state)
    result=ScorerGateway(score_actions,require_complete=True,model_version='frozen').decide(observed)
    assert result.fallback and 'NO_VALID_CANDIDATE' in result.action.reason_codes
    assert result.model_version is None
    data=config();data['tasks']=[]
    empty=obs(data)
    result=ScorerGateway(score_actions,require_complete=True,model_version='frozen').decide(empty)
    assert result.action.mode=='idle' and not result.fallback


def test_frozen_learned_runner_records_model_and_decisions(tmp_path):
    result = run_policy(run_config(config(deadline=4), actions=[], end=4), tmp_path/'run', policy_id='learned')
    metadata = json.loads((tmp_path/'run/manifest.json').read_text(encoding='utf-8'))
    assert result['model_hash'] == result['by_policy'][0]['model_hash'] == metadata['model_hash']
    assert len(result['model_hash']) == 64
    assert metadata['model']['model_version'] == 'a-n3-mlp-v1'
    assert metadata['inference']['requests'] > 0
    assert 'backend/api/inference.py' in metadata['source_sha256']
    assert 'backend/api/processes.py' in metadata['source_sha256']
    assert 'training/policy_features.py' in metadata['source_sha256']
    events = [json.loads(s) for s in (tmp_path/'run/events.jsonl').read_text(encoding='utf-8').splitlines()]
    decisions = [e for e in events if e['event_type'] == 'decision']
    assert decisions and all(len(e['data']['candidate_scores']) == 3 for e in decisions)
    assert any(e['data']['model_version'] == 'a-n3-mlp-v1' and not e['data']['fallback'] for e in decisions)


def test_retry_controller_keeps_model_scores_and_retransmits_required_block(tmp_path):
    from tests.test_protocol import loss_config
    import copy
    data=loss_config();data['true_windows'][0]['end_s']=1.4
    data['forecast_windows']=copy.deepcopy(data['true_windows'])
    second=copy.deepcopy(data['tasks'][0]);second.update(task_id='T2',arrival_s=4.0,deadline_s=10.0)
    data['tasks'].append(second)
    run_policy(run_config(data,actions=[],end=16.0),tmp_path/'retry',policy_id='learned',
               inference_client=edf.score_actions,model_metadata={'model_hash':'a'*64,'model_version':'test-scorer'})
    events=[json.loads(l) for l in (tmp_path/'retry/events.jsonl').read_text().splitlines()]
    assert next(e for e in events if e['event_type']=='sent' and e['sim_time_s']==4.0)['task_id']=='T1'
    decision=next(e['data'] for e in events if e['event_type']=='decision' and e['sim_time_s']==4.0)
    assert 'RETRY_REQUIRED' in decision['action']['reason_codes']
    scores=decision['candidate_scores']
    assert max(s['score'] for s in scores if s['task_id']=='T2') > max(s['score'] for s in scores if s['task_id']=='T1')

