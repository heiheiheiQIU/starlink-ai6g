"""Catch missing time-evolved decisions and source leakage in the new pilot."""
from collections import Counter

from training.recovery_pilot import build_sources, make_splits, classify, check_disjoint
from training.generate_policy_pilot import sample_source, label_state
from training.pilot_scenarios import ROOT, sha256_json
import json
import pytest


def test_sources_capture_both_waitable_and_last_chance_states():
    sources = build_sources()
    assert len(sources) == 30
    assert len({s['content_sha256'] for s in sources}) == 30
    assert len({s['seed'] for s in sources}) == 30
    assert len({s['family'] for s in sources[:4]}) == 4
    splits = make_splits(sources)
    assert Counter(splits.values()) == {'train': 18, 'validation': 6, 'test': 6}
    config = json.loads((ROOT/'configs/teacher.json').read_text(encoding='utf-8'))
    states = sample_source(sources[0])
    assert [s['observation']['sim_time_s'] for s in states] == [0, 2]
    labels = [label_state(s, teacher_config=config, teacher_config_sha256=sha256_json(config), budget_ms=1000) for s in states]
    assert [classify(s) for s in labels] == ['tied', 'send_strictly_better']


def test_no_feasible_and_wait_better_are_distinguished():
    def row(scores):
        return {'label_eligible': True, 'candidate_scores': scores}
    assert classify(row([{'mode':'idle','score':0,'feasible':True}, {'mode':'fast','score':0,'feasible':False}])) == 'no_feasible_send'
    assert classify(row([{'mode':'idle','score':1,'feasible':True}, {'mode':'fast','score':0.5,'feasible':True}])) == 'wait_strictly_better'
    assert classify({'label_eligible':False}) == 'ineligible'


def test_disjoint_check_rejects_renamed_duplicate_and_seed_collision():
    sources = build_sources()
    old = [{**sources[0], 'source_id':'renamed'}]
    with pytest.raises(ValueError, match='overlap'):
        check_disjoint(sources, old)
    old[0]['content_sha256'] = 'different'
    with pytest.raises(ValueError, match='overlap'):
        check_disjoint(sources, old)


def test_audit_replays_labels_even_if_tamper_hash_is_refreshed(tmp_path):
    from training.recovery_pilot import generate
    from training.audit_recovery_pilot import audit
    import hashlib
    output = tmp_path/'pilot'
    generate(output)
    assert audit(output)['status'] == 'passed'
    samples = output/'samples.jsonl'
    rows = [json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    rows[0]['candidate_scores'][0]['score'] = .123456
    samples.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    manifest_path = output/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['output_sha256']['samples.jsonl'] = hashlib.sha256(samples.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):
        audit(output)


def test_audit_rejects_forged_teacher_identity_and_deleted_solver_diagnostics(tmp_path):
    from training.recovery_pilot import generate
    from training.audit_recovery_pilot import audit
    import hashlib
    output = tmp_path/'pilot'
    generate(output)
    manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    for name in ('attempts.jsonl','samples.jsonl'):
        path = output/name
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        for row in rows:
            row['teacher_config_sha256'] = '0'*64
            row['teacher_version'] = 'nonexistent-teacher-v999'
            row['diagnostics']['candidates'] = []
            row['label_content_sha256'] = sha256_json({k:v for k,v in row.items() if k not in {'label_content_sha256','elapsed_ms'}})
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        manifest['output_sha256'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError,match='teacher replay'):
        audit(output)
