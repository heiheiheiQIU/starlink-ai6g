"""The frozen learned package is validated before NumPy inference."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from backend.contracts import Observation
from backend.policies.learned import LearnedPolicyError, score_actions
from training.policy_features import CANDIDATE_FEATURE_NAMES, GLOBAL_FEATURE_NAMES


ROOT = Path(__file__).resolve().parents[1]
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


def observation(**updates):
    fixture = ROOT / "tests/fixtures/contracts/observation.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))["examples"][0]["payload"]
    payload.update(updates)
    return Observation.model_validate(payload)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_package(tmp_path: Path, *, mutate_arrays=None, mutate_normalization=None):
    package = tmp_path / "model"
    package.mkdir()
    arrays = {name: np.zeros(shape, dtype=np.float32) for name, shape in ARRAY_SHAPES.items()}
    if mutate_arrays:
        mutate_arrays(arrays)
    weights = package / "weights.npz"
    np.savez(weights, **arrays)
    normalization = {
        "schema_version": "policy-normalization-v1",
        "feature_schema_version": "policy-features-v1",
        "source_split": "train",
        "global_feature_names": list(GLOBAL_FEATURE_NAMES),
        "candidate_feature_names": list(CANDIDATE_FEATURE_NAMES),
        "global_mean": [0.0] * 14,
        "global_scale": [1.0] * 14,
        "candidate_mean": [0.0] * 9,
        "candidate_scale": [1.0] * 9,
    }
    if mutate_normalization:
        mutate_normalization(normalization)
    normalization_path = package / "normalization.json"
    normalization_path.write_text(json.dumps(normalization), encoding="utf-8")
    return {
        "schema_version": "learned-policy-config-v1",
        "model_version": "test-mlp-v1",
        "feature_schema_version": "policy-features-v1",
        "package_dir": str(package),
        "weights_sha256": sha256(weights),
        "normalization_sha256": sha256(normalization_path),
        "masked_score": -1.0,
    }


def test_complete_variable_candidate_output_uses_frozen_order(tmp_path):
    scores = score_actions(observation(), config=write_package(tmp_path))
    assert [(row.task_id, row.mode) for row in scores] == [
        ("T1", "robust"),
        ("T1", "fast"),
        (None, "idle"),
    ]
    assert [row.score for row in scores] == pytest.approx([0.25, 0.25, 0.25])


def test_structural_mask_keeps_complete_keys_but_ranks_idle_above_send(tmp_path):
    inflight = {
        "task_id": "T1",
        "block_id": 0,
        "payload_bytes": 1024,
        "mode": "fast",
        "sent_at_s": 0.0,
        "timeout_at_s": 2.0,
        "retries": 0,
    }
    scores = score_actions(
        observation(inflight=inflight), config=write_package(tmp_path)
    )
    assert [row.score for row in scores] == pytest.approx([-1.0, -1.0, 0.25])


def test_missing_rul_is_a_supported_public_observation(tmp_path):
    obs = observation()
    assert obs.health.rul_est is None
    assert len(score_actions(obs, config=write_package(tmp_path))) == 3


def test_missing_weights_is_controlled(tmp_path):
    config = write_package(tmp_path)
    (Path(config["package_dir"]) / "weights.npz").unlink()
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == "MODEL_MISSING"


def test_wrong_weights_hash_is_controlled(tmp_path):
    config = write_package(tmp_path)
    config["weights_sha256"] = "f" * 64
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == "MODEL_HASH"


def test_damaged_zip_is_controlled_model_format(tmp_path):
    config = write_package(tmp_path)
    weights = Path(config["package_dir"]) / "weights.npz"
    raw = b"PK\x03\x04broken archive payload"
    weights.write_bytes(raw)
    config["weights_sha256"] = hashlib.sha256(raw).hexdigest()

    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == "MODEL_FORMAT"


def test_truncated_zip_is_controlled_model_format(tmp_path):
    config = write_package(tmp_path)
    weights = Path(config["package_dir"]) / "weights.npz"
    raw = weights.read_bytes()[:-22]
    weights.write_bytes(raw)
    config["weights_sha256"] = hashlib.sha256(raw).hexdigest()

    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == "MODEL_FORMAT"


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda arrays: arrays.update(extra=np.zeros(1, dtype=np.float32)), "MODEL_FORMAT"),
        (lambda arrays: arrays.__setitem__("layer1_bias", np.zeros(31, dtype=np.float32)), "MODEL_FORMAT"),
        (lambda arrays: arrays.__setitem__("layer1_bias", np.zeros(32, dtype=np.float64)), "MODEL_FORMAT"),
        (
            lambda arrays: arrays["layer1_bias"].__setitem__(0, np.nan),
            "MODEL_NONFINITE",
        ),
    ],
    ids=["extra-array", "wrong-shape", "wrong-dtype", "nan"],
)
def test_invalid_weight_packages_are_controlled(tmp_path, mutation, expected):
    config = write_package(tmp_path, mutate_arrays=mutation)
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == expected


def test_normalization_feature_order_mismatch_is_controlled(tmp_path):
    def mutate(payload):
        payload["global_feature_names"] = list(reversed(payload["global_feature_names"]))

    config = write_package(tmp_path, mutate_normalization=mutate)
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(observation(), config=config)
    assert error.value.code == "NORMALIZATION_FORMAT"


def test_invalid_observation_is_controlled_before_model_loading(tmp_path):
    obs = observation()
    obs.sim_time_s = -1.0
    with pytest.raises(LearnedPolicyError) as error:
        score_actions(obs, config=write_package(tmp_path))
    assert error.value.code == "INVALID_OBSERVATION"


def test_default_frozen_package_scores_complete_finite_candidates():
    scores = score_actions(observation())
    assert [(row.task_id, row.mode) for row in scores] == [
        ("T1", "robust"),
        ("T1", "fast"),
        (None, "idle"),
    ]
    assert all(np.isfinite(row.score) for row in scores)


def test_default_manifest_hashes_every_frozen_package_file():
    package = ROOT / "artifacts/models/a_n3_policy_v1"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["model_version"] == "a-n3-mlp-v1"
    assert manifest["feature_schema_version"] == "policy-features-v1"
    for name, expected in manifest["artifacts_sha256"].items():
        assert sha256(package / name) == expected
