import hashlib
import json
from pathlib import Path
import tempfile

import pytest

from backend.contracts import Observation, validate_teacher_result
from backend.policies.teacher import solve_teacher
from training.build_h02_v2_source import build_source_rows, write_source
from training.generate_teacher_data import (
    canonical_json,
    generate_teacher_dataset,
    label_content_sha256,
    observation_content_sha256,
)
from training.splits import build_split_manifest


ROOT = Path(__file__).resolve().parents[1]
TEACHER_CONFIG = json.loads((ROOT / "configs/teacher.json").read_text(encoding="utf-8"))


def test_source_matrix_has_twenty_independent_supported_observations():
    rows = build_source_rows()
    assert len(rows) == 20
    assert len({row["sample_id"] for row in rows}) == 20
    assert len({row["source_group_id"] for row in rows}) == 20

    run_ids = set()
    content_hashes = set()
    for row in rows:
        observation = Observation.model_validate(row["observation"])
        run_ids.add(observation.run_id)
        content_hashes.add(observation_content_sha256(row["observation"]))
        assert observation.policy_id == "teacher"
        assert observation.inflight is None
        assert 1 <= len(observation.tasks) <= 2
        assert sum(task.payload_bytes for task in observation.tasks) <= 4096
        assert observation.health.rul_est is None
        assert "RUL_UNAVAILABLE" in observation.health.reason_codes
        assert all(window.source == "synthetic" for window in observation.forecast_windows)
        assert all(point.robust_loss_prob == point.fast_loss_prob == 0.0
                   for window in observation.forecast_windows for point in window.loss_profile)
        result = validate_teacher_result(
            observation,
            solve_teacher(observation, budget_ms=1000, config=TEACHER_CONFIG),
        )
        assert result.solver_status == "OPTIMAL"
        assert result.gap == 0.0

    assert len(run_ids) == 20
    assert len(content_hashes) == 20


def test_source_writer_is_canonical_idempotent_and_immutable(tmp_path):
    target = tmp_path / "source.jsonl"
    write_source(target)
    original = target.read_bytes()
    assert original.endswith(b"\n")
    assert [json.loads(line) for line in original.splitlines()] == build_source_rows()
    assert all(line.decode("utf-8") == canonical_json(json.loads(line))
               for line in original.splitlines())

    write_source(target)
    assert target.read_bytes() == original

    target.write_text("different\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Refusing to overwrite differing source"):
        write_source(target)
    assert target.read_text(encoding="utf-8") == "different\n"


def test_frozen_v2_artifacts_regenerate_stable_labels_and_split_membership():
    source = ROOT / "data/teacher/sources/a_n3_20_v2.jsonl"
    frozen = ROOT / "data/teacher/a_n3_20_v2"
    frozen_manifest = json.loads((frozen / "manifest.json").read_text(encoding="utf-8"))
    frozen_summary = json.loads((frozen / "summary.json").read_text(encoding="utf-8"))
    frozen_splits = json.loads((frozen / "splits.json").read_text(encoding="utf-8"))
    frozen_rows = {
        row["sample_id"]: row
        for row in (json.loads(line) for line in (frozen / "samples.jsonl").read_text(
            encoding="utf-8").splitlines())
    }
    assert frozen_manifest["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    for name in ("samples.jsonl", "summary.json"):
        assert frozen_manifest["output_sha256"][name] == hashlib.sha256(
            (frozen / name).read_bytes()).hexdigest()

    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="h02_v2_regeneration_", dir=runs) as directory:
        regenerated = Path(directory) / "dataset"
        summary = generate_teacher_dataset(
            source_path=source,
            output_dir=regenerated,
            source_revision=frozen_manifest["source_revision"],
            teacher_config_path=ROOT / "configs/teacher.json",
            budget_ms=1000,
            expected_count=20,
        )
        split = build_split_manifest(
            regenerated / "samples.jsonl",
            regenerated / "splits.json",
            split_seed=20261031,
            split_counts=(12, 4, 4),
        )
        regenerated_rows = {
            row["sample_id"]: row
            for row in (json.loads(line) for line in (regenerated / "samples.jsonl").read_text(
                encoding="utf-8").splitlines())
        }

    assert summary == frozen_summary
    assert regenerated_rows.keys() == frozen_rows.keys()
    for sample_id, row in regenerated_rows.items():
        assert row["label_content_sha256"] == label_content_sha256(row)
        assert row["label_content_sha256"] == frozen_rows[sample_id]["label_content_sha256"]
    assert split["splits"] == frozen_splits["splits"]
    assert split["intersections"] == frozen_splits["intersections"]
