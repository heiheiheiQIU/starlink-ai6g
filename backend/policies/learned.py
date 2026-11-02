"""Validated NumPy inference for the frozen A-N3 learned scorer."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import numpy as np

from backend.contracts import CandidateScore, Observation
from training.policy_features import (
    CANDIDATE_FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    GLOBAL_FEATURE_NAMES,
    encode_observation,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/learned_policy.json"
ARRAY_SHAPES = {
    "layer1_weight": (32, 23),
    "layer1_bias": (32,),
    "layer2_weight": (16, 32),
    "layer2_bias": (16,),
    "utility_weight": (1, 16),
    "utility_bias": (1,),
    "feasibility_weight": (1, 16),
    "feasibility_bias": (1,),
}
_SHA256 = re.compile(r"[0-9a-f]{64}")


class LearnedPolicyError(ValueError):
    """Controlled learned-package or inference failure for gateway fallback."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class ModelBundle:
    model_version: str
    masked_score: float
    arrays: dict[str, np.ndarray]
    global_mean: np.ndarray
    global_scale: np.ndarray
    candidate_mean: np.ndarray
    candidate_scale: np.ndarray


def _fail(code: str, message: str):
    raise LearnedPolicyError(code, message)


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise LearnedPolicyError("MODEL_MISSING", str(path)) from error


def _config(value) -> dict[str, object]:
    try:
        if value is None:
            payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        elif isinstance(value, dict):
            payload = dict(value)
        else:
            payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise LearnedPolicyError("MODEL_CONFIG", type(error).__name__) from error
    if not isinstance(payload, dict):
        _fail("MODEL_CONFIG", "Configuration must be an object")
    if payload.get("enabled", True) is not True:
        _fail("MODEL_MISSING", "Learned package is not enabled")
    if payload.get("schema_version") != "learned-policy-config-v1":
        _fail("MODEL_CONFIG", "Unexpected configuration schema")
    if payload.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        _fail("MODEL_CONFIG", "Feature schema mismatch")
    for field in ("weights_sha256", "normalization_sha256"):
        digest = payload.get(field)
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            _fail("MODEL_CONFIG", f"Invalid {field}")
    model_version = payload.get("model_version")
    package_dir = payload.get("package_dir")
    masked_score = payload.get("masked_score")
    if not isinstance(model_version, str) or not model_version:
        _fail("MODEL_CONFIG", "Invalid model version")
    if not isinstance(package_dir, str) or not package_dir:
        _fail("MODEL_CONFIG", "Invalid package directory")
    if isinstance(masked_score, bool) or not isinstance(masked_score, (int, float)):
        _fail("MODEL_CONFIG", "Invalid masked score")
    masked_score = float(masked_score)
    if not math.isfinite(masked_score) or masked_score >= 0.0:
        _fail("MODEL_CONFIG", "Masked score must be finite and negative")
    package = Path(package_dir)
    if not package.is_absolute():
        package = ROOT / package
    payload["package_dir"] = str(package.resolve())
    payload["masked_score"] = masked_score
    return payload


def _normalization(path: Path, digest: str):
    if _sha256(path) != digest:
        _fail("MODEL_HASH", "normalization.json SHA256 mismatch")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LearnedPolicyError("NORMALIZATION_FORMAT", type(error).__name__) from error
    expected = {
        "schema_version": "policy-normalization-v1",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "source_split": "train",
        "global_feature_names": list(GLOBAL_FEATURE_NAMES),
        "candidate_feature_names": list(CANDIDATE_FEATURE_NAMES),
    }
    if not isinstance(payload, dict) or any(payload.get(key) != value for key, value in expected.items()):
        _fail("NORMALIZATION_FORMAT", "Normalization metadata mismatch")
    arrays = []
    for name, width, positive in (
        ("global_mean", 14, False),
        ("global_scale", 14, True),
        ("candidate_mean", 9, False),
        ("candidate_scale", 9, True),
    ):
        try:
            array = np.asarray(payload[name], dtype=np.float64)
        except (KeyError, TypeError, ValueError) as error:
            raise LearnedPolicyError("NORMALIZATION_FORMAT", name) from error
        if array.shape != (width,) or not np.isfinite(array).all():
            _fail("NORMALIZATION_FORMAT", name)
        if positive and not np.greater(array, 0.0).all():
            _fail("NORMALIZATION_FORMAT", name)
        array.setflags(write=False)
        arrays.append(array)
    return tuple(arrays)


@lru_cache(maxsize=8)
def _load_bundle(
    package_dir: str,
    weights_sha256: str,
    normalization_sha256: str,
    model_version: str,
    masked_score: float,
) -> ModelBundle:
    package = Path(package_dir)
    weights_path = package / "weights.npz"
    if _sha256(weights_path) != weights_sha256:
        _fail("MODEL_HASH", "weights.npz SHA256 mismatch")
    try:
        with np.load(weights_path, allow_pickle=False) as archive:
            if set(archive.files) != set(ARRAY_SHAPES):
                _fail("MODEL_FORMAT", "Unexpected weight array names")
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except LearnedPolicyError:
        raise
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, EOFError) as error:
        raise LearnedPolicyError("MODEL_FORMAT", type(error).__name__) from error
    for name, shape in ARRAY_SHAPES.items():
        array = arrays[name]
        if array.shape != shape or array.dtype != np.float32:
            _fail("MODEL_FORMAT", f"{name} shape or dtype")
        if not np.isfinite(array).all():
            _fail("MODEL_NONFINITE", name)
        array.setflags(write=False)
    global_mean, global_scale, candidate_mean, candidate_scale = _normalization(
        package / "normalization.json", normalization_sha256
    )
    return ModelBundle(
        model_version=model_version,
        masked_score=masked_score,
        arrays=arrays,
        global_mean=global_mean,
        global_scale=global_scale,
        candidate_mean=candidate_mean,
        candidate_scale=candidate_scale,
    )


def _bundle(config) -> ModelBundle:
    payload = _config(config)
    return _load_bundle(
        payload["package_dir"],
        payload["weights_sha256"],
        payload["normalization_sha256"],
        payload["model_version"],
        payload["masked_score"],
    )


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -80.0, 80.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def score_actions(observation: Observation, *, config=None) -> list[CandidateScore]:
    """Score every public candidate; the shared Guard remains authoritative."""
    try:
        observed = Observation.model_validate(observation)
        encoded = encode_observation(observed)
    except (ValueError, TypeError) as error:
        raise LearnedPolicyError("INVALID_OBSERVATION", type(error).__name__) from error
    bundle = _bundle(config)
    global_values = (
        np.asarray(encoded.global_features, dtype=np.float64) - bundle.global_mean
    ) / bundle.global_scale
    candidate_values = (
        np.asarray(encoded.candidate_features, dtype=np.float64) - bundle.candidate_mean
    ) / bundle.candidate_scale
    inputs = np.concatenate(
        (np.repeat(global_values[None, :], len(candidate_values), axis=0), candidate_values),
        axis=1,
    ).astype(np.float32)
    arrays = bundle.arrays
    hidden1 = np.maximum(inputs @ arrays["layer1_weight"].T + arrays["layer1_bias"], 0.0)
    hidden2 = np.maximum(hidden1 @ arrays["layer2_weight"].T + arrays["layer2_bias"], 0.0)
    utility = _sigmoid(hidden2 @ arrays["utility_weight"].T + arrays["utility_bias"])
    feasible = _sigmoid(
        hidden2 @ arrays["feasibility_weight"].T + arrays["feasibility_bias"]
    )
    scores = (utility[:, 0] * feasible[:, 0]).astype(np.float64)
    scores[~np.asarray(encoded.candidate_mask, dtype=bool)] = bundle.masked_score
    if scores.shape != (len(encoded.candidate_keys),) or not np.isfinite(scores).all():
        _fail("MODEL_NONFINITE", "Invalid inference output")
    return [
        CandidateScore(task_id=task_id, mode=mode, score=float(score))
        for (task_id, mode), score in zip(encoded.candidate_keys, scores, strict=True)
    ]
