"""A/C H00 review counterexamples; all payloads are non-experimental fixtures."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from backend import contracts as c


def observation_data():
    return json.loads(Path("tests/fixtures/contracts/observation.json").read_text(
        encoding="utf-8"))["examples"][0]["payload"]


def policy_result_data():
    return json.loads(Path("tests/fixtures/contracts/results.json").read_text(
        encoding="utf-8"))["examples"][0]["payload"]["by_policy"][0]


def teacher_data():
    return dict(candidate_scores=[
        dict(task_id=None, mode="idle", score=0.0, feasible=True),
        dict(task_id="T1", mode="robust", score=1.0, feasible=False),
    ], solver_status="optimal", gap=0.0, elapsed_ms=1.0)


@pytest.mark.parametrize("wire_json", [False, True], ids=["python", "json"])
@pytest.mark.parametrize("change", ["empty", "no_idle", "two_idle", "duplicate_send", "infeasible_idle"])
def test_teacher_rejects_incomplete_or_ambiguous_candidate_sets(change, wire_json):
    payload = teacher_data()
    scores = payload["candidate_scores"]
    if change == "empty":
        scores.clear()
    elif change == "no_idle":
        scores.pop(0)
    elif change == "two_idle":
        # Different score must not evade uniqueness of the (task_id, mode) key.
        scores.append(dict(scores[0], score=2.0))
    elif change == "duplicate_send":
        scores.append(dict(scores[1], score=2.0, feasible=True))
    else:
        scores[0]["feasible"] = False
    with pytest.raises(ValidationError):
        if wire_json:
            c.TeacherResult.model_validate_json(json.dumps(payload))
        else:
            c.TeacherResult.model_validate(payload)


@pytest.mark.parametrize("idle_only", [False, True])
def test_teacher_preserves_valid_idle_and_infeasible_send_labels(idle_only):
    payload = teacher_data()
    if idle_only:
        payload["candidate_scores"] = payload["candidate_scores"][:1]
    assert c.TeacherResult.model_validate(payload).model_dump() == payload


@pytest.mark.parametrize("as_model", [False, True])
def test_teacher_boundary_rejects_candidates_outside_visible_queue(as_model):
    payload = teacher_data()
    payload["candidate_scores"][1]["task_id"] = "FUTURE_TASK"
    result = c.TeacherResult.model_validate(payload) if as_model else payload
    with pytest.raises(c.ContractViolation) as error:
        c.validate_teacher_result(c.Observation.model_validate(observation_data()), result)
    assert error.value.code == "INVALID_TEACHER_RESULT"


@pytest.mark.parametrize("change", ["missing_idle", "mutated_idle", "mutated_observation"])
def test_teacher_boundary_revalidates_models_and_returns_controlled_errors(change):
    obs = c.Observation.model_validate(observation_data())
    result = c.TeacherResult.model_validate(teacher_data())
    if change == "missing_idle":
        result = teacher_data()
        result["candidate_scores"].pop(0)
    elif change == "mutated_idle":
        result.candidate_scores[0].feasible = False
    else:
        obs.forecast_windows[0].forecast_version = "unavailable_batch"
    with pytest.raises(c.ContractViolation) as error:
        c.validate_teacher_result(obs, result)
    assert error.value.code == "INVALID_TEACHER_RESULT"


@pytest.mark.parametrize("empty_queue", [False, True])
def test_teacher_boundary_preserves_valid_inputs_without_mutation(empty_queue):
    obs_data, result_data = observation_data(), teacher_data()
    if empty_queue:
        obs_data["tasks"] = []
        obs_data["cache_bytes"] = 0
        result_data["candidate_scores"] = result_data["candidate_scores"][:1]
    obs = c.Observation.model_validate(obs_data)
    result = c.validate_teacher_result(obs, result_data)
    assert isinstance(result, c.TeacherResult)
    assert result.model_dump() == result_data
    assert obs.model_dump() == obs_data


@pytest.mark.parametrize("wire_json", [False, True], ids=["python", "json"])
@pytest.mark.parametrize("change", ["one_of_two", "all"])
def test_observation_rejects_windows_from_another_forecast_batch(change, wire_json):
    payload = observation_data()
    second = copy.deepcopy(payload["forecast_windows"][0])
    second["window_id"] = "W2"
    second["forecast_version"] = "other_batch"
    payload["forecast_windows"].append(second)
    if change == "all":
        payload["forecast_windows"][0]["forecast_version"] = "other_batch"
    with pytest.raises(ValidationError):
        if wire_json:
            c.Observation.model_validate_json(json.dumps(payload))
        else:
            c.Observation.model_validate(payload)


@pytest.mark.parametrize("window_count", [0, 1, 2])
def test_observation_keeps_batch_id_with_zero_or_multiple_matching_windows(window_count):
    payload = observation_data()
    if window_count == 0:
        payload["forecast_windows"] = []
    elif window_count == 2:
        second = copy.deepcopy(payload["forecast_windows"][0])
        second["window_id"] = "W2"
        payload["forecast_windows"].append(second)
    assert c.Observation.model_validate(payload).model_dump() == payload


@pytest.mark.parametrize("metric,value", [
    ("weighted_on_time_rate", 0.0), ("critical_task_success_rate", 0.0),
    ("goodput_bps", 0.0), ("minimum_soc_true", 0.0),
    ("energy_violation_count", 0), ("energy_violation_duration_s", 0.0),
    ("joule_per_success_bit", 0.0), ("wait_p50_s", 0.0), ("wait_p95_s", 0.0),
    ("decision_p50_ms", 0.0), ("decision_p95_ms", 0.0), ("timeout_rate", 0.0),
    ("parameter_count", 0), ("memory_bytes", 0),
])
def test_measured_metrics_cannot_also_have_missing_value_reasons(metric, value):
    payload = policy_result_data()
    payload[metric] = value
    payload["metric_reasons"][metric] = "NO_DATA"
    with pytest.raises(ValidationError):
        c.PolicyResult.model_validate_json(json.dumps(payload))


def test_zero_measurement_and_null_with_reason_remain_distinct():
    payload = policy_result_data()
    payload["goodput_bps"] = 0.0
    assert c.PolicyResult.model_validate(payload).goodput_bps == 0.0
    payload["goodput_bps"] = None
    payload["metric_reasons"]["goodput_bps"] = "NO_DATA"
    assert c.PolicyResult.model_validate(payload).goodput_bps is None
    payload["metric_reasons"].pop("goodput_bps")
    with pytest.raises(ValidationError):
        c.PolicyResult.model_validate(payload)


def test_schema_rejects_empty_teacher_candidates():
    schema = c.contract_schema()
    validator = Draft202012Validator({"$ref": "#/$defs/TeacherResult", "$defs": schema["$defs"]})
    payload = teacher_data()
    payload["candidate_scores"] = []
    assert not validator.is_valid(payload)
