"""Frozen H02 v2 data is verified before any policy training."""

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from training.policy_dataset import (
    PolicyDataError,
    fit_normalization,
    load_frozen_dataset,
    normalise_example,
)


ROOT = Path(__file__).resolve().parents[1]


def test_loads_exact_frozen_split_and_aligns_labels_by_key():
    data = load_frozen_dataset()
    assert {name: len(rows) for name, rows in data.splits.items()} == {
        "train": 12,
        "validation": 4,
        "test": 4,
    }
    first = data.by_sample_id["h02_v2_00"]
    assert first.candidate_keys == (
        ("T1", "robust"),
        ("T1", "fast"),
        (None, "idle"),
    )
    assert first.target_scores == (0.0, 1.0, 1.0)
    assert first.target_feasible == (False, True, True)
    assert data.samples_sha256 == (
        "2df964e78a6bf6220b4c48c92b29f4838d01af13281f41f666a306e96c5b8957"
    )


def test_normalization_is_fitted_from_train_only_and_outputs_23_finite_values():
    data = load_frozen_dataset()
    expected = fit_normalization(data.splits["train"])
    assert data.normalization == expected
    assert data.normalization.source_split == "train"
    assert all(
        scale > 0.0
        for scale in (*expected.global_scale, *expected.candidate_scale)
    )
    rows = normalise_example(data.splits["validation"][0], data.normalization)
    assert len(rows) in (3, 5)
    assert all(len(row) == 23 for row in rows)
    assert all(value == value and abs(value) != float("inf") for row in rows for value in row)


def _isolated_copy(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    data = root / "data/teacher/a_n3_20_v2"
    config = root / "configs/policy_train.json"
    data.mkdir(parents=True)
    config.parent.mkdir(parents=True)
    for name in ("samples.jsonl", "summary.json", "manifest.json", "splits.json"):
        shutil.copy2(ROOT / "data/teacher/a_n3_20_v2" / name, data / name)
    payload = json.loads((ROOT / "configs/policy_train.json").read_text(encoding="utf-8"))
    config.write_text(json.dumps(payload), encoding="utf-8")
    return root, config


def test_rejects_changed_samples_before_parsing_labels(tmp_path):
    root, config = _isolated_copy(tmp_path)
    samples = root / "data/teacher/a_n3_20_v2/samples.jsonl"
    samples.write_bytes(samples.read_bytes() + b"\n")
    with pytest.raises(PolicyDataError) as error:
        load_frozen_dataset(config, root=root)
    assert error.value.code == "SOURCE_HASH"


def test_rejects_candidate_key_mismatch_even_if_outer_hashes_are_rebound(tmp_path):
    root, config = _isolated_copy(tmp_path)
    samples = root / "data/teacher/a_n3_20_v2/samples.jsonl"
    rows = [json.loads(line) for line in samples.read_text(encoding="utf-8").splitlines()]
    rows[0]["candidate_scores"].pop()
    samples.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    digest = __import__("hashlib").sha256(samples.read_bytes()).hexdigest()
    manifest_path = samples.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_sha256"]["samples.jsonl"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    split_path = samples.parent / "splits.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["source_jsonl_sha256"] = digest
    split_path.write_text(json.dumps(split), encoding="utf-8")
    with pytest.raises(PolicyDataError) as error:
        load_frozen_dataset(config, root=root)
    assert error.value.code == "CANDIDATE_KEYS"


def test_rejects_nonempty_cross_split_intersection(tmp_path):
    root, config = _isolated_copy(tmp_path)
    split_path = root / "data/teacher/a_n3_20_v2/splits.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["intersections"]["train_test"]["sample_ids"] = ["h02_v2_00"]
    split_path.write_text(json.dumps(split), encoding="utf-8")
    with pytest.raises(PolicyDataError) as error:
        load_frozen_dataset(config, root=root)
    assert error.value.code == "SPLIT_LEAKAGE"


def test_rejects_ineligible_label_even_if_outer_hashes_are_rebound(tmp_path):
    root, config = _isolated_copy(tmp_path)
    samples = root / "data/teacher/a_n3_20_v2/samples.jsonl"
    rows = [json.loads(line) for line in samples.read_text(encoding="utf-8").splitlines()]
    rows[0]["label_eligible"] = False
    samples.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    digest = __import__("hashlib").sha256(samples.read_bytes()).hexdigest()
    manifest_path = samples.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_sha256"]["samples.jsonl"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    split_path = samples.parent / "splits.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["source_jsonl_sha256"] = digest
    split_path.write_text(json.dumps(split), encoding="utf-8")
    with pytest.raises(PolicyDataError) as error:
        load_frozen_dataset(config, root=root)
    assert error.value.code == "INELIGIBLE_LABEL"


def test_fit_normalization_does_not_consume_validation_or_test_rows():
    data = load_frozen_dataset()
    altered = replace(
        data.splits["validation"][0],
        global_features=(10_000_000.0,) + data.splits["validation"][0].global_features[1:],
    )
    assert fit_normalization(data.splits["train"]) == data.normalization
    assert altered.global_features[0] != data.splits["validation"][0].global_features[0]
