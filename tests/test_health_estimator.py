from pathlib import Path

from backend.health.estimator import load_health_observation_config
from training.legacy_audit import sha256_file


def test_loads_frozen_synthetic_observation_config():
    path = Path("configs/health_observation.json")
    config = load_health_observation_config(path)
    assert config.schema_version == "1.0"
    assert config.method == "synthetic_absolute_margin"
    assert config.soc_abs_error == 0.05
    assert config.capacity_abs_error_Wh == 1.0
    assert config.model_version == "synthetic-health-v1"
    assert config.config_sha256 == sha256_file(path)

import json
import pytest
from backend.health.legacy_adapter import HealthInputError


def valid_config_payload():
    return {
        "schema_version": "1.0",
        "method": "synthetic_absolute_margin",
        "soc_abs_error": 0.05,
        "capacity_abs_error_Wh": 1.0,
        "model_version": "synthetic-health-v1",
    }


@pytest.mark.parametrize(
    "payload",
    [
        valid_config_payload() | {"extra": True},
        {key: value for key, value in valid_config_payload().items() if key != "method"},
        valid_config_payload() | {"schema_version": "2.0"},
        valid_config_payload() | {"method": "gaussian"},
        valid_config_payload() | {"model_version": "unknown"},
        valid_config_payload() | {"soc_abs_error": 10**400},
        valid_config_payload() | {"capacity_abs_error_Wh": 10**400},
        valid_config_payload() | {"soc_abs_error": True},
        valid_config_payload() | {"soc_abs_error": float("nan")},
        valid_config_payload() | {"soc_abs_error": 1.01},
        valid_config_payload() | {"capacity_abs_error_Wh": -0.01},
        valid_config_payload() | {"capacity_abs_error_Wh": float("inf")},
    ],
)
def test_rejects_invalid_health_config(tmp_path, payload):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HealthInputError) as error:
        load_health_observation_config(path)
    assert error.value.code == "HEALTH_CONFIG_INVALID"


def test_missing_health_config_is_controlled_error(tmp_path):
    with pytest.raises(HealthInputError) as error:
        load_health_observation_config(tmp_path / "missing.json")
    assert error.value.code == "HEALTH_CONFIG_INVALID"


def test_rejects_integer_token_exceeding_parser_limit(tmp_path):
    path = tmp_path / "oversized.json"
    path.write_text(
        '{"schema_version":"1.0","method":"synthetic_absolute_margin",'
        '"soc_abs_error":' + "1" * 4301 + ','
        '"capacity_abs_error_Wh":1.0,"model_version":"synthetic-health-v1"}',
        encoding="utf-8",
    )
    with pytest.raises(HealthInputError) as error:
        load_health_observation_config(path)
    assert error.value.code == "HEALTH_CONFIG_INVALID"


from backend.health.estimator import estimate_health_core


def synthetic_observation(**changes):
    payload = {
        "source": "synthetic",
        "soc_observed": 0.60,
        "capacity_Wh_observed": 12.0,
        "observed_at_s": 8.0,
        "available_at_s": 10.0,
    }
    payload.update(changes)
    return payload


def test_estimates_deterministic_conservative_health_bounds():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    history = [synthetic_observation()]

    first = estimate_health_core(history, 10.0, config)
    second = estimate_health_core(history, 10.0, config)

    assert first == second
    assert first.soc_est == 0.60
    assert first.soc_lower == pytest.approx(0.55)
    assert first.capacity_Wh_est == 12.0
    assert first.capacity_lower_Wh == 11.0
    assert first.energy_lower_Wh == pytest.approx(6.05)
    assert first.observed_at_s == 8.0
    assert first.available_at_s == 10.0
    assert first.config_sha256 == config.config_sha256
    assert first.rul_est is None
    assert first.rul_unit is None
    assert first.reason_codes == (
        "SYNTHETIC_HEALTH_OBSERVATION",
        "SCENARIO_CONSERVATIVE_BOUND",
        "RUL_UNAVAILABLE",
    )


def test_energy_lower_bound_has_explicit_wh_units(tmp_path):
    payload = valid_config_payload() | {
        "soc_abs_error": 0.10,
        "capacity_abs_error_Wh": 2.0,
    }
    path = tmp_path / "units.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    config = load_health_observation_config(path)

    estimate = estimate_health_core([synthetic_observation()], 10.0, config)

    assert estimate.soc_lower == pytest.approx(0.5)
    assert estimate.capacity_lower_Wh == pytest.approx(10.0)
    assert estimate.energy_lower_Wh == pytest.approx(5.0)



def assert_health_error(code, history, now_s=10.0):
    config = load_health_observation_config(Path("configs/health_observation.json"))
    with pytest.raises(HealthInputError) as error:
        estimate_health_core(history, now_s, config)
    assert error.value.code == code


def test_unordered_history_uses_latest_available_observation():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    older = synthetic_observation(soc_observed=0.4, observed_at_s=2.0, available_at_s=3.0)
    newest = synthetic_observation(soc_observed=0.7, observed_at_s=7.0, available_at_s=9.0)

    estimate = estimate_health_core([older, newest], 9.0, config)

    assert estimate.soc_est == 0.7


def test_future_observation_does_not_change_current_estimate():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    future = synthetic_observation(soc_observed=0.99, observed_at_s=20.0, available_at_s=21.0)
    current = synthetic_observation(soc_observed=0.6)

    estimate = estimate_health_core([future, current], 10.0, config)

    assert estimate.soc_est == 0.6


def test_only_future_observation_has_no_available_result():
    assert_health_error(
        "NO_AVAILABLE_OBSERVATION",
        [synthetic_observation(observed_at_s=20.0, available_at_s=21.0)],
    )


def test_empty_history_has_no_available_result():
    assert_health_error("NO_AVAILABLE_OBSERVATION", [])


def test_latest_time_tie_is_rejected_without_input_order_guessing():
    first = synthetic_observation(soc_observed=0.6)
    second = synthetic_observation(soc_observed=0.7)
    assert_health_error("AMBIGUOUS_OBSERVATION", [first, second])



@pytest.mark.parametrize("history", [None, {}, "synthetic", ["not-a-record"]])
def test_invalid_history_shape_is_controlled(history):
    expected = "HISTORY_INVALID" if not isinstance(history, list) else "OBSERVATION_INVALID"
    assert_health_error(expected, history)


@pytest.mark.parametrize(
    "record",
    [
        synthetic_observation(source="simulation_truth"),
        synthetic_observation(soc_observed=True),
        synthetic_observation(soc_observed=float("nan")),
        synthetic_observation(soc_observed=1.1),
        synthetic_observation(capacity_Wh_observed=0.0),
        synthetic_observation(capacity_Wh_observed=float("inf")),
        synthetic_observation(observed_at_s=-1.0),
        synthetic_observation(observed_at_s=11.0, available_at_s=10.0),
        synthetic_observation() | {"soc_true": 0.9},
        synthetic_observation() | {"capacity_true_Wh": 14.0},
        synthetic_observation() | {"raw_fraction": 0.8},
    ],
)
def test_invalid_or_truth_bearing_observation_is_rejected(record):
    assert_health_error("OBSERVATION_INVALID", [record])


@pytest.mark.parametrize("now_s", [True, -1.0, float("nan"), float("inf")])
def test_invalid_now_s_is_rejected(now_s):
    assert_health_error("NOW_S_INVALID", [synthetic_observation()], now_s=now_s)


def test_invalid_config_object_is_rejected():
    with pytest.raises(HealthInputError) as error:
        estimate_health_core([synthetic_observation()], 10.0, {})
    assert error.value.code == "HEALTH_CONFIG_INVALID"

@pytest.mark.parametrize("field,value", [
    ("schema_version", "2.0"), ("method", "gaussian"), ("model_version", "unknown"),
    ("soc_abs_error", True), ("soc_abs_error", "0.1"), ("soc_abs_error", float("nan")),
    ("soc_abs_error", float("inf")), ("soc_abs_error", -0.1), ("soc_abs_error", 1.1),
    ("soc_abs_error", 10**400), ("capacity_abs_error_Wh", False),
    ("capacity_abs_error_Wh", "1"), ("capacity_abs_error_Wh", float("nan")),
    ("capacity_abs_error_Wh", float("inf")), ("capacity_abs_error_Wh", -1),
    ("capacity_abs_error_Wh", 10**400), ("config_sha256", None),
    ("config_sha256", "A" * 63), ("config_sha256", "a" * 64),
    ("config_sha256", "G" * 64), ("config_sha256", "A" * 65),
])
def test_estimate_rejects_invalid_config_contents(field, value):
    from dataclasses import replace
    config = load_health_observation_config(Path("configs/health_observation.json"))
    with pytest.raises(HealthInputError) as error:
        estimate_health_core([synthetic_observation()], 10.0, replace(config, **{field: value}))
    assert error.value.code == "HEALTH_CONFIG_INVALID"


def test_selection_is_independent_of_input_order():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    records = [synthetic_observation(soc_observed=0.4, observed_at_s=2, available_at_s=3),
               synthetic_observation(soc_observed=0.7, observed_at_s=7, available_at_s=9)]
    assert estimate_health_core(records, 10, config) == estimate_health_core(records[::-1], 10, config)
    assert estimate_health_core(records, 10, config).soc_est == 0.7


def test_availability_time_precedes_observation_time():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    records = [synthetic_observation(soc_observed=0.4, observed_at_s=8, available_at_s=9),
               synthetic_observation(soc_observed=0.7, observed_at_s=5, available_at_s=10)]
    assert estimate_health_core(records, 10, config).soc_est == 0.7


def test_observation_time_breaks_equal_availability_tie():
    config = load_health_observation_config(Path("configs/health_observation.json"))
    records = [synthetic_observation(soc_observed=0.4, observed_at_s=5, available_at_s=10),
               synthetic_observation(soc_observed=0.7, observed_at_s=8, available_at_s=10)]
    assert estimate_health_core(records, 10, config).soc_est == 0.7


def test_invalid_future_record_is_rejected_before_filtering():
    future = synthetic_observation(observed_at_s=20, available_at_s=21) | {"soc_true": 0.9}
    assert_health_error("OBSERVATION_INVALID", [synthetic_observation(), future])
