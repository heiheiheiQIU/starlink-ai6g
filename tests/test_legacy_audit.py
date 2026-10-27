from pathlib import Path
from dataclasses import replace
import os
import subprocess
import sys

import numpy as np
import pytest

from training.legacy_audit import AuditError, inspect_npz, load_asset_config, sha256_file, verify_manifest_asset


@pytest.fixture
def asset_config():
    return load_asset_config(Path("configs/legacy_assets.json"))


def run_inspect_cli(config_path: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "training.inspect_legacy", "--config", str(config_path), "--output-root", str(output_root)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )


def test_package_root_is_rejected_without_any_asset_audit_or_write(asset_config, monkeypatch):
    from training import inspect_legacy

    def forbid_asset_audit(*args, **kwargs):
        pytest.fail("Package output root reached asset audit instead of being rejected")

    monkeypatch.setattr(inspect_legacy, "verify_manifest_asset", forbid_asset_audit)
    with pytest.raises(AuditError, match="package root"):
        inspect_legacy.generate(asset_config.config_path, asset_config.package_root)


def test_package_descendant_outside_legacy_assets_is_rejected(asset_config, tmp_path, monkeypatch):
    from training import inspect_legacy

    package = tmp_path / "package"
    package.mkdir()
    config = replace(asset_config, package_root=package, legacy_root=package / "assets/legacy_battery")
    monkeypatch.setattr(inspect_legacy, "load_asset_config", lambda path: config)
    with pytest.raises(AuditError, match="package root"):
        inspect_legacy.generate(config.config_path, package / "new-evidence")
    assert list(package.iterdir()) == []


def test_output_destination_inside_package_is_rejected(tmp_path):
    from training.inspect_legacy import validate_output_destinations

    package = tmp_path / "docs"
    package.mkdir()
    with pytest.raises(AuditError):
        validate_output_destinations(tmp_path, package)


def test_output_sibling_with_package_name_prefix_is_allowed(tmp_path):
    from training.inspect_legacy import validate_output_destinations

    validate_output_destinations(tmp_path / "package-output", tmp_path / "package")


def test_inspect_cli_writes_only_inside_requested_output(asset_config, tmp_path):
    from training.inspect_legacy import OUTPUT_PATHS

    before = sha256_file(asset_config.source_npz)
    result = run_inspect_cli(asset_config.config_path, tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docs/asset_audit.md").is_file()
    assert (tmp_path / "data/manifests/assets_audit.json").is_file()
    assert (tmp_path / "docs/evidence/A1/health_success.json").is_file()
    smoke = tmp_path / "docs/evidence/A1/smoke.log"
    assert smoke.is_file()
    assert smoke.read_text(encoding="utf-8") == result.stdout
    assert "7 manifest-verified assets" in result.stdout
    assert "native RUL unavailable" in result.stdout
    first_outputs = {path: (tmp_path / path).read_bytes() for path in OUTPUT_PATHS}
    rerun = run_inspect_cli(asset_config.config_path, tmp_path)
    assert rerun.returncode == 0, rerun.stderr
    assert rerun.stdout == result.stdout
    assert {path: (tmp_path / path).read_bytes() for path in OUTPUT_PATHS} == first_outputs
    assert sha256_file(asset_config.source_npz) == before


def test_inspect_cli_rejects_existing_child_link_before_any_write(asset_config, tmp_path):
    output_root = tmp_path / "output"
    output_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = output_root / "docs"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        junction = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert junction.returncode == 0, junction.stderr

    result = run_inspect_cli(asset_config.config_path, output_root)
    assert result.returncode != 0
    assert "outside the output root" in result.stderr
    assert not (outside / "evidence/A1/health_success.json").exists()
    assert not (outside / "evidence/A1/smoke.log").exists()
    assert list(outside.iterdir()) == []
    assert not (output_root / "data/manifests/legacy.csv").exists()


def test_asset_config_resolves_to_read_only_sibling_package():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    assert config.legacy_root.name == "legacy_battery"
    assert config.source_npz.name == "battery_source_windows.npz"
    assert config.source_npz.is_file()


def test_source_npz_has_frozen_shape_and_units():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    audit = inspect_npz(config.source_npz)
    assert audit.shape == (585, 15, 11)
    assert audit.window_size == 15
    assert audit.stride == 3
    assert audit.step_unit == "cycle"
    assert audit.rul_unit == "cycles"
    assert audit.finite_x is True
    assert audit.run_count == 20
    assert audit.feature_names == (
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


def test_target_npz_has_frozen_shape_and_units():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    audit = inspect_npz(config.target_npz)
    assert audit.shape == (79710, 15, 11)
    assert audit.step_unit == "orbit"
    assert audit.rul_unit == "orbits"
    assert audit.run_count == 100


def test_source_npz_matches_package_manifest():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    check = verify_manifest_asset(config.source_npz, config.package_root)
    assert check.sha256_matches
    assert check.size_matches


@pytest.mark.parametrize("damage", ["truncated", "empty", "invalid_format"])
def test_corrupt_npz_is_audit_error(tmp_path, damage):
    broken = tmp_path / "corrupt.npz"
    np.savez(broken, X=np.zeros((1, 15, 11)))
    contents = broken.read_bytes()
    broken.write_bytes({"truncated": contents[:-30], "empty": b"", "invalid_format": b"not an NPZ archive"}[damage])
    with pytest.raises(AuditError, match="Could not audit NPZ file"):
        inspect_npz(broken)


def test_all_configured_assets_match_package_manifest():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    assets = (
        config.source_npz,
        config.target_npz,
        config.source_csv,
        config.fixed_source_csv,
        *config.checkpoints.values(),
    )
    for asset in assets:
        check = verify_manifest_asset(asset, config.package_root)
        assert check.sha256_matches, asset
        assert check.size_matches, asset


@pytest.mark.parametrize(
    "manifest",
    [
        "PackagePath,SourcePath,SHA256,Bytes,Purpose\n",
        "PackagePath,SourcePath,SHA256,Bytes,Purpose\nasset.npz,,A,1,test\nasset.npz,,A,1,test\n",
    ],
)
def test_manifest_requires_one_matching_package_row(tmp_path, manifest):
    (tmp_path / "SOURCE_MANIFEST.csv").write_text(manifest, encoding="utf-8")
    asset = tmp_path / "asset.npz"
    asset.write_bytes(b"data")
    with pytest.raises(AuditError):
        verify_manifest_asset(asset, tmp_path)


def test_source_npz_labels_match_fixed_csv_exactly(asset_config):
    from training.legacy_audit import compare_label_lineage

    check = compare_label_lineage(asset_config.source_npz, asset_config.fixed_source_csv)
    assert check.comparable == 585
    assert check.exact_matches == 585
    assert check.missing == 0
    assert check.max_abs_difference == 0.0


def test_source_npz_does_not_match_original_csv(asset_config):
    from training.legacy_audit import compare_label_lineage

    check = compare_label_lineage(asset_config.source_npz, asset_config.source_csv)
    assert check.exact_matches < check.comparable
    assert check.missing > 0


def test_label_lineage_rejects_npz_arrays_with_unequal_lengths(tmp_path):
    from training.legacy_audit import compare_label_lineage

    npz_path = tmp_path / "malformed.npz"
    np.savez(
        npz_path,
        run_id=np.array(["R1", "R2"]),
        time_index=np.array([0]),
        y=np.array([7.0, 8.0]),
        window_size=np.array(1),
    )
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text("run_id,time_index,rul_cycles\nR1,0,7\n", encoding="utf-8")

    with pytest.raises(AuditError, match="same number of entries"):
        compare_label_lineage(npz_path, csv_path)


def test_legacy_start_index_becomes_last_observed_index():
    from training.legacy_audit import window_available_index

    assert window_available_index(start_index=0, window_size=15) == 14
    assert window_available_index(start_index=6, window_size=15) == 20


@pytest.mark.parametrize(
    ("start_index", "window_size"),
    [(-1, 15), (0, 0), (0, -1)],
)
def test_window_available_index_rejects_invalid_arguments(start_index, window_size):
    from training.legacy_audit import window_available_index

    with pytest.raises(ValueError):
        window_available_index(start_index=start_index, window_size=window_size)
