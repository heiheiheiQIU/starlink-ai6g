"""Generate reproducible, read-only evidence for the frozen battery assets."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
import sys

import numpy as np
import torch

from backend.health.legacy_adapter import HealthInputError, predict_npz_windows
from training.legacy_audit import (
    AuditError,
    compare_label_lineage,
    inspect_npz,
    load_asset_config,
    verify_manifest_asset,
)


OUTPUT_PATHS = (
    "data/manifests/legacy.csv",
    "data/manifests/assets_audit.json",
    "docs/asset_audit.md",
    "docs/evidence/A1/health_success.json",
    "docs/evidence/A1/health_missing_rul.json",
    "docs/evidence/A1/health_invalid.json",
    "docs/evidence/A1/smoke.log",
)


def validate_output_destinations(output_root: Path, package_root: Path) -> None:
    """Keep every output within its root and outside the entire frozen package."""
    output_root = output_root.resolve()
    package_root = package_root.resolve()
    if output_root.is_relative_to(package_root):
        raise AuditError("Output root must be outside the frozen package root")
    for relative_path in OUTPUT_PATHS:
        destination = (output_root / relative_path).resolve()
        if destination.is_relative_to(package_root):
            raise AuditError(f"Output destination is inside the frozen package root: {relative_path}")
        if not destination.is_relative_to(output_root):
            raise AuditError(f"Output destination is outside the output root: {relative_path}")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def prediction_record(prediction) -> dict[str, object]:
    return {
        "model_id": prediction.model_id,
        "checkpoint_sha256": prediction.checkpoint_sha256,
        "step_unit": prediction.step_unit,
        "windows": [
            {
                "run_id": run_id,
                "start_index": start,
                "available_index": available,
                "raw_fraction": fraction,
            }
            for run_id, start, available, fraction in zip(
                prediction.run_ids,
                prediction.start_indices,
                prediction.available_indices,
                prediction.raw_fraction,
                strict=True,
            )
        ],
    }


def generate(config_path: Path, output_root: Path) -> None:
    config = load_asset_config(config_path)
    output_root = output_root.resolve()
    validate_output_destinations(output_root, config.package_root)

    assets = [
        ("source_npz", config.source_npz),
        ("target_npz", config.target_npz),
        ("source_csv", config.source_csv),
        ("fixed_source_csv", config.fixed_source_csv),
        *sorted(config.checkpoints.items()),
    ]
    with (config.package_root / "SOURCE_MANIFEST.csv").open(encoding="utf-8-sig", newline="") as manifest_file:
        manifest = {row["PackagePath"]: row for row in csv.DictReader(manifest_file)}

    rows = []
    for purpose, path in assets:
        check = verify_manifest_asset(path, config.package_root)
        if not (check.sha256_matches and check.size_matches):
            raise AuditError(f"Manifest SHA or size mismatch: {purpose}")
        relative = path.relative_to(config.package_root).as_posix()
        rows.append({
            "asset_path": relative,
            "source_path": manifest[relative]["SourcePath"],
            "sha256": check.actual_sha256,
            "size_bytes": check.actual_size,
            "purpose": purpose,
            "status": "manifest_verified",
        })
    rows.sort(key=lambda row: row["asset_path"])

    source = inspect_npz(config.source_npz)
    target = inspect_npz(config.target_npz)
    original = compare_label_lineage(config.source_npz, config.source_csv)
    fixed = compare_label_lineage(config.source_npz, config.fixed_source_csv)
    lstm = predict_npz_windows(config.source_npz, config.checkpoints["lstm_source"], "lstm", [0, 1], now_index=10_000)
    bilstm = predict_npz_windows(config.target_npz, config.checkpoints["bilstm_coral"], "bilstm_attention", [0, 1], now_index=10_000)
    try:
        predict_npz_windows(config.source_npz, config.checkpoints["lstm_source"], "lstm", [0], now_index=13)
    except HealthInputError as error:
        invalid = {"status": "rejected", "error_code": error.code, "message": str(error), "sample_indices": [0], "now_index": 13, "step_unit": source.step_unit}
    else:
        raise AuditError("Future-window rejection did not occur")

    environment = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pytorch": torch.__version__,
        "device": "cpu",
        "cpu": platform.processor() or platform.machine(),
    }
    audit = {
        "schema_version": "1.0",
        "assets": rows,
        "npz": {"source": asdict(source), "target": asdict(target)},
        "label_lineage": {"original_csv": asdict(original), "fixed_csv": asdict(fixed)},
        "environment": environment,
        "inference": {"lstm_source": prediction_record(lstm), "bilstm_coral": prediction_record(bilstm)},
    }
    manifest_path = output_root / "data/manifests/legacy.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=("asset_path", "source_path", "sha256", "size_bytes", "purpose", "status"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_json(output_root / "data/manifests/assets_audit.json", audit)
    evidence = output_root / "docs/evidence/A1"
    write_json(evidence / "health_success.json", {
        "status": "success",
        "kind": "A1_checkpoint_evidence",
        "models": audit["inference"],
        "note": "Raw normalized predictions from delivered NPZ windows; not a B HealthEstimate",
    })
    write_json(evidence / "health_missing_rul.json", {
        "status": "native_rul_unavailable",
        "kind": "A1_checkpoint_evidence",
        "model_id": lstm.model_id,
        "raw_fraction": list(lstm.raw_fraction),
        "rul_est": None,
        "rul_unit": source.rul_unit,
        "step_unit": source.step_unit,
        "reason_codes": ["NATIVE_RUL_RESTORE_REQUIRES_FUTURE_RUN_MAX"],
    })
    write_json(evidence / "health_invalid.json", invalid)
    report = f"""# A1 legacy battery asset audit

Generated by `python -m training.inspect_legacy --config configs/legacy_assets.json --output-root .` from the frozen sibling package. Hashes and sizes are in `data/manifests/legacy.csv`; machine-readable details are in `data/manifests/assets_audit.json`.

## Confirmed

- All {len(rows)} configured assets match their unique package manifest SHA256 and size.
- Source NPZ: {source.shape} windows, {source.run_count} runs, {source.step_unit} steps and {source.rul_unit} labels.
- Target NPZ: {target.shape} windows, {target.run_count} runs, {target.step_unit} steps and {target.rul_unit} labels.
- Source NPZ labels match the fixed CSV exactly for {fixed.exact_matches}/{fixed.comparable} comparable windows; missing={fixed.missing}.
- Strict CPU LSTM and BiLSTM-Attention checkpoints each produced raw normalized predictions for two distinct delivered windows. The first source window starts at index {lstm.start_indices[0]} and is available at index {lstm.available_indices[0]}.
- Environment: Python {environment['python']}; NumPy {environment['numpy']}; PyTorch {environment['pytorch']}; CPU {environment['cpu']}.

## Conflicting lineage

- The original source CSV matches only {original.exact_matches}/{original.comparable} comparable NPZ labels, with {original.missing} missing and maximum absolute difference {original.max_abs_difference}. The fixed CSV matches all source NPZ labels. The legacy preprocessing entry point refers to the original CSV, so its lineage is not established by the delivered NPZ.

## Unverified boundaries

- No persisted scaler has been established for transforming new raw telemetry into the checkpoint feature space. Evidence uses only delivered standardized NPZ windows.
- Native online RUL restoration requires a future run maximum, so `rul_est` remains null. Raw normalized prediction must not be interpreted as SOC, capacity, energy, or online RUL.
- Target NPZ label lineage to its originating CSV and satellite operational validity remain unverified. These results are not new communication experiments.

## Reproduce

```powershell
& '.\\.venv\\Scripts\\python.exe' -m training.inspect_legacy --config configs/legacy_assets.json --output-root .
& '.\\.venv\\Scripts\\python.exe' -m pytest tests/test_legacy_audit.py tests/test_health.py -q --noconftest -p no:cacheprovider
```
"""
    report_path = output_root / "docs/asset_audit.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    smoke_log = (
        f"A1 audit generated: {len(rows)} manifest-verified assets; source SHA256={rows[next(i for i, row in enumerate(rows) if row['purpose'] == 'source_npz')]['sha256']}\n"
        f"Lineage: fixed={fixed.exact_matches}/{fixed.comparable}; original={original.exact_matches}/{original.comparable}, missing={original.missing}\n"
        "Inference: two source LSTM and two target BiLSTM windows; native RUL unavailable\n"
    )
    (evidence / "smoke.log").write_text(smoke_log, encoding="utf-8")
    print(smoke_log, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        generate(args.config, args.output_root)
    except (AuditError, FileNotFoundError, HealthInputError) as error:
        parser.exit(1, f"A1 audit failed: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
