"""H00: hand-checked boundary cases, not simulation or measured results."""

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from backend import contracts as c


def task_data():
    return dict(task_id="T1", arrival_s=0.0, deadline_s=20.0,
                payload_bytes=2048, remaining_bytes=2048, priority_weight=2.0,
                business_class="periodic", data_location="satellite_1")


def health_data():
    return dict(soc_est=0.6, soc_lower=0.5, capacity_Wh_est=10.0,
                capacity_lower_Wh=8.0, energy_lower_Wh=4.0,
                rul_est=None, rul_unit=None, uncertainty_method="synthetic_bounds",
                model_version="synthetic_v1", observed_at_s=0.0,
                available_at_s=0.0, reason_codes=["RUL_UNAVAILABLE"])


def window_data():
    return dict(window_id="W1", start_s=0.0, end_s=20.0,
                rate_profile=[dict(time_s=0.0, robust_bps=8192.0, fast_bps=16384.0)],
                loss_profile=[dict(time_s=0.0, robust_loss_prob=0.1, fast_loss_prob=0.2)],
                source="synthetic", forecast_version="forecast_v1")


def observation_data():
    return dict(schema_version="1.0", run_id="fixture_run", policy_id="edf",
                sim_time_s=0.0, tasks=[task_data()], forecast_windows=[window_data()],
                health=health_data(), inflight=None, cache_bytes=2048,
                forecast_version="forecast_v1")


def scores_data():
    return [dict(task_id=None, mode="idle", score=0.0),
            dict(task_id="T1", mode="robust", score=1.0)]


def decision_data():
    return dict(action=dict(task_id=None, mode="idle", scheduled_bytes=0,
                            reason_codes=["NO_VISIBLE_WINDOW"], fallback=False),
                candidate_scores=scores_data(), constraint_checks=[
                    dict(code="NO_VISIBLE_WINDOW", passed=False, details={})],
                decision_latency_ms=0.1, fallback=False,
                model_version=None, policy_version="edf_v1")


def event_data(event_id=1, policy_id="edf", sim_time_s=0.0):
    return dict(event_id=event_id, run_id="fixture_run", policy_id=policy_id,
                sim_time_s=sim_time_s, event_type="arrived", task_id="T1", block_id=None,
                payload_bytes=2048, overhead_bytes=0, energy_Wh=0.0,
                reason_code=None, data=None)


@pytest.mark.parametrize("field,value", [
    ("payload_bytes", -1), ("payload_bytes", 0), ("payload_bytes", True),
    ("payload_bytes", 1.5), ("payload_bytes", "2048"),
    ("remaining_bytes", -1), ("remaining_bytes", 2049),
    ("deadline_s", 0.0), ("deadline_s", float("nan")),
    ("priority_weight", 0.0), ("priority_weight", float("inf")),
    ("data_location", "ground"), ("task_id", ""),
])
def test_task_rejects_invalid_units_and_boundaries(field, value):
    payload = task_data()
    payload[field] = value
    with pytest.raises(ValidationError):
        c.Task.model_validate(payload)


def test_valid_task_round_trip_preserves_bytes_and_deadline():
    task = c.Task.model_validate_json(json.dumps(task_data()))
    assert task.payload_bytes == 2048
    assert task.deadline_s == 20.0
    assert json.loads(task.model_dump_json()) == task_data()


@pytest.mark.parametrize("change", [
    {"soc_lower": 0.7}, {"soc_est": 1.1}, {"capacity_Wh_est": 0.0},
    {"capacity_lower_Wh": 11.0}, {"energy_lower_Wh": 5.0},
    {"reason_codes": []}, {"observed_at_s": 2.0, "available_at_s": 1.0},
    {"rul_est": 12.0, "rul_unit": None}, {"soc_est": float("nan")},
])
def test_health_rejects_inconsistent_or_unexplained_bounds(change):
    payload = health_data() | change
    with pytest.raises(ValidationError):
        c.HealthEstimate.model_validate(payload)


def test_missing_rul_stays_null_instead_of_becoming_zero():
    health = c.HealthEstimate.model_validate(health_data())
    assert health.model_dump()["rul_est"] is None
    assert health.energy_lower_Wh == 4.0
    assert health.reason_codes == ["RUL_UNAVAILABLE"]


def test_existing_model_instances_are_revalidated_at_contract_boundary():
    obs = c.Observation.model_validate(observation_data())
    # Pydantic's model_copy(update=...) deliberately bypasses validation.
    # A boundary must not trust an instance just because its class is correct.
    obs.health = obs.health.model_copy(update={"soc_lower": 0.8})
    with pytest.raises(ValidationError):
        c.Observation.model_validate(obs)


def test_observation_rejects_truth_bearing_task_subclasses():
    class LeakyTask(c.Task):
        received_at_gateway: bool

    payload = observation_data()
    payload["tasks"] = [LeakyTask.model_validate(task_data() | {"received_at_gateway": True})]
    with pytest.raises(ValidationError):
        c.Observation.model_validate(payload)


@pytest.mark.parametrize("kind,value", [
    ("loss", -0.1), ("loss", 1.1), ("rate", -1.0), ("rate", float("inf")),
    ("end", 0.0), ("profile_start", 1.0), ("profile_time", 20.0),
    ("duplicate_time", 0.0),
])
def test_window_rejects_bad_profiles(kind, value):
    payload = window_data()
    if kind == "loss":
        payload["loss_profile"][0]["fast_loss_prob"] = value
    elif kind == "rate":
        payload["rate_profile"][0]["fast_bps"] = value
    elif kind == "end":
        payload["end_s"] = value
    elif kind == "profile_start":
        payload["rate_profile"][0]["time_s"] = value
    else:
        payload["rate_profile"].append(dict(time_s=value, robust_bps=8192.0, fast_bps=16384.0))
    with pytest.raises(ValidationError):
        c.Window.model_validate(payload)


@pytest.mark.parametrize("where,key", [
    ("top", "true_capacity"), ("top", "future_arrivals"),
    ("top", "actual_future_loss"), ("health", "capacity_true_Wh"),
    ("task", "received_at_gateway"), ("window", "actual_future_loss"),
    ("inflight", "received_at_gateway"),
])
def test_observation_rejects_hidden_truth_at_nested_boundaries(where, key):
    payload = observation_data()
    if where == "top":
        target = payload
    elif where == "health":
        target = payload["health"]
    elif where == "task":
        target = payload["tasks"][0]
    elif where == "window":
        target = payload["forecast_windows"][0]
    else:
        payload["inflight"] = dict(task_id="T1", block_id=0, payload_bytes=1024,
                                   mode="robust", sent_at_s=0.0, timeout_at_s=2.0, retries=0)
        target = payload["inflight"]
    target[key] = 1.0
    with pytest.raises(ValidationError):
        c.Observation.model_validate(payload)


@pytest.mark.parametrize("change", ["future_health", "future_task", "duplicate_task", "duplicate_window"])
def test_observation_rejects_unavailable_or_ambiguous_inputs(change):
    payload = observation_data()
    if change == "future_health":
        payload["health"]["available_at_s"] = 1.0
    elif change == "future_task":
        payload["tasks"][0]["arrival_s"] = 1.0
    elif change == "duplicate_task":
        payload["tasks"].append(copy.deepcopy(payload["tasks"][0]))
    else:
        payload["forecast_windows"].append(copy.deepcopy(payload["forecast_windows"][0]))
    with pytest.raises(ValidationError):
        c.Observation.model_validate(payload)


@pytest.mark.parametrize("change", ["no_idle", "two_idle", "duplicate", "unknown_task", "nan", "infinity"])
def test_full_candidate_validation_rejects_unsafe_scores(change):
    scores = scores_data()
    if change == "no_idle":
        scores.pop(0)
    elif change in {"two_idle", "duplicate"}:
        scores.append(copy.deepcopy(scores[0 if change == "two_idle" else 1]))
    elif change == "unknown_task":
        scores[1]["task_id"] = "FUTURE_TASK"
    else:
        scores[1]["score"] = float("nan" if change == "nan" else "inf")
    with pytest.raises(c.ContractViolation) as error:
        c.validate_candidate_scores(c.Observation.model_validate(observation_data()), scores)
    assert error.value.code == "INVALID_SCORE"


def test_valid_full_scores_and_empty_queue_idle_do_not_mutate_observation():
    payload = observation_data()
    obs = c.Observation.model_validate(payload)
    scores = c.validate_candidate_scores(obs, scores_data())
    assert len(scores) == 2
    assert obs.model_dump() == payload
    payload["tasks"] = []
    payload["cache_bytes"] = 0
    assert c.validate_candidate_scores(c.Observation.model_validate(payload), scores_data()[:1])[0].mode == "idle"


@pytest.mark.parametrize("change", [
    {"scheduled_bytes": 1}, {"task_id": "T1"},
    {"mode": "fast", "task_id": "T1", "scheduled_bytes": 0},
    {"mode": "fast", "task_id": "T1", "scheduled_bytes": 1025},
])
def test_action_rejects_idle_and_block_size_inconsistencies(change):
    payload = decision_data()["action"] | change
    with pytest.raises(ValidationError):
        c.Action.model_validate(payload)


def test_decision_event_maps_latency_without_silent_aliases():
    decision = c.Decision.model_validate(decision_data())
    wire = decision.to_event_data().model_dump()
    assert wire["latency_ms"] == 0.1
    assert "decision_latency_ms" not in wire
    assert decision.decision_latency_ms == 0.1
    assert wire["candidate_scores"][1]["task_id"] == "T1"
    wrong_wire = dict(wire, decision_latency_ms=0.1)
    with pytest.raises(ValidationError):
        c.DecisionData.model_validate(wrong_wire)


def test_decision_rejects_disagreeing_fallback_flags():
    with pytest.raises(ValidationError):
        c.Decision.model_validate(decision_data() | {"fallback": True})


def test_event_type_controls_payload_and_truth_is_explicitly_posthoc():
    payload = event_data() | dict(event_type="decision", data=c.Decision.model_validate(decision_data()).to_event_data().model_dump())
    assert c.Event.model_validate(payload).data.latency_ms == 0.1
    with pytest.raises(ValidationError):
        c.Event.model_validate(payload | {"event_type": "snapshot"})
    with pytest.raises(ValidationError):
        c.Event.model_validate(event_data() | {"data": payload["data"]})
    with pytest.raises(ValidationError):
        c.EvaluationTruth.model_validate(dict(label="live", soc_true=0.5, energy_true_Wh=5.0, capacity_true_Wh=10.0))


def test_event_pages_order_by_global_id_not_cross_policy_time():
    page = dict(run_id="fixture_run", events=[event_data(1, "edf", 9.0), event_data(2, "value", 0.0)], next_after=2, has_more=False)
    assert c.EventsPage.model_validate(page).next_after == 2
    for bad_events in ([event_data(2), event_data(1)], [event_data(1), event_data(1)]):
        with pytest.raises(ValidationError):
            c.EventsPage.model_validate(page | {"events": bad_events})
    with pytest.raises(ValidationError):
        c.EventsPage.model_validate(page | {"next_after": 1})
    with pytest.raises(ValidationError):
        c.EventsPage.model_validate(page | {"run_id": "another_run"})
    assert c.EventsPage.model_validate(dict(run_id="fixture_run", events=[], next_after=2, has_more=False)).next_after == 2


@pytest.mark.parametrize("kwargs", [{"after": -1}, {"after": True}, {"limit": 0}, {"limit": 2001}, {"limit": 1.5}])
def test_event_query_rejects_invalid_cursor_and_limit(kwargs):
    with pytest.raises(ValidationError):
        c.EventsQuery.model_validate(kwargs)


def test_event_query_defaults_and_maximum():
    assert c.EventsQuery().model_dump() == {"after": 0, "limit": 500}
    assert c.EventsQuery(limit=2000).limit == 2000


@pytest.mark.parametrize("policy_ids", [[], ["edf", "edf"], ["edf", "value", "ai"]])
def test_run_request_rejects_invalid_policy_comparisons(policy_ids):
    with pytest.raises(ValidationError):
        c.RunRequest.model_validate(dict(schema_version="1.0", config={}, policy_ids=policy_ids, seed=0))


def test_run_request_rejects_nonfinite_nested_configuration():
    with pytest.raises(ValidationError):
        c.RunRequest.model_validate(dict(schema_version="1.0", config={"nested": [float("nan")]}, policy_ids=["edf"], seed=0))


def test_schema_is_reproducible_and_checks_real_wire_boundaries():
    schema = json.loads(Path("configs/schema.json").read_text(encoding="utf-8"))
    assert schema == c.contract_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator({"$ref": "#/$defs/Observation", "$defs": schema["$defs"]})
    validator.validate(observation_data())
    malformed = observation_data()
    malformed["health"]["capacity_true_Wh"] = 10.0
    assert not validator.is_valid(malformed)
    malformed = observation_data()
    malformed["tasks"][0]["payload_bytes"] = "2048"
    assert not validator.is_valid(malformed)


def test_schema_export_uses_portable_lf_for_handoff_hashes(tmp_path):
    destination = tmp_path / "schema.json"
    result = subprocess.run(
        [sys.executable, "-m", "backend.contracts", "--schema-output", str(destination)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    raw = destination.read_bytes()
    assert b"\r\n" not in raw, "Windows CRLF must not change hashes after Git's LF normalization"
    assert json.loads(raw) == c.contract_schema()


def test_fixture_catalog_validates_both_python_and_json_schema():
    root = Path("tests/fixtures/contracts")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    schema = c.contract_schema()
    covered = set()
    for entry in manifest["files"]:
        fixture = json.loads((root / entry["path"]).read_text(encoding="utf-8"))
        assert fixture["kind"] == "contract_fixture"
        assert fixture["is_experimental_result"] is False
        for example in fixture["examples"]:
            model = c.PUBLIC_MODELS[example["type"]]
            validator = Draft202012Validator({"$ref": f"#/$defs/{example['type']}", "$defs": schema["$defs"]})
            if example["valid"]:
                validator.validate(example["payload"])
                model.model_validate(example["payload"])
            else:
                with pytest.raises(ValidationError):
                    model.model_validate(example["payload"])
                if example.get("schema_rejects", True):
                    assert not validator.is_valid(example["payload"])
        if fixture.get("scenario_id"):
            covered.add(fixture["scenario_id"])
    assert covered == {"empty_queue", "no_window", "low_energy", "ack_loss", "model_failure", "page_refresh"}


def test_completed_results_require_missing_metric_reasons_and_unique_policies():
    fixture = json.loads(Path("tests/fixtures/contracts/results.json").read_text(encoding="utf-8"))
    payload = fixture["examples"][0]["payload"]
    assert c.RunResult.model_validate(payload).status == "completed"
    with pytest.raises(ValidationError):
        c.RunResult.model_validate(payload | {"status": "failed"})
    duplicate = copy.deepcopy(payload)
    duplicate["by_policy"].append(copy.deepcopy(duplicate["by_policy"][0]))
    with pytest.raises(ValidationError):
        c.RunResult.model_validate(duplicate)
    unexplained = copy.deepcopy(payload)
    unexplained["by_policy"][0]["metric_reasons"] = {}
    with pytest.raises(ValidationError):
        c.RunResult.model_validate(unexplained)


def test_teacher_gap_and_scores_cannot_disguise_nonfinite_values():
    payload = dict(candidate_scores=[dict(task_id=None, mode="idle", score=0.0, feasible=True)],
                   solver_status="timeout", gap=None, elapsed_ms=200.0)
    assert c.TeacherResult.model_validate(payload).gap is None
    with pytest.raises(ValidationError):
        c.TeacherResult.model_validate(payload | {"gap": -1.0})
    with pytest.raises(ValidationError):
        c.TeacherResult.model_validate(payload | {"elapsed_ms": float("inf")})
