"""Immutable, unnormalised policy inputs derived only from public Observation."""

from __future__ import annotations

from dataclasses import dataclass
import math

from backend.contracts import Observation


FEATURE_SCHEMA_VERSION = "policy-features-v1"
GLOBAL_FEATURE_NAMES = (
    "sim_time_s", "cache_bytes", "energy_lower_Wh", "soc_lower",
    "capacity_lower_Wh", "visible_task_count", "inflight_present",
    "next_window_start_delta_s", "next_window_duration_s",
    "next_robust_bps", "next_fast_bps", "next_robust_loss_prob",
    "next_fast_loss_prob", "has_forecast_window",
)
CANDIDATE_FEATURE_NAMES = (
    "is_idle", "is_robust", "is_fast", "time_since_arrival_s",
    "time_to_deadline_s", "payload_bytes", "remaining_bytes",
    "remaining_fraction", "priority_weight",
)


class PolicyFeatureError(ValueError):
    """The public observation or its numeric encoding violates the schema."""


@dataclass(frozen=True)
class EncodedObservation:
    schema_version: str
    global_feature_names: tuple[str, ...]
    candidate_feature_names: tuple[str, ...]
    candidate_keys: tuple[tuple[str | None, str], ...]
    global_features: tuple[float, ...]
    candidate_features: tuple[tuple[float, ...], ...]
    candidate_mask: tuple[bool, ...]


def _finite_floats(values) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise PolicyFeatureError("Policy features must be finite")
    return result


def _profile_point(profile, time_s):
    return next((point for point in reversed(profile) if point.time_s <= time_s), profile[0])


def encode_observation(observation: Observation) -> EncodedObservation:
    """Encode raw features and structural availability, without action feasibility.

    Deadline deltas remain signed, including expired tasks. Active windows use
    their full duration and profiles at the current time; future windows use
    profiles at their start. An available candidate still requires safe decoding.
    """
    try:
        if not isinstance(observation, Observation):
            raise PolicyFeatureError("Expected a public Observation instance")
        # Contract models are mutable: revalidate even previously valid instances.
        obs = Observation.model_validate(observation)
        now = obs.sim_time_s
        windows = [window for window in obs.forecast_windows if window.end_s > now]
        next_window = min(windows, key=lambda window: (window.start_s, window.window_id), default=None)
        window_features = (0.0,) * 7
        if next_window is not None:
            at = max(now, next_window.start_s)
            rate = _profile_point(next_window.rate_profile, at)
            loss = _profile_point(next_window.loss_profile, at)
            window_features = (
                max(0.0, next_window.start_s - now),
                next_window.end_s - next_window.start_s,
                rate.robust_bps, rate.fast_bps,
                loss.robust_loss_prob, loss.fast_loss_prob, 1.0,
            )
        global_features = _finite_floats((
            now, obs.cache_bytes, obs.health.energy_lower_Wh,
            obs.health.soc_lower, obs.health.capacity_lower_Wh,
            len(obs.tasks), obs.inflight is not None, *window_features,
        ))
        keys = []
        rows = []
        mask = []
        for task in sorted(obs.tasks, key=lambda task: task.task_id):
            task_features = (
                now - task.arrival_s, task.deadline_s - now,
                task.payload_bytes, task.remaining_bytes,
                task.remaining_bytes / task.payload_bytes, task.priority_weight,
            )
            allowed = (obs.inflight is None and task.deadline_s >= now
                       and task.remaining_bytes > 0)
            for mode in ("robust", "fast"):
                keys.append((task.task_id, mode))
                rows.append(_finite_floats((0.0, mode == "robust", mode == "fast", *task_features)))
                mask.append(allowed)
        keys.append((None, "idle"))
        rows.append((1.0,) + (0.0,) * 8)
        mask.append(True)
        return EncodedObservation(
            schema_version=FEATURE_SCHEMA_VERSION,
            global_feature_names=GLOBAL_FEATURE_NAMES,
            candidate_feature_names=CANDIDATE_FEATURE_NAMES,
            candidate_keys=tuple(keys), global_features=global_features,
            candidate_features=tuple(rows), candidate_mask=tuple(mask),
        )
    except PolicyFeatureError:
        raise
    except (ValueError, TypeError, OverflowError) as error:
        raise PolicyFeatureError(f"Invalid observation features: {error}") from error
