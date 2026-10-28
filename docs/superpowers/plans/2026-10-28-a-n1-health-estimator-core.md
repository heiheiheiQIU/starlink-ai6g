# A-N1 Synthetic Health Estimator Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, synthetic-observation health estimator core that filters future data, computes conservative SOC/capacity/energy lower bounds, and preserves unavailable RUL without copying B-owned public contracts.

**Architecture:** `backend/health/estimator.py` owns strict config parsing, exact synthetic observation validation, deterministic latest-available selection, and an immutable `HealthCoreEstimate`. The implementation reuses A's existing `HealthInputError`; it never imports `backend.contracts`, reads `SimulatorState`, or maps legacy `raw_fraction` into health state. H00 integration remains a later thin adapter after B fixes and freezes the public contract.

**Tech Stack:** Python 3.12, standard-library `dataclasses`/`json`/`hashlib`/`math`, pytest 8.3.5; the existing NumPy 2.1.3 and PyTorch 2.5.1 CPU dependencies remain for A1 regression tests.

## Global Constraints

- Work only on `feature/ai` in `D:\pro2`; do not modify `backend/contracts.py`, B/C branches, or frozen files under `交付包/`.
- The only accepted history source is the exact string `synthetic`; reject truth fields, unknown fields, and legacy `raw_fraction`.
- Default margins are scenario assumptions: `soc_abs_error=0.05`, `capacity_abs_error_Wh=1.0`; never describe them as measured sensor accuracy or statistical coverage.
- The estimator is stateless and deterministic; only records with `available_at_s <= now_s` are eligible.
- RUL is always unavailable in this phase: `rul_est=None`, `rul_unit=None`, with an explicit reason code.
- H00 is not frozen. Produce `HealthCoreEstimate`, not B's public `HealthEstimate`, and label handoff material as draft/non-formal.
- Use a fresh workspace-local pytest `--basetemp` path for each verification run; never point pytest at a directory containing valuable files.
- Every new production behavior follows RED → verify RED → GREEN → verify GREEN before refactoring or documentation.

---

### Task 1: Isolated environment and strict observation configuration

**Files:**
- Create: `configs/health_observation.json`
- Create: `backend/health/estimator.py`
- Create: `tests/test_health_estimator.py`

**Interfaces:**
- Consumes: `backend.health.legacy_adapter.HealthInputError`
- Produces: `HealthObservationConfig` and `load_health_observation_config(path: Path) -> HealthObservationConfig`

- [ ] **Step 1: Create the project-local Python environment**

Run:

```powershell
Set-Location D:\pro2
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --only-binary=:all: -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip check
```

Expected: Python reports 3.12.x and `pip check` prints `No broken requirements found.` The `.venv/` directory remains ignored by Git.

- [ ] **Step 2: Write the first failing valid-config test**

Create `tests/test_health_estimator.py` with:

```python
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
```

- [ ] **Step 3: Run the valid-config test and verify RED**

Run:

```powershell
New-Item -ItemType Directory -Path runs\a_n1_test_tmp_01 -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py::test_loads_frozen_synthetic_observation_config -q --noconftest -p no:cacheprovider --basetemp runs\a_n1_test_tmp_01\pytest
```

Expected: collection fails with `ModuleNotFoundError: No module named 'backend.health.estimator'`. This is the intended RED because the new module does not exist.

- [ ] **Step 4: Add the frozen config and minimal valid loader**

Create `configs/health_observation.json` exactly as:

```json
{
  "schema_version": "1.0",
  "method": "synthetic_absolute_margin",
  "soc_abs_error": 0.05,
  "capacity_abs_error_Wh": 1.0,
  "model_version": "synthetic-health-v1"
}
```

Create `backend/health/estimator.py` with the initial implementation:

```python
"""Deterministic health bounds from explicitly synthetic observations."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from backend.health.legacy_adapter import HealthInputError


@dataclass(frozen=True)
class HealthObservationConfig:
    schema_version: str
    method: str
    soc_abs_error: float
    capacity_abs_error_Wh: float
    model_version: str
    config_sha256: str


def load_health_observation_config(path: Path) -> HealthObservationConfig:
    raw = Path(path).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    return HealthObservationConfig(
        schema_version=payload["schema_version"],
        method=payload["method"],
        soc_abs_error=float(payload["soc_abs_error"]),
        capacity_abs_error_Wh=float(payload["capacity_abs_error_Wh"]),
        model_version=payload["model_version"],
        config_sha256=hashlib.sha256(raw).hexdigest().upper(),
    )
```

- [ ] **Step 5: Run the valid-config test and verify GREEN**

Run the Step 3 command with a fresh `runs\a_n1_test_tmp_02\pytest` basetemp.

Expected: `1 passed`.

- [ ] **Step 6: Add failing strict-config tests**

Append to `tests/test_health_estimator.py`:

```python
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
```

- [ ] **Step 7: Run strict-config tests and verify RED**

Run the full new test file with a fresh basetemp. Expected RED: extra fields and unsupported values are accepted, while missing fields/files leak `KeyError` or `OSError` instead of `HealthInputError`.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py -q --noconftest -p no:cacheprovider --basetemp runs\a_n1_test_tmp_03\pytest
```

Expected: the strict-config tests fail for the stated reasons, not because of a typo or fixture error.

- [ ] **Step 8: Implement exact strict config validation and verify GREEN**

Add `math` and `Any` to the imports, add the exact field set and helper, then replace the loader with:

```python
import math
from typing import Any


_CONFIG_FIELDS = frozenset(
    {
        "schema_version",
        "method",
        "soc_abs_error",
        "capacity_abs_error_Wh",
        "model_version",
    }
)


def _finite_number(value: Any, *, field: str, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HealthInputError(code, f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise HealthInputError(code, f"{field} must be a finite number")
    return converted


def load_health_observation_config(path: Path) -> HealthObservationConfig:
    config_path = Path(path)
    try:
        raw = config_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HealthInputError("HEALTH_CONFIG_INVALID", f"Could not read health config: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _CONFIG_FIELDS:
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Health config fields do not match schema 1.0")
    if payload["schema_version"] != "1.0":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health config schema_version")
    if payload["method"] != "synthetic_absolute_margin":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health uncertainty method")
    if payload["model_version"] != "synthetic-health-v1":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health model_version")
    soc_abs_error = _finite_number(
        payload["soc_abs_error"], field="soc_abs_error", code="HEALTH_CONFIG_INVALID"
    )
    capacity_abs_error_Wh = _finite_number(
        payload["capacity_abs_error_Wh"],
        field="capacity_abs_error_Wh",
        code="HEALTH_CONFIG_INVALID",
    )
    if not 0.0 <= soc_abs_error <= 1.0 or capacity_abs_error_Wh < 0.0:
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Health error margins are outside valid ranges")
    return HealthObservationConfig(
        schema_version="1.0",
        method="synthetic_absolute_margin",
        soc_abs_error=soc_abs_error,
        capacity_abs_error_Wh=capacity_abs_error_Wh,
        model_version="synthetic-health-v1",
        config_sha256=hashlib.sha256(raw).hexdigest().upper(),
    )
```

Re-run the Step 7 command with a fresh `runs\a_n1_test_tmp_04\pytest` basetemp.

Expected: all Task 1 tests pass with no warnings or errors.

- [ ] **Step 9: Commit Task 1**

```powershell
git add configs\health_observation.json backend\health\estimator.py tests\test_health_estimator.py
git commit -m "feat(health): load strict synthetic observation config"
```

---

### Task 2: Deterministic latest-available health estimate

**Files:**
- Modify: `backend/health/estimator.py`
- Modify: `tests/test_health_estimator.py`

**Interfaces:**
- Consumes: `HealthObservationConfig`
- Produces: immutable `HealthCoreEstimate` and `estimate_health_core(history: list[dict], now_s: float, config: HealthObservationConfig) -> HealthCoreEstimate`

- [ ] **Step 1: Write failing calculation, RUL, unit, and determinism tests**

Extend the imports and append:

```python
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
```

- [ ] **Step 2: Run both tests and verify RED**

Run both tests with a fresh basetemp. Expected: import fails because `estimate_health_core` does not exist.

- [ ] **Step 3: Add the immutable result and minimal single-record calculation**

Add to `backend/health/estimator.py`:

```python
@dataclass(frozen=True)
class HealthCoreEstimate:
    soc_est: float
    soc_lower: float
    capacity_Wh_est: float
    capacity_lower_Wh: float
    energy_lower_Wh: float
    rul_est: float | None
    rul_unit: str | None
    uncertainty_method: str
    model_version: str
    config_sha256: str
    observed_at_s: float
    available_at_s: float
    reason_codes: tuple[str, ...]


def _build_estimate(record: dict, config: HealthObservationConfig) -> HealthCoreEstimate:
    soc = float(record["soc_observed"])
    capacity = float(record["capacity_Wh_observed"])
    soc_lower = max(0.0, soc - config.soc_abs_error)
    capacity_lower = max(0.0, capacity - config.capacity_abs_error_Wh)
    return HealthCoreEstimate(
        soc_est=soc,
        soc_lower=soc_lower,
        capacity_Wh_est=capacity,
        capacity_lower_Wh=capacity_lower,
        energy_lower_Wh=soc_lower * capacity_lower,
        rul_est=None,
        rul_unit=None,
        uncertainty_method=config.method,
        model_version=config.model_version,
        config_sha256=config.config_sha256,
        observed_at_s=float(record["observed_at_s"]),
        available_at_s=float(record["available_at_s"]),
        reason_codes=(
            "SYNTHETIC_HEALTH_OBSERVATION",
            "SCENARIO_CONSERVATIVE_BOUND",
            "RUL_UNAVAILABLE",
        ),
    )


def estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate:
    return _build_estimate(history[0], config)
```

- [ ] **Step 4: Re-run Step 2 and verify GREEN**

Expected: both calculation tests pass. Do not add time selection or validation yet.

- [ ] **Step 5: Write failing latest-available selection tests**

Append:

```python
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
```

- [ ] **Step 6: Run selection tests and verify RED**

Expected: the minimal implementation uses the first record, accepts future-only input, and silently chooses one tied record.

- [ ] **Step 7: Implement only latest-available selection and verify GREEN**

Replace `estimate_health_core` with:

```python
def estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate:
    now = float(now_s)
    eligible = tuple(record for record in history if float(record["available_at_s"]) <= now)
    if not eligible:
        raise HealthInputError("NO_AVAILABLE_OBSERVATION", "No health observation is available at now_s")
    latest_key = max(
        (float(record["available_at_s"]), float(record["observed_at_s"]))
        for record in eligible
    )
    latest = tuple(
        record
        for record in eligible
        if (float(record["available_at_s"]), float(record["observed_at_s"])) == latest_key
    )
    if len(latest) != 1:
        raise HealthInputError("AMBIGUOUS_OBSERVATION", "Latest health observation is not unique")
    return _build_estimate(latest[0], config)
```

Re-run the Step 6 tests and the two calculation tests. Expected: all pass.

- [ ] **Step 8: Write failing controlled-validation tests**

Append:

```python
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
```

- [ ] **Step 9: Run validation tests and verify RED**

Expected: non-list history, malformed records, truth fields, invalid `now_s`, and the wrong config type either leak built-in exceptions or are incorrectly accepted.

- [ ] **Step 10: Implement exact strict observation validation and verify GREEN**

Add:

```python
_OBSERVATION_FIELDS = frozenset(
    {
        "source",
        "soc_observed",
        "capacity_Wh_observed",
        "observed_at_s",
        "available_at_s",
    }
)


@dataclass(frozen=True)
class _SyntheticObservation:
    soc_observed: float
    capacity_Wh_observed: float
    observed_at_s: float
    available_at_s: float


def _parse_observation(record: Any) -> _SyntheticObservation:
    if not isinstance(record, dict) or set(record) != _OBSERVATION_FIELDS:
        raise HealthInputError("OBSERVATION_INVALID", "Synthetic observation fields do not match schema")
    if record["source"] != "synthetic":
        raise HealthInputError("OBSERVATION_INVALID", "Observation source must be synthetic")
    soc = _finite_number(record["soc_observed"], field="soc_observed", code="OBSERVATION_INVALID")
    capacity = _finite_number(
        record["capacity_Wh_observed"],
        field="capacity_Wh_observed",
        code="OBSERVATION_INVALID",
    )
    observed = _finite_number(record["observed_at_s"], field="observed_at_s", code="OBSERVATION_INVALID")
    available = _finite_number(record["available_at_s"], field="available_at_s", code="OBSERVATION_INVALID")
    if not 0.0 <= soc <= 1.0 or capacity <= 0.0:
        raise HealthInputError("OBSERVATION_INVALID", "SOC or capacity is outside valid range")
    if observed < 0.0 or available < observed:
        raise HealthInputError("OBSERVATION_INVALID", "Observation times are inconsistent")
    return _SyntheticObservation(soc, capacity, observed, available)
```

Replace `_build_estimate` and `estimate_health_core` with:

```python
def _build_estimate(
    record: _SyntheticObservation,
    config: HealthObservationConfig,
) -> HealthCoreEstimate:
    soc_lower = max(0.0, record.soc_observed - config.soc_abs_error)
    capacity_lower = max(0.0, record.capacity_Wh_observed - config.capacity_abs_error_Wh)
    return HealthCoreEstimate(
        soc_est=record.soc_observed,
        soc_lower=soc_lower,
        capacity_Wh_est=record.capacity_Wh_observed,
        capacity_lower_Wh=capacity_lower,
        energy_lower_Wh=soc_lower * capacity_lower,
        rul_est=None,
        rul_unit=None,
        uncertainty_method=config.method,
        model_version=config.model_version,
        config_sha256=config.config_sha256,
        observed_at_s=record.observed_at_s,
        available_at_s=record.available_at_s,
        reason_codes=(
            "SYNTHETIC_HEALTH_OBSERVATION",
            "SCENARIO_CONSERVATIVE_BOUND",
            "RUL_UNAVAILABLE",
        ),
    )


def estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate:
    if not isinstance(config, HealthObservationConfig):
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Expected HealthObservationConfig")
    now = _finite_number(now_s, field="now_s", code="NOW_S_INVALID")
    if now < 0.0:
        raise HealthInputError("NOW_S_INVALID", "now_s must be non-negative")
    if not isinstance(history, list):
        raise HealthInputError("HISTORY_INVALID", "history must be a list")
    observations = tuple(_parse_observation(record) for record in history)
    eligible = tuple(record for record in observations if record.available_at_s <= now)
    if not eligible:
        raise HealthInputError("NO_AVAILABLE_OBSERVATION", "No health observation is available at now_s")
    latest_key = max((record.available_at_s, record.observed_at_s) for record in eligible)
    latest = tuple(
        record
        for record in eligible
        if (record.available_at_s, record.observed_at_s) == latest_key
    )
    if len(latest) != 1:
        raise HealthInputError("AMBIGUOUS_OBSERVATION", "Latest health observation is not unique")
    return _build_estimate(latest[0], config)
```

Re-run all Task 2 tests. Expected: every calculation, selection, and validation test passes.

- [ ] **Step 11: Run Task 2 tests and existing A regressions**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py tests\test_health.py tests\test_legacy_audit.py tests\test_review_boundaries.py -q --noconftest -p no:cacheprovider --basetemp runs\a_n1_test_tmp_05\pytest
```

Expected: all tests pass; no test reads future health, no frozen asset changes, and no warnings indicate fallback or permissive loading.

- [ ] **Step 12: Commit Task 2**

```powershell
git add backend\health\estimator.py tests\test_health_estimator.py
git commit -m "feat(health): estimate deterministic synthetic bounds"
```

---

### Task 3: Draft handoff, task status, and final verification

**Files:**
- Create: `docs/handoffs/H01_health_estimate.md`
- Modify: `docs/task_board.csv`
- Verify only: `configs/health_observation.json`, `backend/health/estimator.py`, `tests/test_health_estimator.py`

**Interfaces:**
- Consumes: verified `HealthCoreEstimate` behavior from Task 2
- Produces: a clearly non-formal H01 draft and an accurate `in_progress` task-board entry

- [ ] **Step 1: Create the draft handoff**

Create `docs/handoffs/H01_health_estimate.md` with:

```markdown
# H01 HealthEstimate交接草稿（A-N1内部核心）

日期：2026-10-28。状态：`internal_core_ready_for_review`，不是正式H01 accepted。

## 已交付

- `backend/health/estimator.py`：只消费明确标注为synthetic的SOC/容量观测。
- `configs/health_observation.json`：绝对误差场景参数及版本。
- `tests/test_health_estimator.py`：时间过滤、单位、下界、RUL缺失和错误边界。

内部入口：

```python
load_health_observation_config(path: Path) -> HealthObservationConfig
estimate_health_core(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthCoreEstimate
```

`HealthCoreEstimate`是A内部不可变结果，不是B的公共`HealthEstimate`。

## 数据与单位边界

- SOC是0—1比例；容量与能量单位为Wh；时间单位为秒。
- 只使用`available_at_s <= now_s`的synthetic记录。
- 下界采用配置中的确定性绝对误差，只能称为场景保守边界。
- `energy_lower_Wh = soc_lower * capacity_lower_Wh`。
- RUL固定为null；旧`raw_fraction`不进入SOC、容量或能量计算。

## 复现

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py -q `
  --noconftest -p no:cacheprovider --basetemp runs\h01_draft_test\pytest
```

配置SHA256由`load_health_observation_config`从原始JSON字节计算并随结果返回。

## 尚未交付

- 尚未导入或复制B的`backend/contracts.py`。
- 尚未生成正式`HealthEstimate`成功、RUL缺失、输入错误三份样例。
- 尚未完成B主验或C字段展示检查。

以上工作等待H00阻塞项修复、A/C重新签收并合入`main`后完成。当前草稿不得用于宣称
在线健康校准、真实传感器精度或新通信实验结果。
```

- [ ] **Step 2: Update only the A-N1 task-board row**

Replace the current A-N1 row in `docs/task_board.csv` with:

```csv
A-N1,A,in_progress,2026-10-29T22:00:00+08:00,backend/health/estimator.py,B,,等待H00修复冻结,内部核心与测试完成后接正式HealthEstimate适配及三样例
```

Do not change B or C task rows.

- [ ] **Step 3: Run final verification**

Use fresh paths and run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health_estimator.py tests\test_health.py tests\test_legacy_audit.py tests\test_review_boundaries.py -q --noconftest -p no:cacheprovider --basetemp runs\a_n1_final_test\pytest
.\.venv\Scripts\python.exe -m compileall -q backend training tests
powershell -NoProfile -ExecutionPolicy Bypass -File .\交付包\星地智调_团队研发包_2026-10-26_v3\verify_package.ps1
git diff --check
git status --short
```

Expected:

- all estimator and existing A tests pass;
- compileall exits 0;
- the frozen package reports `PASS: 148 files match SHA256 and size`;
- `git diff --check` prints nothing;
- Git shows only the intended handoff/task-board changes before commit;
- `git diff --name-only origin/feature/ai...HEAD` never contains `backend/contracts.py`.

- [ ] **Step 4: Commit Task 3**

```powershell
git add docs\handoffs\H01_health_estimate.md docs\task_board.csv
git commit -m "docs(handoff): deliver A-N1 internal health core draft"
```

- [ ] **Step 5: Review the completed branch before any push**

```powershell
git log --oneline origin/feature/ai..HEAD
git diff --stat origin/feature/ai...HEAD
git status --short --branch
```

Expected: the branch is clean and ahead only by the approved A-N1 design/config/core/tests/draft commits. Do not push or open a PR until the user chooses the branch integration action.
