import json
from pathlib import Path

import pytest

from backend.contracts import Observation, validate_teacher_result
from backend.policies.teacher import solve_teacher
from training.build_h02_v2_source import build_source_rows, write_source
from training.generate_teacher_data import canonical_json, observation_content_sha256


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
