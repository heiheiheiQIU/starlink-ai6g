"""Validated access to the frozen legacy battery windows and checkpoints."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import Sequence
from zipfile import BadZipFile

import numpy as np

from training.legacy_audit import sha256_file, window_available_index


FEATURE_ORDER = (
    "voltage_mean_V",
    "voltage_min_V",
    "voltage_end_V",
    "current_mean_A",
    "temperature_mean_C",
    "temperature_max_C",
    "capacity_Ah",
    "resistance_Re_Ohm",
    "resistance_Rct_Ohm",
    "resistance",
    "soc",
)


class HealthInputError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


class HealthModelError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class LegacyPrediction:
    raw_fraction: tuple[float, ...]
    run_ids: tuple[str, ...]
    start_indices: tuple[int, ...]
    available_indices: tuple[int, ...]
    step_unit: str
    model_id: str
    checkpoint_sha256: str


def predict_npz_windows(
    npz_path: Path,
    checkpoint_path: Path,
    model_kind: str,
    sample_indices: Sequence[int],
    *,
    now_index: int,
) -> LegacyPrediction:
    """Run selected, already available NPZ windows through a strict CPU model."""
    if model_kind not in {"lstm", "bilstm_attention"}:
        raise HealthInputError("MODEL_KIND_INVALID", f"Unsupported model kind: {model_kind}")
    indices = tuple(sample_indices)
    if not indices or any(not isinstance(index, (int, np.integer)) or isinstance(index, (bool, np.bool_)) for index in indices):
        raise HealthInputError("SAMPLE_INDICES_INVALID", "Sample indices must be nonempty integers")
    if len(set(indices)) != len(indices):
        raise HealthInputError("SAMPLE_INDICES_INVALID", "Sample indices must be unique")
    if not isinstance(now_index, (int, np.integer)) or isinstance(now_index, (bool, np.bool_)):
        raise HealthInputError("NOW_INDEX_INVALID", "now_index must be an integer in the NPZ native step unit")

    try:
        with np.load(Path(npz_path), allow_pickle=False) as archive:
            x = archive["X"]
            features = tuple(str(name) for name in archive["feature_names"].tolist())
            starts = archive["time_index"]
            runs = archive["run_id"]
            window_size = archive["window_size"].item()
            step_unit = str(archive["step_unit"].item())
            if step_unit not in {"cycle", "orbit"}:
                raise HealthInputError("STEP_UNIT_INVALID", "Expected cycle or orbit metadata")
            if (starts.ndim != 1 or not np.issubdtype(starts.dtype, np.integer)
                    or np.any(starts < 0) or runs.ndim != 1):
                raise HealthInputError("WINDOW_METADATA_INVALID", "Window starts must be non-negative integer vectors and run IDs must be a vector")
            if features != FEATURE_ORDER:
                raise HealthInputError("FEATURE_ORDER_MISMATCH", "NPZ feature names differ from the 11-feature model order")
            if window_size != 15 or x.ndim != 3 or x.shape[1:] != (15, len(FEATURE_ORDER)) or len(starts) != len(x) or len(runs) != len(x):
                raise HealthInputError("WINDOW_SHAPE_INVALID", "NPZ must declare and contain 15-step windows with consistent metadata")
            window_size = int(window_size)
            if any(index < 0 or index >= len(x) for index in indices):
                raise HealthInputError("SAMPLE_INDICES_INVALID", "Sample index is outside the NPZ")
            selected = x[list(indices)]
            if not np.isfinite(selected).all():
                raise HealthInputError("WINDOW_NONFINITE", "Selected windows contain non-finite values")
            available_indices = tuple(window_available_index(int(starts[index]), window_size) for index in indices)
            if any(available > now_index for available in available_indices):
                raise HealthInputError("WINDOW_NOT_AVAILABLE", "A selected window extends past now_index")
            start_indices = tuple(int(starts[index]) for index in indices)
            run_ids = tuple(str(runs[index]) for index in indices)
    except HealthInputError:
        raise
    except (BadZipFile, EOFError, OSError, KeyError, TypeError, ValueError) as exc:
        raise HealthInputError("NPZ_INVALID", f"Could not read NPZ windows: {exc}") from exc

    if not Path(checkpoint_path).is_file():
        raise HealthModelError("MODEL_NOT_FOUND", f"Checkpoint not found: {checkpoint_path}")

    import torch

    from backend.health.legacy_models import BiLSTMAttention, LSTMRegressor

    model = LSTMRegressor() if model_kind == "lstm" else BiLSTMAttention()
    try:
        state = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=True)
    except (OSError, RuntimeError, ValueError, TypeError, EOFError, pickle.UnpicklingError) as exc:
        raise HealthModelError("MODEL_LOAD_FAILED", f"Could not load checkpoint: {exc}") from exc
    if not isinstance(state, Mapping):
        raise HealthModelError("STATE_DICT_MISMATCH", "Checkpoint must contain a state dictionary mapping")
    try:
        model.load_state_dict(state, strict=True)
    except (RuntimeError, TypeError, ValueError) as exc:
        raise HealthModelError("STATE_DICT_MISMATCH", f"Checkpoint does not match {model_kind}: {exc}") from exc

    model.eval()
    with torch.inference_mode():
        output = model(torch.from_numpy(np.ascontiguousarray(selected, dtype=np.float32)))
    if output.shape != (len(indices), 1) or not torch.isfinite(output).all().item():
        raise HealthModelError("MODEL_OUTPUT_INVALID", "Model output must be finite and preserve batch size")
    return LegacyPrediction(
        raw_fraction=tuple(float(value) for value in output[:, 0].tolist()),
        run_ids=run_ids,
        start_indices=start_indices,
        available_indices=available_indices,
        step_unit=step_unit,
        model_id=Path(checkpoint_path).stem,
        checkpoint_sha256=sha256_file(Path(checkpoint_path)),
    )
