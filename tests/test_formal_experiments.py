import json

import pytest

from tests.test_formal_freeze import make_review


def frozen(tmp_path):
    from backend.formal_freeze import freeze_inputs
    freeze_inputs(*make_review(tmp_path), tmp_path/'frozen')
    return tmp_path/'frozen/manifest.json'


def test_real_three_policy_run_and_resume_preserve_unique_samples(tmp_path):
    from backend.formal_experiments import run_formal, read_run_index
    manifest = frozen(tmp_path); out = tmp_path/'batch'
    trace = 'formal_v1_cell_00_trace_00'
    result = run_formal(manifest, out, trajectory_ids=[trace])
    assert result['expected_policy_runs'] == 540
    assert result['completed_policy_runs'] == 3
    assert result['missing_policy_runs'] == 537
    assert result['data_scope'] == 'test_fixture'
    rows = read_run_index(manifest, out/'run_index.jsonl')
    assert len(rows) == 3
    assert {r['policy_id'] for r in rows} == {'edf', 'value', 'learned'}
    assert len({r['input_hash'] for r in rows}) == 1
    before = (out/'run_index.jsonl').read_bytes()
    assert run_formal(manifest, out, trajectory_ids=[trace], resume=True) == result
    assert (out/'run_index.jsonl').read_bytes() == before
    learned = next(r for r in rows if r['policy_id'] == 'learned')
    assert len(learned['model_hash']) == 64
    assert len({r['run_id'] for r in rows}) == 3


def test_failure_is_retained_and_only_one_retry_allowed(tmp_path, monkeypatch):
    import backend.formal_experiments as module
    manifest = frozen(tmp_path); real = module.run_policy
    def fail_edf(*args, **kwargs):
        if kwargs['policy_id'] == 'edf': raise RuntimeError('injected controlled failure')
        return real(*args, **kwargs)
    monkeypatch.setattr(module, 'run_policy', fail_edf)
    out = tmp_path/'batch'; trace = 'formal_v1_cell_00_trace_00'
    first = module.run_formal(manifest, out, trajectory_ids=[trace])
    assert first['completed_policy_runs'] == 2
    module.run_formal(manifest, out, trajectory_ids=[trace], resume=True)
    module.run_formal(manifest, out, trajectory_ids=[trace], resume=True)
    rows = module.read_run_index(manifest, out/'run_index.jsonl')
    edf = [r for r in rows if r['policy_id'] == 'edf']
    assert [r['attempt'] for r in edf] == [1, 2]
    assert all(r['status'] == 'failed' for r in edf)
    assert all(r['error_type'] == 'RuntimeError' for r in edf)


def test_interruption_is_recorded_on_resume_without_overwrite(tmp_path, monkeypatch):
    import backend.formal_experiments as module
    manifest = frozen(tmp_path); real = module.run_policy
    def interrupt(*args, **kwargs): raise KeyboardInterrupt()
    monkeypatch.setattr(module, 'run_policy', interrupt)
    out = tmp_path/'batch'; trace = 'formal_v1_cell_00_trace_00'
    with pytest.raises(KeyboardInterrupt): module.run_formal(manifest, out, trajectory_ids=[trace])
    monkeypatch.setattr(module, 'run_policy', real)
    result = module.run_formal(manifest, out, trajectory_ids=[trace], resume=True)
    assert result['completed_policy_runs'] == 3
    rows = module.read_run_index(manifest, out/'run_index.jsonl')
    edf = [r for r in rows if r['policy_id'] == 'edf']
    assert [r['status'] for r in edf] == ['interrupted', 'completed']


def test_resume_rejects_result_tampering(tmp_path):
    from backend.formal_experiments import run_formal, read_run_index
    manifest = frozen(tmp_path); out = tmp_path/'batch'
    run_formal(manifest, out, trajectory_ids=['formal_v1_cell_00_trace_00'])
    row = read_run_index(manifest, out/'run_index.jsonl')[0]
    result = out/row['run_path']/'results.json'
    result.write_bytes(result.read_bytes()+b' ')
    with pytest.raises(ValueError): run_formal(manifest, out, resume=True)


def test_bad_selection_or_pending_rejected_before_batch_creation(tmp_path):
    from backend.formal_experiments import run_formal
    manifest = frozen(tmp_path)
    for selection in [[], ['unknown'], ['formal_v1_cell_00_trace_00']*2]:
        with pytest.raises(ValueError): run_formal(manifest, tmp_path/'bad', trajectory_ids=selection)
        assert not (tmp_path/'bad').exists()
    with pytest.raises(ValueError): run_formal(tmp_path/'candidate/manifest.json', tmp_path/'bad')


def test_runner_rejects_actual_horizon_different_from_frozen(tmp_path, monkeypatch):
    import copy
    import backend.formal_experiments as module
    manifest = frozen(tmp_path); original = module.run_policy
    def wrong_horizon(config, *args, **kwargs):
        config = copy.deepcopy(config); config['evaluation_end_s'] = 2.0
        return original(config, *args, **kwargs)
    monkeypatch.setattr(module, 'run_policy', wrong_horizon)
    with pytest.raises(ValueError, match='config'):
        module.run_formal(manifest, tmp_path/'batch', trajectory_ids=['formal_v1_cell_00_trace_00'])
