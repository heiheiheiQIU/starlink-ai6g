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
    for name, digest in subject['audit_files_sha256'].items():
        assert leakage['source_files']['sources/'+name] == digest
    with pytest.raises(ValueError, match='pending'):
        index(review)
    path = output/manifest['trajectories'][0]['config_path']
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):
        verify_candidate(output/'manifest.json')

@pytest.mark.parametrize("changed", [
    "scripts/prepare_formal_v2_review.py",
    "data/teacher/a_n3_20_v2/splits.json",
    "data/teacher/a_n4_pilot_v1/source_splits.json",
])
def test_pre_generation_receipts_reject_changed_audit_file(tmp_path, monkeypatch, changed):
    import shutil
    from backend import formal_v2 as v2

    # Isolate real input bytes and use a substitute seed range even on a failing implementation.
    source = v2.ROOT
    sandbox = tmp_path / "snapshot"
    def copy_input(relative):
        target = sandbox / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
        return target

    for name in ("REGISTRATION", "MODEL", "DEV", "ARCHIVE", "PILOT", "TEMPLATE", "ANALYSIS", "DESIGN"):
        monkeypatch.setattr(v2, name, copy_input(getattr(v2, name).relative_to(source)))
    for relative in ("data/teacher/sources/a_n3_20_v2.jsonl", "scripts/prepare_formal_v2_review.py",
                     "data/teacher/a_n3_20_v2/splits.json", "data/teacher/a_n4_pilot_v1/source_splits.json"):
        copy_input(relative)
    monkeypatch.setattr(v2, "ROOT", sandbox)
    reg = json.loads(v2.REGISTRATION.read_bytes())
    reg.update(seed_start=890000, seed_end=890179)
    v2.REGISTRATION.write_text(json.dumps(reg), encoding="utf-8")
    signed = v2.subject()
    receipts = {role: dict(role=role, reviewer="ci-"+role, status="accepted",
                           subject=signed, notes="Surrogate regression") for role in "ABC"}
    v2.check_receipts(receipts)
    for role, receipt in receipts.items():
        (tmp_path / (role+".json")).write_text(json.dumps(receipt), encoding="utf-8")
    with (sandbox / changed).open("ab") as stream:
        stream.write(b"\n")
    monkeypatch.setattr(v2, "expected_inputs", lambda: pytest.fail("stale receipt reached generation"))
    with pytest.raises(ValueError, match="receipt"):
        v2.materialize(tmp_path, tmp_path / "output")
    assert not (tmp_path / "output").exists()
