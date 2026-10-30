"""Recompute auditable teacher labels from public observations only."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from backend.contracts import Observation, validate_teacher_result
from backend.policies.teacher import solve_teacher


LABEL_CONTENT_FIELDS = (
    "sample_id", "scenario_id", "state_id", "source_revision",
    "source_observation_sha256", "observation", "teacher_version",
    "teacher_config_sha256", "candidate_scores", "solver_status",
    "gap", "diagnostics", "label_eligible", "exclusion_reasons",
)
LEAK_FIELDS = {
    "true_capacity", "capacity_true_wh", "future_arrivals",
    "actual_future_loss", "evaluation_truth", "energy_true_wh", "soc_true",
}


class TeacherDataError(ValueError):
    """Controlled data boundary failure, with a machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def label_content_sha256(record: dict[str, object]) -> str:
    return sha256_text(canonical_json({key: record[key] for key in LABEL_CONTENT_FIELDS}))


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reject_leaks(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in LEAK_FIELDS:
                raise TeacherDataError("LEAK_FIELD", f"Hidden-truth field: {key}")
            _reject_leaks(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_leaks(child)


def generate_record(
    source: dict[str, object],
    *,
    source_revision: str,
    budget_ms: int,
    teacher_config_path: Path,
) -> dict[str, object]:
    """Solve one source observation; never reuse labels in its envelope."""
    try:
        sample_id = source["sample_id"]
        payload = source["observation"]
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError("sample_id must be a nonempty string")
        _reject_leaks(payload)
        before = canonical_json(payload)
        observation = Observation.model_validate(payload)
        parsed_before = canonical_json(observation.model_dump(mode="json"))
    except TeacherDataError:
        raise
    except (KeyError, ValueError, TypeError) as error:
        raise TeacherDataError("INVALID_OBSERVATION", str(error)) from error

    config = load_json(teacher_config_path)
    config_sha256 = hashlib.sha256(teacher_config_path.read_bytes()).hexdigest()
    diagnostics: dict[str, object] = {}
    result = solve_teacher(observation, budget_ms=budget_ms,
                           config=config, diagnostics=diagnostics)
    try:
        unchanged = (canonical_json(payload) == before and
                     canonical_json(observation.model_dump(mode="json")) == parsed_before)
    except (ValueError, TypeError):
        unchanged = False
    if not unchanged:
        raise TeacherDataError("OBSERVATION_MUTATED", "Teacher modified its observation")

    try:
        result = validate_teacher_result(observation, result)
        keys = [(item.task_id, item.mode) for item in result.candidate_scores]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate candidate keys")
        if any(not math.isfinite(item.score) for item in result.candidate_scores):
            raise ValueError("Candidate scores must be finite")
        if result.gap is not None and not math.isfinite(result.gap):
            raise ValueError("Gap must be finite")
    except (ValueError, TypeError) as error:
        raise TeacherDataError("INVALID_TEACHER_RESULT", str(error)) from error

    # Candidate timing is runtime evidence and cannot enter the stable label hash.
    for candidate in diagnostics.get("candidates", []):
        candidate.pop("elapsed_ms", None)

    eligible = result.solver_status == "OPTIMAL" and result.gap == 0.0
    record: dict[str, object] = {
        "schema_version": "1.0",
        "dataset_version": "a-n3-teacher-20-v1",
        "sample_id": sample_id,
        "scenario_id": observation.run_id,
        "state_id": sample_id,
        "source_revision": source_revision,
        "source_observation_sha256": sha256_text(before),
        "observation": copy.deepcopy(payload),
        "teacher_version": diagnostics["teacher_version"],
        "teacher_config_sha256": config_sha256,
        "candidate_scores": [item.model_dump(mode="json") for item in result.candidate_scores],
        "solver_status": result.solver_status,
        "gap": result.gap,
        "elapsed_ms": result.elapsed_ms,
        "diagnostics": diagnostics,
        "label_eligible": eligible,
        "exclusion_reasons": [] if eligible else [result.solver_status],
    }
    record["label_content_sha256"] = label_content_sha256(record)
    return record
