import builtins
import math
from pathlib import Path

import numpy as np
import pytest

from backend.health.legacy_adapter import (
    FEATURE_ORDER,
    HealthInputError,
    HealthModelError,
    predict_npz_windows,
)
from training.legacy_audit import load_asset_config, sha256_file


@pytest.fixture
def asset_config():
    return load_asset_config(Path("configs/legacy_assets.json"))


@pytest.mark.parametrize(("window_size", "sequence_length"), [(1, 1), (1, 15), (15, 1), (15.5, 15)])
def test_frozen_window_length_is_required_before_torch_import(
    tmp_path, monkeypatch, window_size, sequence_length,
):
    malformed = tmp_path / "wrong_window.npz"
    np.savez(
        malformed,
        X=np.zeros((1, sequence_length, 11), dtype=np.float32),
        feature_names=np.array(FEATURE_ORDER),
        time_index=np.array([0]),
        run_id=np.array(["R1"]),
        window_size=np.array(window_size),
        step_unit=np.array("cycle"),
    )
    original_import = builtins.__import__

    def reject_torch_import(name, *args, **kwargs):
        assert name != "torch", "Invalid window reached the PyTorch import"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_torch_import)
    checkpoint = tmp_path / "never_loaded.pt"
    checkpoint.touch()
    with pytest.raises(HealthInputError, match="WINDOW_SHAPE_INVALID") as error:
        predict_npz_windows(malformed, checkpoint, "lstm", [0], now_index=100)
    assert error.value.code == "WINDOW_SHAPE_INVALID"


def write_npz_without_feature(source: Path, output_dir: Path, feature: str) -> Path:
    with np.load(source, allow_pickle=False) as data:
        names = data["feature_names"].tolist()
        keep = [index for index, name in enumerate(names) if name != feature]
        output = output_dir / "missing_feature.npz"
        np.savez_compressed(
            output,
            X=data["X"][:, :, keep],
            y=data["y"],
            y_fraction=data["y_fraction"],
            run_id=data["run_id"],
            time_index=data["time_index"],
            feature_names=data["feature_names"][keep],
            window_size=data["window_size"],
            stride=data["stride"],
            step_unit=data["step_unit"],
            rul_unit=data["rul_unit"],
        )
    return output


def test_future_window_is_rejected(asset_config):
    with pytest.raises(HealthInputError, match="WINDOW_NOT_AVAILABLE"):
        predict_npz_windows(
            asset_config.source_npz,
            asset_config.checkpoints["lstm_source"],
            "lstm", [0], now_index=13,
        )


def test_missing_feature_is_rejected(asset_config, tmp_path):
    broken = write_npz_without_feature(asset_config.source_npz, tmp_path, "soc")
    with pytest.raises(HealthInputError, match="FEATURE_ORDER_MISMATCH"):
        predict_npz_windows(
            broken, asset_config.checkpoints["lstm_source"],
            "lstm", [0], now_index=1000,
        )


def test_missing_checkpoint_is_rejected(asset_config, tmp_path):
    with pytest.raises(HealthModelError, match="MODEL_NOT_FOUND"):
        predict_npz_windows(
            asset_config.source_npz, tmp_path / "missing.pt",
            "lstm", [0], now_index=1000,
        )


@pytest.mark.parametrize("damage", ["truncated", "empty", "invalid_format"])
def test_corrupt_npz_is_stable_input_error(tmp_path, damage):
    broken = tmp_path / "corrupt.npz"
    np.savez(broken, X=np.zeros((1, 15, 11)))
    contents = broken.read_bytes()
    broken.write_bytes({"truncated": contents[:-30], "empty": b"", "invalid_format": b"not an NPZ archive"}[damage])
    with pytest.raises(HealthInputError, match="NPZ_INVALID") as error:
        predict_npz_windows(broken, tmp_path / "unused.pt", "lstm", [0], now_index=100)
    assert error.value.code == "NPZ_INVALID"


def test_empty_checkpoint_is_model_load_failure(asset_config, tmp_path):
    empty_checkpoint = tmp_path / "empty.pt"
    empty_checkpoint.write_bytes(b"")
    with pytest.raises(HealthModelError, match="MODEL_LOAD_FAILED") as error:
        predict_npz_windows(
            asset_config.source_npz, empty_checkpoint,
            "lstm", [0], now_index=10_000,
        )
    assert error.value.code == "MODEL_LOAD_FAILED"


def test_pickled_module_is_model_load_failure(asset_config, tmp_path):
    import torch

    pickled_checkpoint = tmp_path / "module.pt"
    torch.save(torch.nn.Linear(11, 1), pickled_checkpoint)
    with pytest.raises(HealthModelError, match="MODEL_LOAD_FAILED") as error:
        predict_npz_windows(
            asset_config.source_npz, pickled_checkpoint,
            "lstm", [0], now_index=10_000,
        )
    assert error.value.code == "MODEL_LOAD_FAILED"


def test_lstm_checkpoint_runs_two_distinct_windows(asset_config):
    prediction = predict_npz_windows(
        asset_config.source_npz,
        asset_config.checkpoints["lstm_source"],
        "lstm", [0, 1], now_index=10_000,
    )
    assert len(prediction.raw_fraction) == 2
    assert all(math.isfinite(value) for value in prediction.raw_fraction)
    assert prediction.checkpoint_sha256 == sha256_file(
        asset_config.checkpoints["lstm_source"]
    )
    assert prediction.start_indices == (0, 3)
    assert prediction.available_indices == (14, 17)
    assert prediction.step_unit == "cycle"

    reversed_prediction = predict_npz_windows(
        asset_config.source_npz,
        asset_config.checkpoints["lstm_source"],
        "lstm", [1, 0], now_index=10_000,
    )
    assert reversed_prediction.start_indices == (3, 0)
    assert reversed_prediction.available_indices == (17, 14)
    assert reversed_prediction.raw_fraction == tuple(reversed(prediction.raw_fraction))


def test_bilstm_checkpoint_requires_matching_architecture(asset_config):
    prediction = predict_npz_windows(
        asset_config.target_npz,
        asset_config.checkpoints["bilstm_coral"],
        "bilstm_attention", [0, 1], now_index=10_000,
    )
    assert len(prediction.raw_fraction) == 2
    assert prediction.step_unit == "orbit"


def test_wrong_architecture_fails_strictly(asset_config):
    with pytest.raises(HealthModelError, match="STATE_DICT_MISMATCH"):
        predict_npz_windows(
            asset_config.target_npz,
            asset_config.checkpoints["bilstm_coral"],
            "lstm", [0], now_index=10_000,
        )


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_selected_window_nonfinite_input_is_rejected(tmp_path, invalid_value):
    broken = tmp_path / "nonfinite.npz"
    windows = np.zeros((2, 15, 11), dtype=np.float32)
    windows[1, 3, 4] = invalid_value
    np.savez(
        broken, X=windows, feature_names=np.array(FEATURE_ORDER),
        time_index=np.array([0, 3]), run_id=np.array(["R1", "R1"]),
        window_size=np.array(15), step_unit=np.array("cycle"),
    )
    with pytest.raises(HealthInputError, match="WINDOW_NONFINITE") as error:
        predict_npz_windows(broken, tmp_path / "unused.pt", "lstm", [1], now_index=100)
    assert error.value.code == "WINDOW_NONFINITE"


@pytest.mark.parametrize(
    ("output_shape", "output_value"),
    [((2, 1), float("nan")), ((2, 1), float("inf")), ((2, 1), -float("inf")),
     ((1, 1), 0.5), ((2,), 0.5), ((2, 2), 0.5)],
    ids=["nan", "positive-infinity", "negative-infinity", "wrong-batch", "missing-column", "extra-column"],
)
def test_invalid_model_output_is_rejected(asset_config, monkeypatch, output_shape, output_value):
    import torch
    from backend.health.legacy_models import LSTMRegressor

    # Preserve real construction, CPU checkpoint loading, strict matching, and eval.
    # Override only forward because valid frozen checkpoints do not emit these failures.
    def invalid_forward(self, windows):
        assert windows.shape == (2, 15, 11)
        return torch.full(output_shape, output_value)

    monkeypatch.setattr(LSTMRegressor, "forward", invalid_forward)
    with pytest.raises(HealthModelError, match="MODEL_OUTPUT_INVALID") as error:
        predict_npz_windows(
            asset_config.source_npz, asset_config.checkpoints["lstm_source"],
            "lstm", [0, 1], now_index=10_000,
        )
    assert error.value.code == "MODEL_OUTPUT_INVALID"
