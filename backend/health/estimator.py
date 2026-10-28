"""Deterministic health bounds from explicitly synthetic observations."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from backend.health.legacy_adapter import HealthInputError


@dataclass(frozen=True)
class HealthObservationConfig:
    schema_version: str
    method: str
    soc_abs_error: float
    capacity_abs_error_Wh: float
    model_version: str
    config_sha256: str


_CONFIG_FIELDS = frozenset(
    {"schema_version", "method", "soc_abs_error", "capacity_abs_error_Wh", "model_version"}
)


def _finite_number(value: Any, *, field: str, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HealthInputError(code, f"{field} must be a finite number")
    try:
        converted = float(value)
    except OverflowError as exc:
        raise HealthInputError(code, f"{field} must be a finite number") from exc
    if not math.isfinite(converted):
        raise HealthInputError(code, f"{field} must be a finite number")
    return converted


def load_health_observation_config(path: Path) -> HealthObservationConfig:
    config_path = Path(path)
    try:
        raw = config_path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HealthInputError("HEALTH_CONFIG_INVALID", f"Could not read health config: {exc}") from exc
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise HealthInputError("HEALTH_CONFIG_INVALID", f"Could not read health config: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _CONFIG_FIELDS:
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Health config fields do not match schema 1.0")
    return _validate_config(HealthObservationConfig(
        schema_version=payload["schema_version"],
        method=payload["method"],
        soc_abs_error=payload["soc_abs_error"],
        capacity_abs_error_Wh=payload["capacity_abs_error_Wh"],
        model_version=payload["model_version"],
        config_sha256=hashlib.sha256(raw).hexdigest().upper(),
    ))


def _validate_config(config: HealthObservationConfig) -> HealthObservationConfig:
    if not isinstance(config, HealthObservationConfig):
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Expected HealthObservationConfig")
    if config.schema_version != "1.0":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health config schema_version")
    if config.method != "synthetic_absolute_margin":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health uncertainty method")
    if config.model_version != "synthetic-health-v1":
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Unsupported health model_version")
    soc = _finite_number(config.soc_abs_error, field="soc_abs_error", code="HEALTH_CONFIG_INVALID")
    capacity = _finite_number(
        config.capacity_abs_error_Wh, field="capacity_abs_error_Wh", code="HEALTH_CONFIG_INVALID"
    )
    if not 0.0 <= soc <= 1.0 or capacity < 0.0:
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Health error margins are outside valid ranges")
    digest = config.config_sha256
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789ABCDEF" for c in digest):
        raise HealthInputError("HEALTH_CONFIG_INVALID", "Invalid health config SHA-256")
    return HealthObservationConfig(config.schema_version, config.method, soc, capacity, config.model_version, digest)



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
    config = _validate_config(config)
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
