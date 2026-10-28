"""H00 candidate contract 1.0. No simulation, policy or HTTP implementation.

Python validates structural and cross-field invariants. Generated JSON Schema
validates the wire structure; temporal and membership checks remain Python-side.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Annotated, Literal, Protocol, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError, model_validator


SCHEMA_VERSION = "1.0"
NonEmpty = Annotated[str, Field(min_length=1, pattern=r"\S")]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]
Probability = Annotated[float, Field(ge=0, le=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]
Mode = Literal["idle", "robust", "fast"]
RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
ErrorCode = Literal["INVALID_CONFIG", "RUN_NOT_FOUND", "RUN_NOT_COMPLETE", "CAPACITY_BUSY", "INTERNAL_RUN_ERROR"]


class ContractModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False,
                              revalidate_instances="always")

    @model_validator(mode="after")
    def json_values_are_finite(self):
        # Opaque config/error detail maps must not bypass float field validation.
        json.dumps(self.model_dump(mode="python"), allow_nan=False)
        return self


class Task(ContractModel):
    task_id: NonEmpty
    arrival_s: NonNegativeFloat
    deadline_s: NonNegativeFloat
    payload_bytes: PositiveInt
    remaining_bytes: NonNegativeInt
    priority_weight: PositiveFloat
    business_class: NonEmpty
    data_location: Literal["satellite_1"]

    @model_validator(mode="after")
    def consistent_task(self):
        if self.deadline_s <= self.arrival_s:
            raise ValueError("deadline_s must exceed arrival_s")
        if self.remaining_bytes > self.payload_bytes:
            raise ValueError("remaining_bytes cannot exceed payload_bytes")
        return self


class RatePoint(ContractModel):
    time_s: NonNegativeFloat
    robust_bps: NonNegativeFloat
    fast_bps: NonNegativeFloat


class LossPoint(ContractModel):
    time_s: NonNegativeFloat
    robust_loss_prob: Probability
    fast_loss_prob: Probability


class Window(ContractModel):
    window_id: NonEmpty
    start_s: NonNegativeFloat
    end_s: NonNegativeFloat
    rate_profile: Annotated[list[RatePoint], Field(min_length=1)]
    loss_profile: Annotated[list[LossPoint], Field(min_length=1)]
    source: NonEmpty
    forecast_version: NonEmpty

    @model_validator(mode="after")
    def consistent_profiles(self):
        if self.end_s <= self.start_s:
            raise ValueError("Window requires start_s < end_s")
        for profile in (self.rate_profile, self.loss_profile):
            times = [point.time_s for point in profile]
            if times[0] != self.start_s:
                raise ValueError("Each profile must start at window.start_s")
            if any(t < self.start_s or t >= self.end_s for t in times):
                raise ValueError("Profile times must lie in [start_s, end_s)")
            if any(a >= b for a, b in zip(times, times[1:])):
                raise ValueError("Profile times must be strictly increasing")
        return self


class HealthEstimate(ContractModel):
    soc_est: Probability
    soc_lower: Probability
    capacity_Wh_est: PositiveFloat
    capacity_lower_Wh: NonNegativeFloat
    energy_lower_Wh: NonNegativeFloat
    rul_est: NonNegativeFloat | None
    rul_unit: NonEmpty | None
    uncertainty_method: NonEmpty
    model_version: NonEmpty
    observed_at_s: NonNegativeFloat
    available_at_s: NonNegativeFloat
    reason_codes: list[NonEmpty]

    @model_validator(mode="after")
    def consistent_estimate(self):
        if self.soc_lower > self.soc_est or self.capacity_lower_Wh > self.capacity_Wh_est:
            raise ValueError("Lower bounds cannot exceed estimates")
        expected_energy = self.soc_lower * self.capacity_lower_Wh
        if not math.isclose(self.energy_lower_Wh, expected_energy, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("energy_lower_Wh must equal soc_lower * capacity_lower_Wh")
        if self.observed_at_s > self.available_at_s:
            raise ValueError("available_at_s cannot precede observed_at_s")
        if self.rul_est is None and not self.reason_codes:
            raise ValueError("Missing RUL requires a reason code")
        if self.rul_est is not None and self.rul_unit is None:
            raise ValueError("Available RUL requires a native unit")
        return self


class InFlight(ContractModel):
    task_id: NonEmpty
    block_id: NonNegativeInt
    payload_bytes: Annotated[int, Field(gt=0, le=1024)]
    mode: Literal["robust", "fast"]
    sent_at_s: NonNegativeFloat
    timeout_at_s: NonNegativeFloat
    retries: NonNegativeInt

    @model_validator(mode="after")
    def timeout_follows_send(self):
        if self.timeout_at_s <= self.sent_at_s:
            raise ValueError("timeout_at_s must follow sent_at_s")
        return self


class Observation(ContractModel):
    schema_version: Literal["1.0"]
    run_id: NonEmpty
    policy_id: NonEmpty
    sim_time_s: NonNegativeFloat
    tasks: list[Task]
    forecast_windows: list[Window]
    health: HealthEstimate
    inflight: InFlight | None
    cache_bytes: NonNegativeInt
    forecast_version: NonEmpty

    @model_validator(mode="after")
    def only_available_information(self):
        ids = [task.task_id for task in self.tasks]
        window_ids = [window.window_id for window in self.forecast_windows]
        if len(ids) != len(set(ids)) or len(window_ids) != len(set(window_ids)):
            raise ValueError("Task and window IDs must be unique")
        if self.health.available_at_s > self.sim_time_s:
            raise ValueError("Health is not yet available")
        if any(task.arrival_s > self.sim_time_s for task in self.tasks):
            raise ValueError("Future arrivals are not observable")
        if self.inflight is not None:
            if self.inflight.task_id not in ids or self.inflight.sent_at_s > self.sim_time_s:
                raise ValueError("In-flight block must refer to an observed task and past send")
        return self


_TASK_MODE_SCHEMA = {
    "allOf": [{"if": {"properties": {"mode": {"const": "idle"}}},
               "then": {"properties": {"task_id": {"type": "null"}}},
               "else": {"properties": {"task_id": {"type": "string", "minLength": 1}}}}]
}


class CandidateScore(ContractModel):
    model_config = ConfigDict(json_schema_extra=_TASK_MODE_SCHEMA)
    task_id: NonEmpty | None
    mode: Mode
    score: float

    @model_validator(mode="after")
    def task_matches_mode(self):
        if (self.mode == "idle") != (self.task_id is None):
            raise ValueError("Only idle has task_id=null")
        return self


class ContractViolation(ValueError):
    """Controlled boundary error; guard/API owns fallback or HTTP translation."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def validate_candidate_scores(obs: Observation, scores: list[CandidateScore] | list[dict]) -> list[CandidateScore]:
    """Validate the FULL scorer output, never a top-3 event summary."""
    try:
        if not isinstance(scores, list):
            raise ValueError("Candidate output must be a list")
        parsed = [CandidateScore.model_validate(s.model_dump() if isinstance(s, CandidateScore) else s) for s in scores]
        keys = [(s.task_id, s.mode) for s in parsed]
        if len(keys) != len(set(keys)) or sum(s.mode == "idle" for s in parsed) != 1:
            raise ValueError("Candidates must be unique with exactly one idle")
        task_ids = {task.task_id for task in obs.tasks}
        if any(s.mode != "idle" and s.task_id not in task_ids for s in parsed):
            raise ValueError("Non-idle candidate must reference the visible queue")
        return parsed
    except (ValidationError, ValueError, TypeError) as error:
        raise ContractViolation("INVALID_SCORE", str(error)) from error


class Action(ContractModel):
    task_id: NonEmpty | None
    mode: Mode
    scheduled_bytes: Annotated[int, Field(ge=0, le=1024)]
    reason_codes: list[NonEmpty]
    fallback: bool

    @model_validator(mode="after")
    def executable_shape(self):
        if self.mode == "idle":
            if self.task_id is not None or self.scheduled_bytes != 0:
                raise ValueError("Idle requires null task and zero bytes")
        elif self.task_id is None or self.scheduled_bytes == 0:
            raise ValueError("Sending requires a task and positive bytes")
        if self.fallback and not self.reason_codes:
            raise ValueError("Fallback requires a reason code")
        return self


class ConstraintCheck(ContractModel):
    code: NonEmpty
    passed: bool
    details: dict[str, JsonValue]


class DecisionData(ContractModel):
    """Wire payload, with the latency_ms field required by manual 09."""
    action: Action
    candidate_scores: list[CandidateScore]
    constraint_checks: list[ConstraintCheck]
    latency_ms: NonNegativeFloat
    fallback: bool
    model_version: NonEmpty | None
    policy_version: NonEmpty

    @model_validator(mode="after")
    def matching_fallback(self):
        if self.fallback != self.action.fallback:
            raise ValueError("Decision and Action fallback flags must agree")
        return self


class Decision(ContractModel):
    """Python decoder return type; explicitly converted to wire event data."""
    action: Action
    candidate_scores: list[CandidateScore]
    constraint_checks: list[ConstraintCheck]
    decision_latency_ms: NonNegativeFloat
    fallback: bool
    model_version: NonEmpty | None
    policy_version: NonEmpty

    @model_validator(mode="after")
    def matching_fallback(self):
        if self.fallback != self.action.fallback:
            raise ValueError("Decision and Action fallback flags must agree")
        return self

    def to_event_data(self) -> DecisionData:
        values = self.model_dump()
        values["latency_ms"] = values.pop("decision_latency_ms")
        return DecisionData.model_validate(values)


class EnergyBandPoint(ContractModel):
    time_s: NonNegativeFloat
    energy_lower_Wh: NonNegativeFloat
    energy_upper_Wh: NonNegativeFloat

    @model_validator(mode="after")
    def ordered_bounds(self):
        if self.energy_lower_Wh > self.energy_upper_Wh:
            raise ValueError("Energy band lower exceeds upper")
        return self


class EvaluationTruth(ContractModel):
    label: Literal["posthoc_simulation"]
    soc_true: float
    energy_true_Wh: float
    capacity_true_Wh: PositiveFloat


class SnapshotData(ContractModel):
    soc_est: Probability
    energy_est_Wh: NonNegativeFloat
    energy_lower_Wh: NonNegativeFloat
    queue_count: NonNegativeInt
    forecast_energy_band: list[EnergyBandPoint] | None
    policy_version: NonEmpty
    evaluation_truth: EvaluationTruth | None
    reason_codes: list[NonEmpty]

    @model_validator(mode="after")
    def missing_band_is_explained(self):
        if self.forecast_energy_band is None and not self.reason_codes:
            raise ValueError("Missing forecast band requires reason_codes")
        if self.energy_lower_Wh > self.energy_est_Wh:
            raise ValueError("Energy lower bound exceeds estimate")
        return self


class WindowChangedData(ContractModel):
    window_id: NonEmpty
    is_visible: bool


_EVENT_PAYLOAD_TYPES = {"decision": DecisionData, "snapshot": SnapshotData, "window_changed": WindowChangedData}
_EVENT_SCHEMA = {"allOf": [
    {"if": {"properties": {"event_type": {"const": name}}},
     "then": {"properties": {"data": {"$ref": f"#/$defs/{model.__name__}"}}}}
    for name, model in _EVENT_PAYLOAD_TYPES.items()
] + [{"if": {"properties": {"event_type": {"enum": ["arrived", "sent", "received", "acked", "dropped", "fallback"]}}},
      "then": {"properties": {"data": {"type": "null"}}}}]}


class Event(ContractModel):
    event_id: PositiveInt
    run_id: NonEmpty
    policy_id: NonEmpty
    sim_time_s: NonNegativeFloat
    event_type: Literal["arrived", "sent", "received", "acked", "dropped", "fallback", "decision", "snapshot", "window_changed"]
    task_id: NonEmpty | None
    block_id: NonNegativeInt | None
    payload_bytes: NonNegativeInt
    overhead_bytes: NonNegativeInt
    energy_Wh: NonNegativeFloat
    reason_code: NonEmpty | None
    data: DecisionData | SnapshotData | WindowChangedData | None

    @model_validator(mode="after")
    def appropriate_payload(self):
        expected = _EVENT_PAYLOAD_TYPES.get(self.event_type)
        if expected is not None and not isinstance(self.data, expected):
            raise ValueError(f"{self.event_type} requires {expected.__name__}")
        if expected is None and self.data is not None:
            raise ValueError("Basic event data must be null")
        if self.event_type == "fallback" and self.reason_code is None:
            raise ValueError("Fallback event requires reason_code")
        return self


class EventsQuery(ContractModel):
    after: NonNegativeInt = 0
    limit: Annotated[int, Field(ge=1, le=2000)] = 500


class EventsPage(ContractModel):
    run_id: NonEmpty
    events: list[Event]
    next_after: NonNegativeInt
    has_more: bool

    @model_validator(mode="after")
    def consistent_cursor(self):
        ids = [event.event_id for event in self.events]
        if any(a >= b for a, b in zip(ids, ids[1:])):
            raise ValueError("event_id must increase across policies")
        if any(event.run_id != self.run_id for event in self.events):
            raise ValueError("Page cannot mix runs")
        if ids and self.next_after != ids[-1]:
            raise ValueError("next_after must equal the last event_id")
        if not ids and self.has_more:
            raise ValueError("Empty page cannot promise more events without advancing")
        return self


class ErrorBody(ContractModel):
    code: ErrorCode
    message: NonEmpty
    details: dict[str, JsonValue]


class RunRequest(ContractModel):
    schema_version: Literal["1.0"]
    config: dict[str, JsonValue]
    policy_ids: Annotated[list[NonEmpty], Field(min_length=1, max_length=2)]
    seed: NonNegativeInt

    @model_validator(mode="after")
    def unique_policies(self):
        if len(self.policy_ids) != len(set(self.policy_ids)):
            raise ValueError("policy_ids must be unique")
        return self


class RunCreated(ContractModel):
    run_id: NonEmpty
    status: Literal["queued"]
    schema_version: Literal["1.0"]


class RunStatusResponse(ContractModel):
    run_id: NonEmpty
    status: RunStatus
    progress: Probability | None
    active_policies: Annotated[list[NonEmpty], Field(max_length=2)]
    error: ErrorBody | None

    @model_validator(mode="after")
    def consistent_status(self):
        if len(self.active_policies) != len(set(self.active_policies)):
            raise ValueError("active_policies must be unique")
        if self.status == "failed" and self.error is None:
            raise ValueError("Failed run requires an error")
        if self.status != "failed" and self.error is not None:
            raise ValueError("Only failed runs carry error; cancelled is a distinct state")
        return self


class PolicyResult(ContractModel):
    policy_id: NonEmpty
    model_hash: Sha256 | None
    sample_count: NonNegativeInt
    evaluation_end_s: NonNegativeFloat
    pending_task_count: NonNegativeInt
    weighted_on_time_rate: Probability | None
    critical_task_success_rate: Probability | None
    goodput_bps: NonNegativeFloat | None
    minimum_soc_true: float | None
    energy_violation_count: NonNegativeInt | None
    energy_violation_duration_s: NonNegativeFloat | None
    success_payload_bytes: NonNegativeInt
    joule_per_success_bit: NonNegativeFloat | None
    wait_p50_s: NonNegativeFloat | None
    wait_p95_s: NonNegativeFloat | None
    decision_p50_ms: NonNegativeFloat | None
    decision_p95_ms: NonNegativeFloat | None
    timeout_rate: Probability | None
    parameter_count: NonNegativeInt | None
    memory_bytes: NonNegativeInt | None
    metric_reasons: dict[str, NonEmpty]

    @model_validator(mode="after")
    def missing_metrics_are_explained(self):
        metric_names = set(type(self).model_fields) - {
            "policy_id", "model_hash", "sample_count", "evaluation_end_s",
            "pending_task_count", "success_payload_bytes", "metric_reasons",
        }
        for name in metric_names:
            if getattr(self, name) is None and name not in self.metric_reasons:
                raise ValueError(f"Missing metric {name} requires a reason")
        if set(self.metric_reasons) - metric_names:
            raise ValueError("Unknown metric reason key")
        if self.sample_count == 0 and self.weighted_on_time_rate is not None:
            raise ValueError("Empty task denominator must not produce a rate")
        if self.success_payload_bytes == 0:
            if self.joule_per_success_bit is not None or self.metric_reasons.get("joule_per_success_bit") != "NO_DELIVERY":
                raise ValueError("No successful bits requires null J/bit and NO_DELIVERY")
        for prefix, unit in (("wait", "s"), ("decision", "ms")):
            p50, p95 = getattr(self, f"{prefix}_p50_{unit}"), getattr(self, f"{prefix}_p95_{unit}")
            if p50 is not None and p95 is not None and p50 > p95:
                raise ValueError("P50 cannot exceed P95")
        return self


class RunResult(ContractModel):
    schema_version: Literal["1.0"]
    run_id: NonEmpty
    status: Literal["completed"]
    config_hash: Sha256
    input_hash: Sha256
    model_hash: Sha256 | None
    code_revision: NonEmpty
    seed: NonNegativeInt
    by_policy: Annotated[list[PolicyResult], Field(min_length=1, max_length=2)]
    metric_definitions: dict[str, NonEmpty]
    artifact_paths: dict[str, NonEmpty]

    @model_validator(mode="after")
    def unique_policy_results(self):
        ids = [result.policy_id for result in self.by_policy]
        if len(ids) != len(set(ids)):
            raise ValueError("by_policy must have unique policy_id")
        hashes = {result.model_hash for result in self.by_policy}
        expected = next(iter(hashes)) if len(hashes) == 1 else None
        if self.model_hash != expected:
            raise ValueError("Top-level model_hash must be common hash or null for mixed policies")
        for path in self.artifact_paths.values():
            if path.startswith(("/", "\\")) or ":" in path or ".." in path.replace("\\", "/").split("/"):
                raise ValueError("artifact_paths must be run-relative paths")
        return self


class TeacherCandidateScore(CandidateScore):
    feasible: bool


class TeacherResult(ContractModel):
    candidate_scores: list[TeacherCandidateScore]
    solver_status: NonEmpty
    gap: NonNegativeFloat | None
    elapsed_ms: NonNegativeFloat


class SimulatorState(Protocol):
    """Environment-only structural interface, deliberately absent from JSON schema.

    R2 owns the concrete state (including hidden truth); never pass it to a scorer
    or serialize it as an Observation. No simulation state is implemented here.
    """
    run_id: str
    policy_id: str
    sim_time_s: float


@dataclass
class StepResult:
    next_state: SimulatorState
    events: list[Event]


PUBLIC_MODELS = {model.__name__: model for model in (
    Task, RatePoint, LossPoint, Window, HealthEstimate, InFlight, Observation,
    CandidateScore, Action, ConstraintCheck, Decision, DecisionData, EnergyBandPoint,
    EvaluationTruth, SnapshotData, WindowChangedData, Event, EventsQuery, EventsPage,
    ErrorBody, RunRequest, RunCreated, RunStatusResponse, PolicyResult, RunResult,
    TeacherCandidateScore, TeacherResult,
)}


def contract_schema() -> dict:
    """Generate reproducible Draft 2020-12 structural schemas for all wire types."""
    schema = TypeAdapter(Union[tuple(PUBLIC_MODELS.values())]).json_schema()
    # Pydantic resolves definition names during generation. Attach cross-model
    # references afterwards, when their final $defs names are available.
    schema["$defs"]["Event"].update(_EVENT_SCHEMA)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:starlink-ai6g:contracts:1.0"
    schema["title"] = "Starlink AI6G H00 candidate contracts 1.0"
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Export H00 candidate JSON Schema; does not run simulations.")
    parser.add_argument("--schema-output", type=Path, required=True)
    args = parser.parse_args()
    args.schema_output.parent.mkdir(parents=True, exist_ok=True)
    args.schema_output.write_text(json.dumps(contract_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
