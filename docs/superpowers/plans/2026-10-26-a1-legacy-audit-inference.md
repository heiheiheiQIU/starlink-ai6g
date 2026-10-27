# A1 Legacy Asset Audit and Minimal Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, reproducible audit and strict two-window inference path for the packaged legacy battery assets without claiming that legacy RUL is already a valid online health signal.

**Architecture:** The new repository references the sibling v3 research package through explicit configuration and never writes into it. A small audit library verifies hashes, NPZ structure, CSV label lineage, checkpoint keys, and legacy time semantics; a separate PyTorch inference module strictly loads the matching LSTM or BiLSTM-Attention state dictionary and returns an internal `LegacyPrediction`. The public B-owned `HealthEstimate` wrapper is excluded until H00 supplies `backend/contracts.py`.

**Tech Stack:** Python 3.12, NumPy 2.1.3, PyTorch 2.5.1 CPU, pytest 8.3.5, standard-library CSV/JSON/hashlib.

## Global Constraints

- New work is written only under `D:\ict\星地智调`.
- `D:\ict\星地智调_团队研发包_2026-10-26_v3` is read-only evidence; tests must verify it is unchanged by SHA.
- Never call legacy `run_pipeline.py --mode full` or `preprocess_windows.py`.
- Never use `strict=False` when loading checkpoints.
- The delivered source and target NPZ inputs have shape `(N, 15, 11)` and feature order recorded in the NPZ.
- Legacy source steps are `cycle`; target steps are `orbit`; neither is converted to seconds.
- Legacy `time_index` is treated as a window-start index. Prediction availability is the final observed point of the 15-step window.
- Native RUL restoration that depends on a run's true maximum lifetime is excluded from online inference.
- No new communication result, accuracy improvement, or satellite validation claim is produced by this plan.
- `backend/contracts.py` remains B-owned and is not created here.

## File Structure

- `pyproject.toml`: package metadata, exact test configuration, and supported Python version.
- `requirements.lock.txt`: exact first environment versions after successful installation.
- `configs/legacy_assets.json`: sibling package-relative asset locations.
- `training/legacy_audit.py`: pure audit functions and typed audit records.
- `training/inspect_legacy.py`: CLI that writes JSON, CSV, Markdown, and smoke evidence only under the new repository.
- `backend/health/legacy_models.py`: exact local architecture definitions required for strict state-dict loading.
- `backend/health/legacy_adapter.py`: validated NPZ-window inference returning `LegacyPrediction`.
- `tests/test_legacy_audit.py`: manifest, NPZ, lineage, and time-semantics behavior.
- `tests/test_health.py`: model class selection, availability, feature, finite-value, strict-load, and batch behavior.
- `docs/asset_audit.md`: generated human-readable audit summary.
- `data/manifests/legacy.csv`: generated source, SHA, size, purpose, and status table.
- `data/manifests/assets_audit.json`: generated machine-readable audit.
- `docs/health_contract.md`: A-to-B boundary and unavailable-RUL behavior.
- `docs/evidence/A1/`: successful, unavailable, invalid, and smoke-log evidence.
- `docs/handoffs/H01_2026-10-28.md`: handoff record; acceptance remains B-owned.

---

### Task 1: Reproducible Python Test Harness and Asset Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.lock.txt`
- Create: `.gitignore`
- Create: `configs/legacy_assets.json`
- Create: `training/__init__.py`
- Create: `training/legacy_audit.py`
- Create: `backend/__init__.py`
- Create: `backend/health/__init__.py`
- Create: `tests/test_legacy_audit.py`

**Interfaces:**
- Consumes: sibling package path `../星地智调_团队研发包_2026-10-26_v3`.
- Produces: a project-local `.venv` and configuration keys `legacy_root`, `source_npz`, `target_npz`, `source_csv`, `fixed_source_csv`, and `checkpoints`.

- [ ] **Step 1: Create the exact dependency and pytest configuration**

```toml
[build-system]
requires = ["setuptools==75.8.0"]
build-backend = "setuptools.build_meta"

[project]
name = "starlink-ai6g"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["numpy==2.1.3", "torch==2.5.1"]

[project.optional-dependencies]
test = ["pytest==8.3.5"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

Create `requirements.lock.txt` with:

```text
numpy==2.1.3
pytest==8.3.5
torch==2.5.1
```

- [ ] **Step 2: Create the asset configuration**

```json
{
  "schema_version": "1.0",
  "legacy_root": "../星地智调_团队研发包_2026-10-26_v3/assets/legacy_battery",
  "source_npz": "data/processed/battery_source_windows.npz",
  "target_npz": "data/processed/battery_target_windows.npz",
  "source_csv": "data/processed/public_battery.csv",
  "fixed_source_csv": "results/p3-1/public_battery_fixed.csv",
  "checkpoints": {
    "lstm_source": "results/models/battery_lstm_source_only.pt",
    "lstm_finetune": "results/models/battery_lstm_finetune_best.pt",
    "bilstm_coral": "results/models/battery_bilstm_coral_best.pt"
  }
}
```

Expected SHA256 values are read from package `SOURCE_MANIFEST.csv`; do not duplicate them in this JSON.

- [ ] **Step 3: Create and install the isolated environment**

Create `.gitignore` with:

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
```

Run:

```powershell
& 'C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install --disable-pip-version-check -r requirements.lock.txt
```

Expected: installation exits 0 and `python -c "import numpy, torch, pytest"` exits 0. If PyTorch 2.5.1 has no compatible wheel, stop and report the resolver output rather than changing the pin silently.

- [ ] **Step 4: Write the first failing configuration test**

```python
from pathlib import Path
from training.legacy_audit import load_asset_config


def test_asset_config_resolves_to_read_only_sibling_package():
    config = load_asset_config(Path("configs/legacy_assets.json"))
    assert config.legacy_root.name == "legacy_battery"
    assert config.source_npz.name == "battery_source_windows.npz"
    assert config.source_npz.is_file()
```

- [ ] **Step 5: Run the test and verify RED**

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_legacy_audit.py::test_asset_config_resolves_to_read_only_sibling_package -v
```

Expected: `ModuleNotFoundError: No module named 'training.legacy_audit'`.

- [ ] **Step 6: Implement only configuration loading needed by the test**

Create `AssetConfig` in `training/legacy_audit.py` with immutable fields `config_path`, `package_root`, `legacy_root`, `source_npz`, `target_npz`, `source_csv`, `fixed_source_csv`, and `checkpoints: Mapping[str, Path]`, plus `load_asset_config(path: Path) -> AssetConfig`. Resolve `legacy_root` relative to the repository root; define `package_root = legacy_root.parents[1]`; raise `FileNotFoundError` for a missing root or configured asset.

- [ ] **Step 7: Run the test and verify GREEN**

Run the same targeted pytest command. Expected: `1 passed`.

- [ ] **Step 8: Commit**

```powershell
git add .gitignore pyproject.toml requirements.lock.txt configs training/__init__.py training/legacy_audit.py backend/__init__.py backend/health/__init__.py tests/test_legacy_audit.py
git commit -m "build: add isolated A1 audit environment"
```

---

### Task 2: Hash, NPZ Structure, and Split Audit

**Files:**
- Modify: `training/legacy_audit.py`
- Modify: `tests/test_legacy_audit.py`

**Interfaces:**
- Consumes: `AssetConfig` and package `SOURCE_MANIFEST.csv`.
- Produces: `sha256_file(path: Path) -> str`, `inspect_npz(path: Path) -> NpzAudit`, and `verify_manifest_asset(path: Path, package_root: Path) -> ManifestCheck`.

- [ ] **Step 1: Add failing tests for real NPZ structure and manifest verification**

```python
def test_source_npz_has_frozen_shape_and_units(asset_config):
    audit = inspect_npz(asset_config.source_npz)
    assert audit.shape == (585, 15, 11)
    assert audit.window_size == 15
    assert audit.stride == 3
    assert audit.step_unit == "cycle"
    assert audit.rul_unit == "cycles"
    assert audit.finite_x is True
    assert audit.run_count == 20


def test_target_npz_has_frozen_shape_and_units(asset_config):
    audit = inspect_npz(asset_config.target_npz)
    assert audit.shape == (79710, 15, 11)
    assert audit.step_unit == "orbit"
    assert audit.rul_unit == "orbits"
    assert audit.run_count == 100


def test_source_npz_matches_package_manifest(asset_config):
    check = verify_manifest_asset(asset_config.source_npz, asset_config.package_root)
    assert check.sha256_matches
    assert check.size_matches
```

- [ ] **Step 2: Verify RED**

Run `pytest tests/test_legacy_audit.py -v`. Expected: missing-function failures.

- [ ] **Step 3: Implement immutable audit records and pure readers**

`inspect_npz` loads with `allow_pickle=False`, requires exactly these keys, asserts `X.shape[1] == window_size`, requires finite `X`, `y`, and `y_fraction`, and preserves feature order:

```python
REQUIRED_NPZ_KEYS = {
    "X", "y", "y_fraction", "run_id", "time_index", "feature_names",
    "window_size", "stride", "step_unit", "rul_unit",
}
```

`verify_manifest_asset` compares byte size and uppercase SHA256 against the unique package-relative manifest row. Missing or duplicate rows raise `AuditError`.

- [ ] **Step 4: Verify GREEN and syntax compilation**

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_legacy_audit.py -v
& '.\.venv\Scripts\python.exe' -m compileall training backend tests
```

Expected: all Task 1–2 tests pass; compileall exits 0.

- [ ] **Step 5: Commit**

```powershell
git add training/legacy_audit.py tests/test_legacy_audit.py
git commit -m "feat: audit legacy NPZ and package hashes"
```

---

### Task 3: CSV Label Lineage and Window Availability Semantics

**Files:**
- Modify: `training/legacy_audit.py`
- Modify: `tests/test_legacy_audit.py`

**Interfaces:**
- Consumes: source NPZ, original source CSV, and fixed source CSV.
- Produces: `compare_label_lineage(npz_path, csv_path) -> LabelLineageCheck` and `window_available_index(start_index: int, window_size: int) -> int`.

- [ ] **Step 1: Add failing lineage tests using the real assets**

```python
def test_source_npz_labels_match_fixed_csv_exactly(asset_config):
    check = compare_label_lineage(asset_config.source_npz, asset_config.fixed_source_csv)
    assert check.comparable == 585
    assert check.exact_matches == 585
    assert check.missing == 0
    assert check.max_abs_difference == 0.0


def test_source_npz_does_not_match_original_csv(asset_config):
    check = compare_label_lineage(asset_config.source_npz, asset_config.source_csv)
    assert check.exact_matches < check.comparable
    assert check.missing > 0


def test_legacy_start_index_becomes_last_observed_index():
    assert window_available_index(start_index=0, window_size=15) == 14
    assert window_available_index(start_index=6, window_size=15) == 20
```

- [ ] **Step 2: Verify RED**

Run the three named tests. Expected: missing-function failures.

- [ ] **Step 3: Implement CSV comparison without pandas**

Use `csv.DictReader`, group non-empty `rul_cycles` rows by `run_id`, sort by numeric `time_index`, and map every NPZ sample's legacy start index to row position `start + window_size - 1`. Return counts and absolute differences without mutating either CSV.

`window_available_index` rejects negative indices and non-positive window sizes with `ValueError`.

- [ ] **Step 4: Verify GREEN**

Run `pytest tests/test_legacy_audit.py -v`. Expected: all audit tests pass and the fixed CSV comparison is 585/585 exact.

- [ ] **Step 5: Commit**

```powershell
git add training/legacy_audit.py tests/test_legacy_audit.py
git commit -m "test: prove legacy CSV and NPZ label lineage"
```

---

### Task 4: Strict Legacy Model Loading and Two-Window Inference

**Files:**
- Create: `backend/health/legacy_models.py`
- Create: `backend/health/legacy_adapter.py`
- Create: `tests/test_health.py`

**Interfaces:**
- Consumes: standardized NPZ windows, feature order, checkpoint path, `available_at_index`, and `now_index` in the NPZ native step unit.
- Produces: `LegacyPrediction(raw_fraction: tuple[float, ...], run_ids: tuple[str, ...], start_indices: tuple[int, ...], available_indices: tuple[int, ...], step_unit: str, model_id: str, checkpoint_sha256: str)` and `predict_npz_windows(...) -> LegacyPrediction`.

- [ ] **Step 1: Write failing validation tests before production code**

At the top of `tests/test_health.py`, import `math`, `numpy as np`, `pytest`, the adapter exceptions/functions, and `sha256_file`. Define this real fixture helper so the feature-order failure is reproducible:

```python
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
```

```python
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
```

- [ ] **Step 2: Verify RED**

Run the three tests. Expected: import failure for the missing adapter.

- [ ] **Step 3: Implement minimal validation and errors**

Create `HealthInputError(code, message)` and `HealthModelError(code, message)`. Validate unique in-range sample indices, exact 11-feature tuple, finite selected samples, `start_index + window_size - 1 <= now_index`, checkpoint existence, and model kind. Do not load PyTorch until all input checks pass.

- [ ] **Step 4: Run validation tests and verify GREEN**

Expected: the three tests pass without requiring successful inference.

- [ ] **Step 5: Add failing strict-load and real-forward tests**

```python
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


def test_bilstm_checkpoint_requires_matching_architecture(asset_config):
    prediction = predict_npz_windows(
        asset_config.target_npz,
        asset_config.checkpoints["bilstm_coral"],
        "bilstm_attention", [0, 1], now_index=10_000,
    )
    assert len(prediction.raw_fraction) == 2


def test_wrong_architecture_fails_strictly(asset_config):
    with pytest.raises(HealthModelError, match="STATE_DICT_MISMATCH"):
        predict_npz_windows(
            asset_config.target_npz,
            asset_config.checkpoints["bilstm_coral"],
            "lstm", [0], now_index=10_000,
        )
```

- [ ] **Step 6: Verify RED for absent architecture/loader**

Expected: tests fail because model definitions or strict loading are absent.

- [ ] **Step 7: Implement exact classes and strict CPU inference**

`legacy_models.py` reproduces:

- `LSTMRegressor(input_dim=11, hidden_dim=64, num_layers=2, dropout=0.2)`;
- `BiLSTMAttention(input_dim=11, hidden_dim=64, num_layers=2, dropout=0.2, attention_dim=32)`.

Load with `torch.load(path, map_location="cpu", weights_only=True)`, require a mapping, call `model.load_state_dict(state, strict=True)`, then `model.eval()` under `torch.inference_mode()`. Missing/unexpected keys or size mismatches become `HealthModelError("STATE_DICT_MISMATCH", ...)`. Output must be finite and preserve batch size.

- [ ] **Step 8: Verify GREEN**

Run `pytest tests/test_health.py -v`. Expected: all validation, LSTM, BiLSTM, and wrong-architecture tests pass.

- [ ] **Step 9: Commit**

```powershell
git add backend/health/legacy_models.py backend/health/legacy_adapter.py tests/test_health.py
git commit -m "feat: add strict legacy battery inference"
```

---

### Task 5: Generated Audit, H01 Evidence, and Handoff Documentation

**Files:**
- Create: `training/inspect_legacy.py`
- Create: `docs/health_contract.md`
- Generate: `docs/asset_audit.md`
- Generate: `data/manifests/legacy.csv`
- Generate: `data/manifests/assets_audit.json`
- Generate: `docs/evidence/A1/health_success.json`
- Generate: `docs/evidence/A1/health_missing_rul.json`
- Generate: `docs/evidence/A1/health_invalid.json`
- Generate: `docs/evidence/A1/smoke.log`
- Create: `docs/handoffs/H01_2026-10-28.md`
- Modify: `tests/test_legacy_audit.py`

**Interfaces:**
- Consumes: Task 1–4 audit and inference functions.
- Produces: `python -m training.inspect_legacy --config configs/legacy_assets.json --output-root .` and the exact H01 evidence paths above.

- [ ] **Step 1: Write a failing CLI integration test**

Define the subprocess helper in `tests/test_legacy_audit.py`:

```python
def run_inspect_cli(config_path: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "training.inspect_legacy",
            "--config",
            str(config_path),
            "--output-root",
            str(output_root),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
```

```python
def test_inspect_cli_writes_only_inside_requested_output(asset_config, tmp_path):
    before = sha256_file(asset_config.source_npz)
    result = run_inspect_cli(asset_config.config_path, tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "docs/asset_audit.md").is_file()
    assert (tmp_path / "data/manifests/assets_audit.json").is_file()
    assert (tmp_path / "docs/evidence/A1/health_success.json").is_file()
    assert sha256_file(asset_config.source_npz) == before
```

- [ ] **Step 2: Verify RED**

Expected: subprocess fails because `training.inspect_legacy` does not exist.

- [ ] **Step 3: Implement the idempotent CLI**

The CLI must resolve configuration, verify manifest SHA/size, inspect both NPZ files, compare both CSV lineages, run two-window LSTM and BiLSTM inference, write sorted UTF-8 JSON, write CSV columns `asset_path,source_path,sha256,size_bytes,purpose,status`, separate confirmed/conflicting/unverified facts in Markdown, record Python/NumPy/PyTorch/CPU versions, and reject output paths inside `legacy_root`.

`health_missing_rul.json` contains `rul_est: null`, native unit, and `NATIVE_RUL_RESTORE_REQUIRES_FUTURE_RUN_MAX`. `health_invalid.json` records one controlled future-window failure. These are evidence examples, not B's final schema objects.

- [ ] **Step 4: Verify GREEN and generate repository evidence**

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_legacy_audit.py::test_inspect_cli_writes_only_inside_requested_output -v
& '.\.venv\Scripts\python.exe' -m training.inspect_legacy --config configs/legacy_assets.json --output-root . 2>&1 | Tee-Object docs/evidence/A1/smoke.log
```

Expected: integration test passes; CLI exits 0; outputs exist; source NPZ SHA remains `DE8EA216CC7F604B277EEFCAC7054CD6E439C22F413BDB18B870F59B11F55499`.

- [ ] **Step 5: Write health contract and handoff record**

`docs/health_contract.md` states normalized prediction only, `rul_est` remains null until online-safe restoration exists, step units remain cycle/orbit, start and available indices are retained, RUL never becomes SOC/capacity/energy, B may use explicit synthetic health, and formal `HealthEstimate` waits for H00.

`docs/handoffs/H01_2026-10-28.md` lists commit, schema boundary, evidence paths, commands, limitations, and three B acceptance checks.

- [ ] **Step 6: Run complete verification**

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_legacy_audit.py tests/test_health.py -q
& '.\.venv\Scripts\python.exe' -m compileall training backend tests
git diff --check
git status --short
```

Expected: zero test failures; compileall exits 0; `git diff --check` has no output. Inspect generated JSON to ensure absolute personal paths are evidence metadata, not model results.

- [ ] **Step 7: Commit**

```powershell
git add training/inspect_legacy.py docs/asset_audit.md docs/health_contract.md docs/evidence/A1 docs/handoffs/H01_2026-10-28.md data/manifests tests/test_legacy_audit.py
git commit -m "docs: deliver A1 audit and H01 evidence"
```

## Completion Gate

A1 is complete only when real LSTM and BiLSTM checkpoints perform strict CPU forward passes on two distinct standardized NPZ windows, all tests pass, legacy hashes remain unchanged, and the handoff explicitly says native online RUL is unavailable. If the pinned environment cannot install or either checkpoint fails strict loading, stop at the audit evidence and issue the documented unavailable result; do not weaken validation or change claims.
