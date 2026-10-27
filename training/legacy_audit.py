"""Resolve the read-only legacy battery assets configured for this project."""

from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from zipfile import BadZipFile

import numpy as np


REQUIRED_NPZ_KEYS = frozenset(
    {
        "X",
        "y",
        "y_fraction",
        "run_id",
        "time_index",
        "feature_names",
        "window_size",
        "stride",
        "step_unit",
        "rul_unit",
    }
)


class AuditError(ValueError):
    """Raised when a legacy asset does not satisfy the audit contract."""


@dataclass(frozen=True)
class NpzAudit:
    shape: tuple[int, ...]
    window_size: int
    stride: int
    step_unit: str
    rul_unit: str
    finite_x: bool
    finite_y: bool
    finite_y_fraction: bool
    run_count: int
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class ManifestCheck:
    sha256_matches: bool
    size_matches: bool
    expected_sha256: str
    actual_sha256: str
    expected_size: int
    actual_size: int


@dataclass(frozen=True)
class LabelLineageCheck:
    comparable: int
    exact_matches: int
    missing: int
    max_abs_difference: float


@dataclass(frozen=True)
class AssetConfig:
    config_path: Path
    package_root: Path
    legacy_root: Path
    source_npz: Path
    target_npz: Path
    source_csv: Path
    fixed_source_csv: Path
    checkpoints: Mapping[str, Path]


def window_available_index(start_index: int, window_size: int) -> int:
    """Map a window's legacy start index to its final observed row index."""
    if start_index < 0:
        raise ValueError("start_index must be non-negative")
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    return start_index + window_size - 1


def compare_label_lineage(npz_path: Path, csv_path: Path) -> LabelLineageCheck:
    """Compare NPZ labels to CSV RUL at each window's final observed row."""
    with np.load(Path(npz_path), allow_pickle=False) as archive:
        run_ids = archive["run_id"]
        start_indices = archive["time_index"]
        labels = archive["y"]
        window_size = int(archive["window_size"].item())
    sample_counts = (len(run_ids), len(start_indices), len(labels))
    if len(set(sample_counts)) != 1:
        raise AuditError(
            "NPZ run_id, time_index, and y arrays must contain the same number of entries"
        )

    rows_by_run: dict[str, list[tuple[float, float]]] = {}
    try:
        with Path(csv_path).open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames or not {"run_id", "time_index", "rul_cycles"}.issubset(reader.fieldnames):
                raise AuditError("CSV must contain run_id, time_index, and rul_cycles columns")
            for row in reader:
                raw_rul = (row.get("rul_cycles") or "").strip()
                if not raw_rul:
                    continue
                run_id = (row.get("run_id") or "").strip()
                if not run_id:
                    continue
                try:
                    time_index = float(row["time_index"])
                    rul_cycles = float(raw_rul)
                except (KeyError, TypeError, ValueError) as exc:
                    raise AuditError("CSV contains a non-numeric time_index or rul_cycles value") from exc
                rows_by_run.setdefault(run_id, []).append((time_index, rul_cycles))
    except OSError as exc:
        raise AuditError(f"Could not read label CSV {csv_path}: {exc}") from exc

    for rows in rows_by_run.values():
        rows.sort(key=lambda row: row[0])

    comparable = 0
    exact_matches = 0
    missing = 0
    max_abs_difference = 0.0
    for run_id, start_index, label in zip(run_ids, start_indices, labels):
        rows = rows_by_run.get(str(run_id), ())
        available_index = window_available_index(int(start_index), window_size)
        if available_index >= len(rows):
            missing += 1
            continue
        comparable += 1
        difference = abs(float(label) - rows[available_index][1])
        max_abs_difference = max(max_abs_difference, difference)
        if difference == 0.0:
            exact_matches += 1

    return LabelLineageCheck(
        comparable=comparable,
        exact_matches=exact_matches,
        missing=missing,
        max_abs_difference=max_abs_difference,
    )


def sha256_file(path: Path) -> str:
    """Return the uppercase SHA256 digest of a file, streaming in chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as asset_file:
        for chunk in iter(lambda: asset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def inspect_npz(path: Path) -> NpzAudit:
    """Read and validate the structure and numeric contents of a legacy NPZ."""
    try:
        with np.load(Path(path), allow_pickle=False) as archive:
            keys = set(archive.files)
            if keys != REQUIRED_NPZ_KEYS:
                missing = sorted(REQUIRED_NPZ_KEYS - keys)
                extra = sorted(keys - REQUIRED_NPZ_KEYS)
                raise AuditError(f"NPZ keys differ from the required set; missing={missing}, extra={extra}")

            x = archive["X"]
            y = archive["y"]
            y_fraction = archive["y_fraction"]
            raw_window = archive["window_size"].item()
            raw_stride = archive["stride"].item()
            if raw_window != 15 or raw_stride != 3:
                raise AuditError("Frozen assets require window_size=15 and stride=3")
            window_size, stride = int(raw_window), int(raw_stride)
            features = archive["feature_names"]
            starts = archive["time_index"]
            runs = archive["run_id"]
            if x.ndim != 3 or x.shape[1:] != (15, 11) or features.shape != (11,):
                raise AuditError("Frozen X must have shape (N,15,11) with 11 feature names")
            if any(a.shape != (len(x),) for a in (y, y_fraction, starts, runs)):
                raise AuditError("Labels, run IDs and time indices must be vectors matching X sample count")
            if not np.issubdtype(starts.dtype, np.integer) or np.any(starts < 0):
                raise AuditError("time_index must contain non-negative integers")
            step_unit = str(archive["step_unit"].item())
            rul_unit = str(archive["rul_unit"].item())
            if {"cycle": "cycles", "orbit": "orbits"}.get(step_unit) != rul_unit:
                raise AuditError("Unsupported or inconsistent step/RUL units")
            if not (np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(y_fraction).all()):
                raise AuditError("X, y, and y_fraction must contain only finite values")

            feature_names = tuple(str(name) for name in archive["feature_names"].tolist())
            run_ids = archive["run_id"]
            return NpzAudit(
                shape=tuple(int(dimension) for dimension in x.shape),
                window_size=window_size,
                stride=stride,
                step_unit=str(archive["step_unit"].item()),
                rul_unit=str(archive["rul_unit"].item()),
                finite_x=bool(np.isfinite(x).all()),
                finite_y=bool(np.isfinite(y).all()),
                finite_y_fraction=bool(np.isfinite(y_fraction).all()),
                run_count=int(np.unique(run_ids).size),
                feature_names=feature_names,
            )
    except AuditError:
        raise
    except (BadZipFile, EOFError, OSError, ValueError, KeyError, TypeError) as exc:
        raise AuditError(f"Could not audit NPZ file {path}: {exc}") from exc


def verify_manifest_asset(path: Path, package_root: Path) -> ManifestCheck:
    """Compare an asset's byte size and SHA256 to its unique manifest row."""
    asset_path = Path(path).resolve(strict=True)
    root = Path(package_root).resolve(strict=True)
    try:
        relative_path = asset_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise AuditError(f"Asset is outside the package root: {asset_path}") from exc

    manifest_path = root / "SOURCE_MANIFEST.csv"
    try:
        with manifest_path.open(encoding="utf-8-sig", newline="") as manifest_file:
            rows = [row for row in csv.DictReader(manifest_file) if row.get("PackagePath") == relative_path]
    except OSError as exc:
        raise AuditError(f"Could not read package manifest {manifest_path}: {exc}") from exc
    if len(rows) != 1:
        raise AuditError(f"Expected exactly one manifest row for {relative_path}; found {len(rows)}")

    try:
        expected_size = int(rows[0]["Bytes"])
        expected_sha256 = rows[0]["SHA256"].strip().upper()
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError(f"Manifest row for {relative_path} has invalid size or SHA256") from exc
    actual_size = asset_path.stat().st_size
    actual_sha256 = sha256_file(asset_path)
    return ManifestCheck(
        sha256_matches=actual_sha256 == expected_sha256,
        size_matches=actual_size == expected_size,
        expected_sha256=expected_sha256,
        actual_sha256=actual_sha256,
        expected_size=expected_size,
        actual_size=actual_size,
    )


def load_asset_config(path: Path) -> AssetConfig:
    """Load asset locations and require every configured file to exist."""
    config_path = path.resolve(strict=True)
    with config_path.open(encoding="utf-8") as config_file:
        settings = json.load(config_file)

    repository_root = config_path.parent.parent
    legacy_root = (repository_root / settings["legacy_root"]).resolve()
    if not legacy_root.is_dir():
        raise FileNotFoundError(legacy_root)

    def asset(relative_path: str) -> Path:
        resolved = (legacy_root / relative_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved

    checkpoints = MappingProxyType(
        {name: asset(relative_path) for name, relative_path in settings["checkpoints"].items()}
    )
    return AssetConfig(
        config_path=config_path,
        package_root=legacy_root.parents[1],
        legacy_root=legacy_root,
        source_npz=asset(settings["source_npz"]),
        target_npz=asset(settings["target_npz"]),
        source_csv=asset(settings["source_csv"]),
        fixed_source_csv=asset(settings["fixed_source_csv"]),
        checkpoints=checkpoints,
    )
