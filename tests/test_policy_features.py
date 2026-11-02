"""The policy leakage boundary consumes public observations, never labels."""

import copy
from dataclasses import FrozenInstanceError, fields
import inspect
import json
from pathlib import Path
import struct

import pytest
from pydantic import ValidationError

from backend.contracts import Observation
from training.policy_features import (
    CANDIDATE_FEATURE_NAMES, GLOBAL_FEATURE_NAMES, EncodedObservation,
    PolicyFeatureError, encode_observation,
)


GLOBAL_NAMES = (
    "sim_time_s", "cache_bytes", "energy_lower_Wh", "soc_lower",
    "capacity_lower_Wh", "visible_task_count", "inflight_present",
    "next_window_start_delta_s", "next_window_duration_s",
    "next_robust_bps", "next_fast_bps", "next_robust_loss_prob",
    "next_fast_loss_prob", "has_forecast_window",
)
CANDIDATE_NAMES = (
    "is_idle", "is_robust", "is_fast", "time_since_arrival_s",
    "time_to_deadline_s", "payload_bytes", "remaining_bytes",
    "remaining_fraction", "priority_weight",
)


def payload():
    fixture = Path(__file__).parent / "fixtures/contracts/observation.json"
    return json.loads(fixture.read_text(encoding="utf-8"))["examples"][0]["payload"]


def observation(**updates):
    data = payload()
    data.update(updates)
    return Observation.model_validate(data)


def window(start, end, name):
    value = copy.deepcopy(payload()["forecast_windows"][0])
    value.update(window_id=name, start_s=start, end_s=end)
    value["rate_profile"] = [
        dict(time_s=start, robust_bps=100.0, fast_bps=200.0),
        dict(time_s=start + 2.0, robust_bps=300.0, fast_bps=400.0),
        dict(time_s=end - 1.0, robust_bps=500.0, fast_bps=600.0),
    ]
    value["loss_profile"] = [
        dict(time_s=start, robust_loss_prob=0.1, fast_loss_prob=0.2),
        dict(time_s=start + 3.0, robust_loss_prob=0.3, fast_loss_prob=0.4),
    ]
    return value


def test_exact_public_contract_raw_features_and_immutability():
    obs = observation(sim_time_s=5.0)
    before = obs.model_dump_json()
    result = encode_observation(obs)
    assert isinstance(result, EncodedObservation)
    assert result.schema_version == "policy-features-v1"
    assert tuple(field.name for field in fields(result)) == (
        "schema_version", "global_feature_names", "candidate_feature_names",
        "candidate_keys", "global_features", "candidate_features", "candidate_mask",
    )
    assert GLOBAL_FEATURE_NAMES == result.global_feature_names == GLOBAL_NAMES
    assert CANDIDATE_FEATURE_NAMES == result.candidate_feature_names == CANDIDATE_NAMES
    assert result.candidate_keys == (("T1", "robust"), ("T1", "fast"), (None, "idle"))
    assert result.global_features == (
        5.0, 2048.0, 4.0, 0.5, 8.0, 1.0, 0.0,
        0.0, 20.0, 8192.0, 16384.0, 0.1, 0.2, 1.0,
    )
    assert result.candidate_features == (
        (0.0, 1.0, 0.0, 5.0, 15.0, 2048.0, 2048.0, 1.0, 2.0),
        (0.0, 0.0, 1.0, 5.0, 15.0, 2048.0, 2048.0, 1.0, 2.0),
        (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    assert result.candidate_mask == (True, True, True)
    for value in (result.global_features, *result.candidate_features):
        assert type(value) is tuple
        assert all(type(item) is float for item in value)
    assert type(result.candidate_keys) is tuple
    assert all(type(key) is tuple for key in result.candidate_keys)
    assert type(result.candidate_features) is tuple
    assert type(result.candidate_mask) is tuple
    assert all(type(item) is bool for item in result.candidate_mask)
    with pytest.raises(FrozenInstanceError):
        result.schema_version = "changed"
    assert obs.model_dump_json() == before


def test_empty_queue_no_forecast_has_only_available_idle():
    result = encode_observation(observation(tasks=[], forecast_windows=[]))
    assert result.candidate_keys == ((None, "idle"),)
    assert result.candidate_mask == (True,)
    assert result.candidate_features == ((1.0,) + (0.0,) * 8,)
    assert result.global_features[5:] == (0.0,) * 9


@pytest.mark.parametrize("now, expected", [
    (1.0, (1.0, 10.0, 100.0, 200.0, 0.1, 0.2, 1.0)),
    (4.0, (0.0, 10.0, 300.0, 400.0, 0.1, 0.2, 1.0)),
    (5.0, (0.0, 10.0, 300.0, 400.0, 0.3, 0.4, 1.0)),
    (12.0, (8.0, 10.0, 100.0, 200.0, 0.1, 0.2, 1.0)),
    (30.0, (0.0,) * 7),
])
def test_next_window_and_latest_profiles_use_public_time(now, expected):
    obs = observation(sim_time_s=now, forecast_windows=[
        window(20.0, 30.0, "late"), window(2.0, 12.0, "early"),
    ])
    assert encode_observation(obs).global_features[7:] == expected


def test_task_sorting_remaining_fraction_and_structural_mask():
    task = payload()["tasks"][0]
    tasks = [dict(task, task_id="T2", deadline_s=10.0, remaining_bytes=512),
             dict(task, task_id="T1", deadline_s=9.0),
             dict(task, task_id="T10", remaining_bytes=0)]
    obs = observation(sim_time_s=10.0, tasks=tasks, forecast_windows=[])
    result = encode_observation(obs)
    assert result.candidate_keys == (
        ("T1", "robust"), ("T1", "fast"), ("T10", "robust"),
        ("T10", "fast"), ("T2", "robust"), ("T2", "fast"), (None, "idle"),
    )
    assert result.candidate_mask == (False, False, False, False, True, True, True)
    assert result.candidate_features[0][4] == -1.0
    assert result.candidate_features[4][7] == 0.25
    assert result == encode_observation(observation(
        sim_time_s=10.0, tasks=list(reversed(tasks)), forecast_windows=[]))


def test_inflight_disables_both_modes_but_never_idle():
    inflight = dict(task_id="T1", block_id=0, payload_bytes=1024, mode="fast",
                    sent_at_s=0.0, timeout_at_s=2.0, retries=0)
    result = encode_observation(observation(inflight=inflight))
    assert result.candidate_mask == (False, False, True)
    assert result.global_features[6] == 1.0


def test_mask_ignores_energy_rates_and_losses():
    data = payload()
    data["health"].update(soc_lower=0.0, energy_lower_Wh=0.0)
    data["forecast_windows"][0]["rate_profile"][0].update(robust_bps=0.0, fast_bps=0.0)
    data["forecast_windows"][0]["loss_profile"][0].update(
        robust_loss_prob=1.0, fast_loss_prob=1.0)
    assert encode_observation(Observation.model_validate(data)).candidate_mask == (True, True, True)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("field", ["sim_time_s", "priority_weight", "robust_bps", "soc_lower"])
def test_encoder_defensively_rejects_nonfinite_mutated_instances(invalid, field):
    obs = observation()
    target = {"sim_time_s": obs, "priority_weight": obs.tasks[0],
              "robust_bps": obs.forecast_windows[0].rate_profile[0],
              "soc_lower": obs.health}[field]
    # Upstream validation stays intact; assignment deliberately bypasses it here.
    setattr(target, field, invalid)
    with pytest.raises(ValidationError):
        Observation.model_validate(obs)
    with pytest.raises(PolicyFeatureError):
        encode_observation(obs)


@pytest.mark.parametrize("kind", ["schema", "negative", "duplicate", "zero_payload", "wrong_type"])
def test_schema_violations_are_controlled(kind):
    obs = observation()
    if kind == "schema":
        obs.schema_version = "unsupported"
    elif kind == "negative":
        obs.cache_bytes = -1
    elif kind == "duplicate":
        obs.tasks.append(obs.tasks[0].model_copy(deep=True))
    elif kind == "zero_payload":
        obs.tasks[0].payload_bytes = 0
    else:
        obs = obs.model_dump()
    with pytest.raises(PolicyFeatureError):
        encode_observation(obs)


def test_finite_input_that_overflows_float_output_is_controlled():
    obs = observation(cache_bytes=10 ** 400)
    with pytest.raises(PolicyFeatureError):
        encode_observation(obs)


def test_labels_cannot_influence_encoded_bytes_or_be_passed_to_encoder():
    obs = observation()
    labels = {"candidate_scores": [dict(task_id=task_id, mode=mode, score=0.0, feasible=True)
              for task_id, mode in (("T1", "robust"), ("T1", "fast"), (None, "idle"))]}

    def encoded_bytes():
        result = encode_observation(obs)
        floats = result.global_features + tuple(x for row in result.candidate_features for x in row)
        return (struct.pack(f"!{len(floats)}d", *floats), bytes(result.candidate_mask))

    before = encoded_bytes()
    for item in labels["candidate_scores"]:
        item.update(score=987654.0, feasible=False)
    assert encoded_bytes() == before
    assert tuple(inspect.signature(encode_observation).parameters) == ("observation",)
    with pytest.raises(TypeError):
        encode_observation(obs, labels)
    with pytest.raises(TypeError):
        encode_observation(obs, teacher_result=labels)
