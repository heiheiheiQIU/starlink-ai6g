import json
from pathlib import Path

import pytest


def test_old_matrix_cannot_be_promoted_to_formal():
    from backend.formal_freeze import check_population
    old = json.loads(Path('experiments/formal_v1/input_manifest.json').read_text())
    with pytest.raises(ValueError, match='engineering_regression_v1'):
        check_population('formal', old)


def test_generation_needs_three_receipts_before_creating_files(tmp_path):
    from backend.formal_v2 import materialize
    with pytest.raises(ValueError, match='receipt'):
        materialize(tmp_path, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_registered_seeds_disjoint_from_all_known_seed_records():
    from backend.formal_v2 import isolation
    proof = isolation()
    assert proof['registered_count'] == 180
    assert proof['overlap'] == []
    assert proof['retired_count'] == 180


def test_surrogate_generation_verified_and_tamper_rejected(tmp_path, monkeypatch):
    # Exercise the generator on a substitute range. Never materialize the registered holdout in CI.
    from backend import formal_v2 as v2
    from backend.formal_freeze import verify_candidate
    reg = json.loads(v2.REGISTRATION.read_text())
    reg.update(seed_start=890000, seed_end=890179)
    surrogate = tmp_path/'surrogate.json'
    surrogate.write_text(json.dumps(reg))
    monkeypatch.setattr(v2, 'REGISTRATION', surrogate)
    subject = v2.subject()
    for role in 'ABC':
        (tmp_path/f'{role}.json').write_text(json.dumps(dict(role=role, reviewer='ci-'+role,
            status='accepted', subject=subject, notes='Synthetic CI using substitute range')))
    output = tmp_path/'generated'
    v2.materialize(tmp_path, output)
    manifest = verify_candidate(output/'manifest.json')
    assert len(manifest['trajectories']) == 180
    from backend.formal_freeze import freeze_inputs, verify_frozen
    from tests.test_formal_freeze import make_review
    args = make_review(tmp_path, output/'manifest.json')
    freeze_inputs(*args, tmp_path/'envelope')
    verified = verify_frozen(tmp_path/'envelope/manifest.json')
    assert verified['trajectories'] == manifest['trajectories']
    from scripts.prepare_formal_v2_review import prepare, index
    review = tmp_path/'post_generation'
    prepare(output/'manifest.json', review)
    leakage = json.loads((review/'leakage.json').read_text())
    assert set(range(200000,200180)).issubset(leakage['excluded_seeds'])
    assert leakage['status'] == 'pending'
    with pytest.raises(ValueError, match='pending'):
        index(review)
    path = output/manifest['trajectories'][0]['config_path']
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):
        verify_candidate(output/'manifest.json')
