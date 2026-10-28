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
        payload["capacity_abs_error_Wh"], field="capacity_abs_error_Wh", code="HEALTH_CONFIG_INVALID"
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
