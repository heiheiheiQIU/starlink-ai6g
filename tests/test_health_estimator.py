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
