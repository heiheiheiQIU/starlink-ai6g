"""Deterministic training and non-pickle export for A-N3."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from training.policy_dataset import load_frozen_dataset
from training.train_policy import (
    export_state_dict,
    train_seed,
    write_deterministic_npz,
)


def test_deterministic_npz_is_byte_identical_and_non_pickle(tmp_path):
    arrays = {
        "layer1_bias": np.zeros(32, dtype=np.float32),
        "utility_bias": np.array([0.5], dtype=np.float32),
    }
    left, right = tmp_path / "left.npz", tmp_path / "right.npz"
    write_deterministic_npz(left, arrays)
    write_deterministic_npz(right, dict(reversed(list(arrays.items()))))
    assert left.read_bytes() == right.read_bytes()
    with np.load(left, allow_pickle=False) as loaded:
        assert sorted(loaded.files) == sorted(arrays)
        assert loaded["utility_bias"].tolist() == pytest.approx([0.5])


def test_same_seed_repeats_exact_parameters_and_metrics():
    data = load_frozen_dataset()
    left = train_seed(data, seed=20261031, epochs=20)
    right = train_seed(data, seed=20261031, epochs=20)
    assert left.metrics == right.metrics
    assert left.seed == right.seed == 20261031
    assert all(
        torch.equal(left.state_dict[key], right.state_dict[key])
        for key in left.state_dict
    )


def test_exported_array_names_shapes_and_dtypes_match_runtime_contract():
    result = train_seed(load_frozen_dataset(), seed=20261031, epochs=1)
    arrays = export_state_dict(result.state_dict)
    assert {name: value.shape for name, value in arrays.items()} == {
        "layer1_weight": (32, 23),
        "layer1_bias": (32,),
        "layer2_weight": (16, 32),
        "layer2_bias": (16,),
        "utility_weight": (1, 16),
        "utility_bias": (1,),
        "feasibility_weight": (1, 16),
        "feasibility_bias": (1,),
    }
    assert all(value.dtype == np.float32 for value in arrays.values())
    assert all(np.isfinite(value).all() for value in arrays.values())


def test_training_uses_three_fixed_seeds_and_frozen_hyperparameters():
    config = json.loads(
        (Path(__file__).resolve().parents[1] / "configs/policy_train.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["training_seeds"] == [20261031, 20261032, 20261033]
    assert config["model"] == {"input_width": 23, "hidden_widths": [32, 16]}
    assert config["optimizer"] == {
        "name": "Adam",
        "learning_rate": 0.01,
        "weight_decay": 0.0,
        "epochs": 2000,
        "feasibility_loss_weight": 0.25,
    }
    assert config["training_enabled"] is False
