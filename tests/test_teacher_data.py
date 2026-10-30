"""Independent teacher labels over the frozen public H02 observations."""

import json
import math
import hashlib
from pathlib import Path

import pytest

import training.generate_teacher_data as module
from training.generate_teacher_data import (
    TeacherDataError, canonical_json, generate_record, label_content_sha256, sha256_text,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "cccca9892086522624a5979216d7a2ab73209803"
TEACHER_CONFIG = ROOT / "configs/teacher.json"


def first_source():
    with (ROOT / "docs/evidence/B/H02_2026-10-29/samples.jsonl").open(encoding="utf-8") as stream:
        return json.loads(next(stream))


def generate(source):
    return generate_record(source, source_revision=SOURCE_REVISION,
                           budget_ms=1000, teacher_config_path=TEACHER_CONFIG)


def test_generate_record_recomputes_first_h02_label():
    source = first_source()
    before = canonical_json(source["observation"])
    record = generate(source)
    assert record["sample_id"] == source["sample_id"]
    assert record["scenario_id"] == source["observation"]["run_id"]
    assert record["state_id"] == source["sample_id"]
    assert record["solver_status"] == "OPTIMAL"
    assert record["gap"] == 0.0
    assert record["label_eligible"] is True
    assert record["exclusion_reasons"] == []
    assert record["observation"] == source["observation"]
    score_by_key = {(item["task_id"], item["mode"]): item
                    for item in record["candidate_scores"]}
    assert len(score_by_key) == len(record["candidate_scores"])
    assert score_by_key[("T1", "fast")]["score"] == 1.0
    assert score_by_key[("T1", "fast")]["feasible"] is True
    assert score_by_key[("T1", "robust")]["feasible"] is False
    assert all(math.isfinite(item["score"]) for item in record["candidate_scores"])
    assert math.isfinite(record["gap"])
    assert canonical_json(source["observation"]) == before
    assert record["label_content_sha256"] == label_content_sha256(record)
    assert record["teacher_version"] == "bounded-forecast-r4-v1"
    assert record["teacher_config_sha256"] == hashlib.sha256(TEACHER_CONFIG.read_bytes()).hexdigest()
    assert record["source_observation_sha256"] == sha256_text(before)
    assert record["source_revision"] == SOURCE_REVISION
    assert math.isfinite(record["elapsed_ms"])


def test_canonical_utf8_hash_and_stable_field_selection():
    assert canonical_json({"z": 1, "a": "中文"}) == '{"a":"中文","z":1}'
    assert sha256_text("中文") == hashlib.sha256("中文".encode("utf-8")).hexdigest()
    record = generate(first_source())
    expected_fields = (
        "sample_id", "scenario_id", "state_id", "source_revision",
        "source_observation_sha256", "observation", "teacher_version",
        "teacher_config_sha256", "candidate_scores", "solver_status",
        "gap", "diagnostics", "label_eligible", "exclusion_reasons",
    )
    expected = sha256_text(canonical_json({key: record[key] for key in expected_fields}))
    record.update(elapsed_ms=9999.0, generated_at="tomorrow", output_path="elsewhere",
                  label_content_sha256="ignored")
    assert label_content_sha256(record) == expected


def test_repeated_solve_has_stable_label_content_hash():
    left = generate(first_source())
    right = generate(first_source())
    assert left["label_content_sha256"] == right["label_content_sha256"]


@pytest.mark.parametrize("key", [
    "TRUE_CAPACITY", "Capacity_True_Wh", "future_arrivals", "actual_future_loss",
    "evaluation_truth", "Energy_True_Wh", "soc_true",
])
@pytest.mark.parametrize("nested", [False, True])
def test_rejects_hidden_truth_inside_observation(key, nested):
    source = first_source()
    if nested:
        source["observation"]["tasks"][0]["metadata"] = [{key: 1}]
    else:
        source["observation"][key] = 1
    with pytest.raises(TeacherDataError) as error:
        generate(source)
    assert error.value.code == "LEAK_FIELD"


def test_source_envelope_labels_and_truth_are_ignored():
    source = first_source()
    source.update(candidate_scores="obsolete", scenario_id="wrong", solver_status="wrong",
                  gap=float("nan"), elapsed_ms=-1, teacher_version="wrong",
                  evaluation_truth={"soc_true": 1})
    record = generate(source)
    assert record["solver_status"] == "OPTIMAL"
    assert record["scenario_id"] == source["observation"]["run_id"]
    assert record["candidate_scores"][1]["score"] == 1.0


@pytest.mark.parametrize("malformation", ["duplicate", "nan_score", "inf_score", "nan_gap", "inf_gap", "mutation"])
def test_rejects_malformed_solver_returns(monkeypatch, malformation):
    real_solver = module.solve_teacher

    def malformed(observation, **kwargs):
        result = real_solver(observation, **kwargs)
        if malformation == "duplicate":
            result.candidate_scores.append(result.candidate_scores[0])
        elif malformation.endswith("score"):
            result.candidate_scores[0].score = float(malformation.split("_")[0])
        elif malformation.endswith("gap"):
            result.gap = float(malformation.split("_")[0])
        else:
            observation.tasks[0].priority_weight += 1.0
        return result

    monkeypatch.setattr(module, "solve_teacher", malformed)
    with pytest.raises(TeacherDataError) as error:
        generate(first_source())
    expected = "OBSERVATION_MUTATED" if malformation == "mutation" else "INVALID_TEACHER_RESULT"
    assert error.value.code == expected


def test_non_optimal_real_result_is_retained_and_excluded():
    source = first_source()
    source["observation"]["forecast_windows"][0]["loss_profile"][0]["fast_loss_prob"] = 0.1
    record = generate(source)
    assert record["solver_status"] == "UNSUPPORTED_LOSS"
    assert record["gap"] is None
    assert record["label_eligible"] is False
    assert record["exclusion_reasons"]
    assert record["candidate_scores"]
