"""Freeze gates: receipts bind exact bytes, not a free-standing approved flag."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.formal_inputs import materialize_inputs


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False), encoding='utf-8')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_review(tmp_path, candidate=None):
    from backend.formal_freeze import freeze_binding
    if candidate is None:
        candidate = tmp_path/'candidate/manifest.json'
        materialize_inputs(Path('experiments/formal_v1/protocol.json'), candidate.parent)
    model = Path('configs/learned_policy.json')
    protocol = Path('experiments/formal_v1/analysis_protocol.json')
    binding = freeze_binding(candidate, model, protocol)
    source = write_json(tmp_path/'sources/fixture.json', {'data_scope': 'test_fixture', 'seed': 10000})
    evidence = write_json(tmp_path/'leakage.json', dict(
        schema_version='formal-leakage-review-v1', status='accepted', data_scope='test_fixture',
        candidate_manifest_sha256=binding['candidate_manifest_sha256'],
        model_artifacts_sha256=binding['model_artifacts_sha256'],
        excluded_seeds=list(range(10000, 10180)), excluded_content_hashes=[],
        source_files={'sources/fixture.json': digest(source)}, method='Synthetic isolated fixture sources; not production audit.'))
    receipts = []
    for role in 'ABC':
        path = write_json(tmp_path/f'receipt_{role}.json', dict(
            schema_version='formal-freeze-receipt-v1', role=role, reviewer=f'test-fixture-{role}',
            reviewed_at='2026-11-07T12:00:00+08:00', status='accepted', data_scope='test_fixture',
            binding=binding, leakage_sha256=digest(evidence), notes='Synthetic test receipt; not a real team signoff.'))
        receipts.append(dict(role=role, path=path.name, sha256=digest(path)))
    review = dict(schema_version='formal-freeze-review-v1', data_scope='test_fixture', binding=binding,
                  receipts=receipts, leakage=dict(path=evidence.name, sha256=digest(evidence)))
    return candidate, write_json(tmp_path/'review.json', review), model, protocol


def test_freeze_roundtrip_preserves_candidate_and_model(tmp_path):
    from backend.formal_freeze import freeze_inputs, verify_frozen
    args = make_review(tmp_path)
    before = args[0].read_bytes()
    manifest = freeze_inputs(*args, tmp_path/'frozen')
    assert manifest['status'] == 'frozen'
    assert manifest['data_scope'] == 'test_fixture'
    assert verify_frozen(tmp_path/'frozen/manifest.json') == manifest
    assert args[0].read_bytes() == before
    assert len(manifest['trajectories']) == 180
    assert (tmp_path/'frozen/candidate/manifest.json').read_bytes() == before
    assert (tmp_path/'frozen/model/weights.npz').read_bytes() == Path('artifacts/models/a_n3_policy_v1/weights.npz').read_bytes()
    with pytest.raises(ValueError, match='new'):
        freeze_inputs(*args, tmp_path/'frozen')


@pytest.mark.parametrize('bad', ['missing_role', 'pending', 'wrong_subject', 'receipt_tampered', 'seed_collision', 'content_collision', 'path_escape', 'fake_production'])
def test_freeze_rejects_unreviewed_or_wrong_subject(tmp_path, bad):
    from backend.formal_freeze import freeze_inputs
    args = make_review(tmp_path)
    review = json.loads(args[1].read_text())
    if bad == 'missing_role':
        review['receipts'].pop()
    elif bad == 'path_escape':
        review['receipts'][0]['path'] = '../escape.json'
    elif bad == 'fake_production':
        review['data_scope'] = 'formal'
    elif bad in ('seed_collision', 'content_collision'):
        path = tmp_path/'leakage.json'; evidence = json.loads(path.read_text())
        if bad == 'seed_collision': evidence['excluded_seeds'].append(200000)
        else: evidence['excluded_content_hashes'].append(json.loads(args[0].read_text())['trajectories'][0]['content_hash'])
        write_json(path, evidence); review['leakage']['sha256'] = digest(path)
    else:
        path = tmp_path/'receipt_A.json'; receipt = json.loads(path.read_text())
        if bad == 'pending': receipt['status'] = 'pending'
        elif bad == 'wrong_subject': receipt['binding']['candidate_manifest_sha256'] = '0'*64
        else: receipt['notes'] = 'changed after review'
        write_json(path, receipt)
        if bad != 'receipt_tampered': review['receipts'][0]['sha256'] = digest(path)
    write_json(args[1], review)
    with pytest.raises(ValueError): freeze_inputs(*args, tmp_path/'frozen')
    assert not (tmp_path/'frozen').exists()


@pytest.mark.parametrize('file', ['candidate/configs/formal_v1_cell_00_trace_00.json', 'model/weights.npz', 'receipts/A.json', 'analysis_protocol.json'])
def test_frozen_tampering_rejected(tmp_path, file):
    from backend.formal_freeze import freeze_inputs, verify_frozen
    freeze_inputs(*make_review(tmp_path), tmp_path/'frozen')
    path = tmp_path/'frozen'/file
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError): verify_frozen(tmp_path/'frozen/manifest.json')


def test_analysis_protocol_rejects_changed_method(tmp_path):
    from backend.formal_freeze import validate_analysis_protocol
    protocol = json.loads(Path('experiments/formal_v1/analysis_protocol.json').read_text())
    assert validate_analysis_protocol(protocol) == protocol
    for field, value in [('bootstrap_replicates', 10), ('aggregation', 'pooled'), ('max_retries', 3)]:
        altered = copy.deepcopy(protocol); altered[field] = value
        with pytest.raises(ValueError): validate_analysis_protocol(altered)


@pytest.mark.parametrize('bad', ['missing_source', 'source_tampered', 'leakage_replaced'])
def test_source_evidence_and_receipt_binding_enforced(tmp_path, bad):
    from backend.formal_freeze import freeze_inputs
    args = make_review(tmp_path)
    if bad == 'missing_source': (tmp_path/'sources/fixture.json').unlink()
    elif bad == 'source_tampered': (tmp_path/'sources/fixture.json').write_text('{}')
    else:
        path = tmp_path/'leakage.json'; value = json.loads(path.read_text())
        value['method'] = 'Changed after reviewers signed'
        write_json(path, value)
        review = json.loads(args[1].read_text()); review['leakage']['sha256'] = digest(path)
        write_json(args[1], review)
    with pytest.raises(ValueError): freeze_inputs(*args, tmp_path/'frozen')


def test_freeze_without_git_executable(tmp_path, monkeypatch):
    import backend.formal_freeze as module
    args = make_review(tmp_path)
    def missing(*args, **kwargs): raise FileNotFoundError('git')
    monkeypatch.setattr(module.subprocess, 'run', missing)
    assert module.freeze_binding(args[0], args[2], args[3])['code_revision'] is None
