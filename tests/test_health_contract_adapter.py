from dataclasses import replace
from pathlib import Path

import pytest

import backend.health.estimator as estimator
from backend.contracts import HealthEstimate
from backend.health.legacy_adapter import HealthInputError


def synthetic_observation(**changes):
    payload = {"source": "synthetic", "soc_observed": 0.60, "capacity_Wh_observed": 12.0,
               "observed_at_s": 8.0, "available_at_s": 10.0}
    payload.update(changes)
    return payload


def test_formal_entry_returns_frozen_health_estimate():
    result = estimator.estimate_health([synthetic_observation()], 10.0)
    assert isinstance(result, HealthEstimate)
    assert result.model_dump() == {
        "soc_est": 0.60, "soc_lower": pytest.approx(0.55), "capacity_Wh_est": 12.0,
        "capacity_lower_Wh": 11.0, "energy_lower_Wh": pytest.approx(6.05), "rul_est": None,
        "rul_unit": None, "uncertainty_method": "synthetic_absolute_margin",
        "model_version": "synthetic-health-v1", "observed_at_s": 8.0, "available_at_s": 10.0,
        "reason_codes": ["SYNTHETIC_HEALTH_OBSERVATION", "SCENARIO_CONSERVATIVE_BOUND", "RUL_UNAVAILABLE"],
    }


def test_formal_entry_resolves_config_outside_repository_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert estimator.estimate_health([synthetic_observation()], 10.0).model_version == "synthetic-health-v1"


def test_formal_entry_is_deterministic():
    history = [synthetic_observation()]
    assert estimator.estimate_health(history, 10.0) == estimator.estimate_health(history, 10.0)


@pytest.mark.parametrize(("history", "now_s", "code"), [
    ([], 10.0, "NO_AVAILABLE_OBSERVATION"),
    ([synthetic_observation(observed_at_s=20.0, available_at_s=21.0)], 10.0, "NO_AVAILABLE_OBSERVATION"),
    ([synthetic_observation(source="simulation_truth")], 10.0, "OBSERVATION_INVALID"),
    ([synthetic_observation(soc_observed=float("nan"))], 10.0, "OBSERVATION_INVALID"),
    ([synthetic_observation(), synthetic_observation(soc_observed=0.7)], 10.0, "AMBIGUOUS_OBSERVATION"),
])
def test_formal_entry_preserves_controlled_input_errors(history, now_s, code):
    with pytest.raises(HealthInputError) as error:
        estimator.estimate_health(history, now_s)
    assert error.value.code == code


def test_contract_mismatch_is_wrapped_as_controlled_health_error(monkeypatch):
    config = estimator.load_health_observation_config(
        Path(estimator.__file__).resolve().parents[2] / "configs" / "health_observation.json")
    valid = estimator.estimate_health_core([synthetic_observation()], 10.0, config)
    invalid = replace(valid, energy_lower_Wh=999.0)
    monkeypatch.setattr(estimator, "estimate_health_core", lambda *args, **kwargs: invalid)
    with pytest.raises(HealthInputError) as error:
        estimator._estimate_health_with_config([synthetic_observation()], 10.0, config)
    assert error.value.code == "HEALTH_CONTRACT_INVALID"
import json
import subprocess
import sys


def run_cli(history_path: Path, now_s: str):
    root = Path(estimator.__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "-m", "backend.health.estimator", "--history", str(history_path), "--now-s", now_s],
        cwd=root, capture_output=True, text=True, check=False,
    )


def test_cli_prints_only_formal_health_json_on_success(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([synthetic_observation()]), encoding="utf-8")
    process = run_cli(path, "10")
    assert process.returncode == 0
    assert process.stderr == ""
    HealthEstimate.model_validate_json(process.stdout)


def test_cli_rejects_invalid_observation_with_json_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([synthetic_observation(source="simulation_truth")]), encoding="utf-8")
    process = run_cli(path, "10")
    assert process.returncode == 2
    assert process.stdout == ""
    error = json.loads(process.stderr)
    assert error["status"] == "rejected"
    assert error["error_code"] == "OBSERVATION_INVALID"


def test_cli_rejects_unreadable_history_as_controlled_json(tmp_path):
    process = run_cli(tmp_path / "missing.json", "10")
    assert process.returncode == 2
    assert json.loads(process.stderr)["error_code"] == "HISTORY_FILE_INVALID"
