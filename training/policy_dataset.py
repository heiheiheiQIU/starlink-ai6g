"""Verified, leakage-safe inputs for the A-N3 learned policy."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from backend.contracts import Observation
from training.generate_teacher_data import observation_content_sha256
from training.policy_features import (
    CANDIDATE_FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    GLOBAL_FEATURE_NAMES,
    encode_observation,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/policy_train.json"


class PolicyDataError(ValueError):
    """A frozen training-data invariant failed before model code ran."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class PolicyExample:
    sample_id: str
    observation: Observation
    candidate_keys: tuple[tuple[str | None, str], ...]
    global_features: tuple[float, ...]
    candidate_features: tuple[tuple[float, ...], ...]
    candidate_mask: tuple[bool, ...]
    target_scores: tuple[float, ...]
    target_feasible: tuple[bool, ...]


@dataclass(frozen=True)
class Normalization:
    schema_version: str
    feature_schema_version: str
    source_split: str
    global_feature_names: tuple[str, ...]
    candidate_feature_names: tuple[str, ...]
    global_mean: tuple[float, ...]
    global_scale: tuple[float, ...]
    candidate_mean: tuple[float, ...]
    candidate_scale: tuple[float, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "feature_schema_version": self.feature_schema_version,
            "source_split": self.source_split,
            "global_feature_names": list(self.global_feature_names),
            "candidate_feature_names": list(self.candidate_feature_names),
            "global_mean": list(self.global_mean),
            "global_scale": list(self.global_scale),
            "candidate_mean": list(self.candidate_mean),
            "candidate_scale": list(self.candidate_scale),
        }


@dataclass(frozen=True)
class FrozenPolicyDataset:
    splits: dict[str, tuple[PolicyExample, ...]]
    by_sample_id: dict[str, PolicyExample]
    normalization: Normalization
    samples_sha256: str
    split_sha256: str


def _fail(code: str, message: str):
    raise PolicyDataError(code, message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, code: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolicyDataError(code, f"Cannot read {path}: {type(error).__name__}") from error
    if not isinstance(value, dict):
        _fail(code, f"Expected an object in {path}")
    return value


def _resolve(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        _fail("CONFIG", f"{field} must be a path string")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _validate_config(config: dict[str, object]):
    if config.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        _fail("FEATURE_SCHEMA", "Unexpected feature schema version")
    if tuple(config.get("global_feature_names", ())) != GLOBAL_FEATURE_NAMES:
        _fail("FEATURE_SCHEMA", "Global feature order differs from encoder")
    if tuple(config.get("candidate_feature_names", ())) != CANDIDATE_FEATURE_NAMES:
        _fail("FEATURE_SCHEMA", "Candidate feature order differs from encoder")
    if config.get("split_algorithm_version") != "source-group-sha256-v2":
        _fail("CONFIG", "Unexpected split algorithm")
    if config.get("split_seed") != 20261031:
        _fail("CONFIG", "Unexpected split seed")
    if config.get("split_counts") != {"train": 12, "validation": 4, "test": 4}:
        _fail("CONFIG", "Unexpected split counts")
    if config.get("eligible_solver_status") != "OPTIMAL" or config.get("required_gap") != 0.0:
        _fail("CONFIG", "Unexpected label eligibility gate")


def _read_rows(path: Path) -> list[dict[str, object]]:
    rows = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                _fail("SOURCE_FORMAT", f"Line {number} is not an object")
            rows.append(row)
    except PolicyDataError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolicyDataError("SOURCE_FORMAT", type(error).__name__) from error
    return rows


def _example(row: dict[str, object]) -> PolicyExample:
    if (
        row.get("label_eligible") is not True
        or row.get("solver_status") != "OPTIMAL"
        or row.get("gap") != 0.0
    ):
        _fail("INELIGIBLE_LABEL", str(row.get("sample_id")))
    try:
        observation = Observation.model_validate(row.get("observation"))
    except (ValueError, TypeError) as error:
        raise PolicyDataError("OBSERVATION", type(error).__name__) from error
    stored_hash = row.get("observation_content_sha256")
    if stored_hash != observation_content_sha256(observation.model_dump()):
        _fail("OBSERVATION_HASH", str(row.get("sample_id")))
    encoded = encode_observation(observation)
    labels = row.get("candidate_scores")
    if not isinstance(labels, list):
        _fail("CANDIDATE_KEYS", "candidate_scores must be a list")
    by_key: dict[tuple[str | None, str], dict[str, object]] = {}
    for label in labels:
        if not isinstance(label, dict):
            _fail("CANDIDATE_KEYS", "Candidate label must be an object")
        key = (label.get("task_id"), label.get("mode"))
        if key in by_key:
            _fail("CANDIDATE_KEYS", f"Duplicate candidate {key}")
        by_key[key] = label
    if set(by_key) != set(encoded.candidate_keys):
        _fail("CANDIDATE_KEYS", str(row.get("sample_id")))
    scores = []
    feasible = []
    for key in encoded.candidate_keys:
        label = by_key[key]
        score = label.get("score")
        possible = label.get("feasible")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            _fail("LABEL_VALUE", f"Invalid score for {key}")
        if type(possible) is not bool:
            _fail("LABEL_VALUE", f"Invalid feasibility for {key}")
        scores.append(float(score))
        feasible.append(possible)
    sample_id = row.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id:
        _fail("IDENTIFIER", "Invalid sample ID")
    return PolicyExample(
        sample_id=sample_id,
        observation=observation,
        candidate_keys=encoded.candidate_keys,
        global_features=encoded.global_features,
        candidate_features=encoded.candidate_features,
        candidate_mask=encoded.candidate_mask,
        target_scores=tuple(scores),
        target_feasible=tuple(feasible),
    )


def _mean_scale(rows: tuple[tuple[float, ...], ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows or not rows[0]:
        _fail("NORMALIZATION", "Cannot fit empty feature rows")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        _fail("NORMALIZATION", "Feature width mismatch")
    means = tuple(sum(row[index] for row in rows) / len(rows) for index in range(width))
    scales = []
    for index, mean in enumerate(means):
        variance = sum((row[index] - mean) ** 2 for row in rows) / len(rows)
        scale = math.sqrt(variance)
        scales.append(scale if scale > 0.0 else 1.0)
    if not all(math.isfinite(value) for value in (*means, *scales)):
        _fail("NORMALIZATION", "Non-finite statistics")
    return means, tuple(scales)


def fit_normalization(examples: tuple[PolicyExample, ...]) -> Normalization:
    global_rows = tuple(example.global_features for example in examples)
    candidate_rows = tuple(row for example in examples for row in example.candidate_features)
    global_mean, global_scale = _mean_scale(global_rows)
    candidate_mean, candidate_scale = _mean_scale(candidate_rows)
    return Normalization(
        schema_version="policy-normalization-v1",
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        source_split="train",
        global_feature_names=GLOBAL_FEATURE_NAMES,
        candidate_feature_names=CANDIDATE_FEATURE_NAMES,
        global_mean=global_mean,
        global_scale=global_scale,
        candidate_mean=candidate_mean,
        candidate_scale=candidate_scale,
    )


def normalise_example(
    example: PolicyExample, normalization: Normalization
) -> tuple[tuple[float, ...], ...]:
    global_values = tuple(
        (value - mean) / scale
        for value, mean, scale in zip(
            example.global_features, normalization.global_mean, normalization.global_scale, strict=True
        )
    )
    rows = tuple(
        global_values
        + tuple(
            (value - mean) / scale
            for value, mean, scale in zip(
                candidate,
                normalization.candidate_mean,
                normalization.candidate_scale,
                strict=True,
            )
        )
        for candidate in example.candidate_features
    )
    if not all(math.isfinite(value) for row in rows for value in row):
        _fail("NORMALIZATION", "Non-finite normalized feature")
    return rows


def load_frozen_dataset(
    config_path: Path = DEFAULT_CONFIG, *, root: Path | None = None
) -> FrozenPolicyDataset:
    config_path = Path(config_path)
    repository_root = ROOT if root is None else Path(root)
    config = _read_json(config_path, "CONFIG")
    _validate_config(config)
    samples_path = _resolve(repository_root, config.get("dataset_path"), "dataset_path")
    summary_path = _resolve(repository_root, config.get("dataset_summary_path"), "dataset_summary_path")
    manifest_path = _resolve(repository_root, config.get("dataset_manifest_path"), "dataset_manifest_path")
    split_path = _resolve(repository_root, config.get("split_manifest_path"), "split_manifest_path")
    manifest = _read_json(manifest_path, "MANIFEST")
    summary = _read_json(summary_path, "SUMMARY")
    split = _read_json(split_path, "SPLIT")
    samples_sha = _sha256(samples_path)
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, dict) or outputs.get("samples.jsonl") != samples_sha:
        _fail("SOURCE_HASH", "samples.jsonl differs from manifest")
    if outputs.get("summary.json") != _sha256(summary_path):
        _fail("SOURCE_HASH", "summary.json differs from manifest")
    if split.get("source_jsonl_sha256") != samples_sha:
        _fail("SOURCE_HASH", "splits.json is bound to another source")
    if summary != {
        "eligible": 20,
        "failures": 0,
        "ineligible": 0,
        "solver_status_counts": {"OPTIMAL": 20},
        "status": "ready_for_split",
        "total": 20,
    }:
        _fail("SUMMARY", "Unexpected frozen summary")
    intersections = split.get("intersections")
    if not isinstance(intersections, dict) or any(
        values for pair in intersections.values() if isinstance(pair, dict) for values in pair.values()
    ):
        _fail("SPLIT_LEAKAGE", "Split intersections must be empty")
    rows = _read_rows(samples_path)
    if len(rows) != 20:
        _fail("SOURCE_FORMAT", "Expected 20 rows")
    examples = [_example(row) for row in rows]
    by_id = {example.sample_id: example for example in examples}
    if len(by_id) != len(examples):
        _fail("IDENTIFIER", "Duplicate sample ID")
    split_payload = split.get("splits")
    if not isinstance(split_payload, dict) or set(split_payload) != {"train", "validation", "test"}:
        _fail("SPLIT", "Missing split")
    result: dict[str, tuple[PolicyExample, ...]] = {}
    used = set()
    row_by_id = {row["sample_id"]: row for row in rows}
    for name, expected_count in (("train", 12), ("validation", 4), ("test", 4)):
        payload = split_payload[name]
        if not isinstance(payload, dict) or payload.get("sample_count") != expected_count:
            _fail("SPLIT", f"Unexpected {name} count")
        sample_ids = payload.get("sample_ids")
        if not isinstance(sample_ids, list) or len(sample_ids) != expected_count:
            _fail("SPLIT", f"Invalid {name} sample IDs")
        if used.intersection(sample_ids):
            _fail("SPLIT_LEAKAGE", f"Repeated sample in {name}")
        if any(sample_id not in by_id for sample_id in sample_ids):
            _fail("SPLIT", f"Unknown sample in {name}")
        selected_rows = [row_by_id[sample_id] for sample_id in sample_ids]
        expected_sets = {
            "scenario_ids": {row["scenario_id"] for row in selected_rows},
            "source_group_ids": {row["source_group_id"] for row in selected_rows},
            "observation_content_sha256": {
                row["observation_content_sha256"] for row in selected_rows
            },
        }
        for field, expected in expected_sets.items():
            if set(payload.get(field, ())) != expected:
                _fail("SPLIT", f"{name} {field} mismatch")
        used.update(sample_ids)
        result[name] = tuple(by_id[sample_id] for sample_id in sample_ids)
    if used != set(by_id):
        _fail("SPLIT", "Split coverage is incomplete")
    normalization = fit_normalization(result["train"])
    return FrozenPolicyDataset(
        splits=result,
        by_sample_id=by_id,
        normalization=normalization,
        samples_sha256=samples_sha,
        split_sha256=_sha256(split_path),
    )
