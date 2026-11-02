# A-N1 Formal HealthEstimate Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the frozen two-argument `estimate_health` entry point, return the H00 `HealthEstimate`, and deliver reproducible H01 success/missing-RUL/error evidence without changing the public contract or legacy assets.

**Architecture:** Keep the accepted deterministic `estimate_health_core` unchanged and place a thin public adapter around it. The adapter resolves the fixed configuration from the repository, maps the immutable internal result into `backend.contracts.HealthEstimate`, and exposes a JSON CLI; formal evidence is generated only after the implementation commit is fixed.

**Tech Stack:** Python 3.12, Pydantic 2.12.3, pytest 8.3.5, standard-library `argparse`/`json`/`hashlib`, PowerShell, Git.

## Global Constraints

- Work on A-owned code and documents only; do not edit `backend/contracts.py`, `configs/schema.json`, B/C branches, or any file under `交付包/`.
- The public signature is exactly `estimate_health(history: list[dict], now_s: float) -> HealthEstimate`; no public config argument.
- Resolve `configs/health_observation.json` relative to the module, never relative to the current working directory.
- Preserve the existing core calculation, time filtering, reason codes, strict synthetic-only input, and `config_sha256` semantics.
- Never map legacy `raw_fraction` to SOC, capacity, energy, or RUL; never convert cycle/orbit indices to seconds.
- RUL remains `None` with `RUL_UNAVAILABLE`; a missing value is never replaced with zero.
- New behavior follows RED → verify RED → GREEN → verify GREEN.
- Use a fresh workspace-local `--basetemp` directory for every pytest command.
- Use `runs/a_n1_formal_env/venv`; the existing `.venv` launcher points to a removed Python installation and is not valid evidence.
- H01 artifacts are synthetic contract evidence, not real satellite measurements or new performance results.
- Keep the unpushed R3 receipt out of implementation claims; this task neither repairs nor accepts B-R3.

## File Map

- Modify `backend/health/estimator.py`: fixed config path, formal adapter, contract-error wrapping, CLI.
- Create `scripts/generate_h01_evidence.py`: execute the real CLI/tests and write hash-linked H01 evidence.
- Create `tests/test_health_contract_adapter.py`: public adapter and CLI behavior.
- Create `tests/test_h01_evidence.py`: evidence schema, provenance, and hash verification.
- Create `docs/evidence/A/H01_2026-10-29/inputs/health_history_success.json`: reproducible valid input.
- Create `docs/evidence/A/H01_2026-10-29/inputs/health_history_invalid.json`: reproducible rejected input.
- Create `docs/evidence/A/H01_2026-10-29/health_success.json`: actual CLI `HealthEstimate` output.
- Create `docs/evidence/A/H01_2026-10-29/health_missing_rul.json`: missing-RUL audit view referencing the success artifact.
- Create `docs/evidence/A/H01_2026-10-29/health_invalid.json`: actual CLI rejection output.
- Create `docs/evidence/A/H01_2026-10-29/smoke.log`: commands, versions, exit codes, and test summary.
- Create `docs/evidence/A/H01_2026-10-29/manifest.json`: source/config/input/artifact hashes and synthetic labels.
- Modify `docs/health_contract.md`: formal adapter availability and retained legacy boundary.
- Modify `docs/handoffs/H01_health_estimate.md`: ready-for-review H01 handoff and B acceptance commands.

---

### Task 1: Integrate the Frozen H00 Baseline

**Files:**
- Merge only; no manual public-contract edits.

**Interfaces:**
- Consumes: `origin/main@75f1c52`, including `backend.contracts.HealthEstimate`.
- Produces: A branch containing H00 plus the existing A-N1 internal core.

- [ ] **Step 1: Verify the A workspace and refresh remote references**

Run:

```powershell
Set-Location D:\pro2
git status --short --branch
git fetch --prune origin
git rev-parse origin/main
```

Expected: the branch is `feature/ai`; there are no unstaged files; `origin/main` is exactly
`75f1c52b558f5b1e9545d5659bb3a2c3588b109e` and contains the H00 freeze record. If main has advanced,
inspect the new commits before changing this pinned baseline.

- [ ] **Step 2: Create a clean locked Python environment**

Run:

```powershell
C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  -m venv runs\a_n1_formal_env\venv
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pip install `
  --disable-pip-version-check --only-binary=:all: -r requirements.lock.txt
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pip check
```

Expected: Python 3.12.x environment creation succeeds and `pip check` reports `No broken requirements found.` The ignored, broken `.venv` is left untouched.

- [ ] **Step 3: Merge the approved main baseline**

Run:

```powershell
git merge --no-edit 75f1c52b558f5b1e9545d5659bb3a2c3588b109e
```

Expected: a clean merge commit. A preflight `git merge-tree` found no textual conflict; stop instead of guessing if the remote changed and a conflict now appears.

- [ ] **Step 4: Prove the public contract is byte-identical to main**

Run:

```powershell
git diff --exit-code origin/main -- backend/contracts.py configs/schema.json
```

Expected: no output and exit code 0.

- [ ] **Step 5: Verify H00 and the existing A-N1 core before modification**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest `
  tests\test_contracts.py tests\test_h00_review_regressions.py `
  tests\test_health_estimator.py -q --noconftest -p no:cacheprovider `
  --basetemp runs\a_n1_formal_01\pytest
```

Expected: all selected tests pass; any failure is a baseline blocker and must be diagnosed before Task 2.

---

### Task 2: Formal Two-Argument Health Adapter

**Files:**
- Modify: `backend/health/estimator.py`
- Create: `tests/test_health_contract_adapter.py`

**Interfaces:**
- Consumes: `estimate_health_core(history, now_s, config) -> HealthCoreEstimate` and `backend.contracts.HealthEstimate`.
- Produces: `estimate_health(history: list[dict], now_s: float) -> HealthEstimate` and private `_estimate_health_with_config(...)`.

- [ ] **Step 1: Write the failing public-adapter tests**

Create `tests/test_health_contract_adapter.py` with:

```python
from dataclasses import replace
from pathlib import Path

import pytest

import backend.health.estimator as estimator
from backend.contracts import HealthEstimate
from backend.health.legacy_adapter import HealthInputError


def synthetic_observation(**changes):
    payload = {
        "source": "synthetic",
        "soc_observed": 0.60,
        "capacity_Wh_observed": 12.0,
        "observed_at_s": 8.0,
        "available_at_s": 10.0,
    }
    payload.update(changes)
    return payload


def test_formal_entry_returns_frozen_health_estimate():
    result = estimator.estimate_health([synthetic_observation()], 10.0)

    assert isinstance(result, HealthEstimate)
    assert result.model_dump() == {
        "soc_est": 0.60,
        "soc_lower": pytest.approx(0.55),
        "capacity_Wh_est": 12.0,
        "capacity_lower_Wh": 11.0,
        "energy_lower_Wh": pytest.approx(6.05),
        "rul_est": None,
        "rul_unit": None,
        "uncertainty_method": "synthetic_absolute_margin",
        "model_version": "synthetic-health-v1",
        "observed_at_s": 8.0,
        "available_at_s": 10.0,
        "reason_codes": [
            "SYNTHETIC_HEALTH_OBSERVATION",
            "SCENARIO_CONSERVATIVE_BOUND",
            "RUL_UNAVAILABLE",
        ],
    }


def test_formal_entry_resolves_config_outside_repository_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = estimator.estimate_health([synthetic_observation()], 10.0)
    assert result.model_version == "synthetic-health-v1"


def test_formal_entry_is_deterministic():
    history = [synthetic_observation()]
    assert estimator.estimate_health(history, 10.0) == estimator.estimate_health(history, 10.0)


@pytest.mark.parametrize(
    ("history", "now_s", "code"),
    [
        ([], 10.0, "NO_AVAILABLE_OBSERVATION"),
        ([synthetic_observation(observed_at_s=20.0, available_at_s=21.0)], 10.0,
         "NO_AVAILABLE_OBSERVATION"),
        ([synthetic_observation(source="simulation_truth")], 10.0, "OBSERVATION_INVALID"),
        ([synthetic_observation(soc_observed=float("nan"))], 10.0, "OBSERVATION_INVALID"),
        ([synthetic_observation(), synthetic_observation(soc_observed=0.7)], 10.0,
         "AMBIGUOUS_OBSERVATION"),
    ],
)
def test_formal_entry_preserves_controlled_input_errors(history, now_s, code):
    with pytest.raises(HealthInputError) as error:
        estimator.estimate_health(history, now_s)
    assert error.value.code == code


def test_contract_mismatch_is_wrapped_as_controlled_health_error(monkeypatch):
    config = estimator.load_health_observation_config(
        Path(estimator.__file__).resolve().parents[2] / "configs" / "health_observation.json"
    )
    valid = estimator.estimate_health_core([synthetic_observation()], 10.0, config)
    invalid = replace(valid, energy_lower_Wh=999.0)
    monkeypatch.setattr(estimator, "estimate_health_core", lambda *args, **kwargs: invalid)

    with pytest.raises(HealthInputError) as error:
        estimator._estimate_health_with_config([synthetic_observation()], 10.0, config)

    assert error.value.code == "HEALTH_CONTRACT_INVALID"
```

- [ ] **Step 2: Run the adapter tests and verify RED**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest tests\test_health_contract_adapter.py -q `
  --noconftest -p no:cacheprovider --basetemp runs\a_n1_formal_02\pytest
```

Expected: collection or calls fail because `estimate_health` and `_estimate_health_with_config` do not exist. This is the intended RED.

- [ ] **Step 3: Add the minimal formal adapter**

In `backend/health/estimator.py`, add these imports:

```python
from pydantic import ValidationError

from backend.contracts import HealthEstimate
```

Add the fixed path after the config field declaration:

```python
_HEALTH_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "health_observation.json"
```

Add these functions after `estimate_health_core`:

```python
def _estimate_health_with_config(
    history: list[dict],
    now_s: float,
    config: HealthObservationConfig,
) -> HealthEstimate:
    core = estimate_health_core(history, now_s, config)
    try:
        return HealthEstimate(
            soc_est=core.soc_est,
            soc_lower=core.soc_lower,
            capacity_Wh_est=core.capacity_Wh_est,
            capacity_lower_Wh=core.capacity_lower_Wh,
            energy_lower_Wh=core.energy_lower_Wh,
            rul_est=core.rul_est,
            rul_unit=core.rul_unit,
            uncertainty_method=core.uncertainty_method,
            model_version=core.model_version,
            observed_at_s=core.observed_at_s,
            available_at_s=core.available_at_s,
            reason_codes=list(core.reason_codes),
        )
    except ValidationError as exc:
        raise HealthInputError(
            "HEALTH_CONTRACT_INVALID",
            "Internal health estimate does not satisfy frozen HealthEstimate",
        ) from exc


def estimate_health(history: list[dict], now_s: float) -> HealthEstimate:
    config = load_health_observation_config(_HEALTH_CONFIG_PATH)
    return _estimate_health_with_config(history, now_s, config)
```

- [ ] **Step 4: Run the adapter tests and verify GREEN**

Run the Step 2 command with `--basetemp runs\a_n1_formal_03\pytest`.

Expected: every test in `test_health_contract_adapter.py` passes.

- [ ] **Step 5: Run the existing core and H00 regression tests**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest `
  tests\test_health_estimator.py tests\test_contracts.py `
  tests\test_h00_review_regressions.py -q --noconftest -p no:cacheprovider `
  --basetemp runs\a_n1_formal_04\pytest
```

Expected: all selected tests pass and the public schema remains unchanged.

- [ ] **Step 6: Commit the adapter**

```powershell
git add backend\health\estimator.py tests\test_health_contract_adapter.py
git commit -m "feat(health): adapt core to frozen HealthEstimate"
```

---

### Task 3: Reproducible JSON Command Line

**Files:**
- Modify: `backend/health/estimator.py`
- Modify: `tests/test_health_contract_adapter.py`

**Interfaces:**
- Consumes: `estimate_health(history, now_s) -> HealthEstimate`.
- Produces: `main(argv: list[str] | None = None) -> int` and `python -m backend.health.estimator --history PATH --now-s SECONDS`.

- [ ] **Step 1: Write failing CLI tests**

Append to `tests/test_health_contract_adapter.py`:

```python
import json
import subprocess
import sys


def run_cli(history_path: Path, now_s: str):
    root = Path(estimator.__file__).resolve().parents[2]
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.health.estimator",
            "--history",
            str(history_path),
            "--now-s",
            now_s,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_prints_only_formal_health_json_on_success(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([synthetic_observation()]), encoding="utf-8")

    process = run_cli(path, "10")

    assert process.returncode == 0
    assert process.stderr == ""
    HealthEstimate.model_validate_json(process.stdout)


def test_cli_rejects_invalid_observation_with_json_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps([synthetic_observation(source="simulation_truth")]),
        encoding="utf-8",
    )

    process = run_cli(path, "10")

    assert process.returncode == 2
    assert process.stdout == ""
    error = json.loads(process.stderr)
    assert error["status"] == "rejected"
    assert error["error_code"] == "OBSERVATION_INVALID"


def test_cli_rejects_unreadable_history_as_controlled_json(tmp_path):
    process = run_cli(tmp_path / "missing.json", "10")
    assert process.returncode == 2
    assert json.loads(process.stderr)["error_code"] == "HISTORY_FILE_INVALID"
```

- [ ] **Step 2: Run the CLI tests and verify RED**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest `
  tests\test_health_contract_adapter.py -q --noconftest -p no:cacheprovider `
  --basetemp runs\a_n1_formal_05\pytest
```

Expected: the earlier adapter tests pass and the three CLI tests fail because the module has no command-line implementation.

- [ ] **Step 3: Implement the minimal controlled CLI**

Add imports to `backend/health/estimator.py`:

```python
import argparse
import sys
```

Append:

```python
def _load_history_file(path: Path) -> list[dict]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HealthInputError(
            "HISTORY_FILE_INVALID", "Could not read history JSON"
        ) from exc
    if not isinstance(payload, list):
        raise HealthInputError("HISTORY_INVALID", "history JSON must contain a list")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one formal HealthEstimate")
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--now-s", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        result = estimate_health(_load_history_file(args.history), args.now_s)
    except HealthInputError as error:
        payload = {
            "status": "rejected",
            "error_code": error.code,
            "message": str(error),
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the CLI tests and verify GREEN**

Run the Step 2 command with `--basetemp runs\a_n1_formal_06\pytest`.

Expected: all adapter and CLI tests pass; successful stderr and rejected stdout are empty.

- [ ] **Step 5: Commit the CLI**

```powershell
git add backend\health\estimator.py tests\test_health_contract_adapter.py
git commit -m "feat(health): expose reproducible estimate command"
```

Record the resulting commit as `source_revision`; formal evidence must point to this implementation commit, not its later evidence commit.

---

### Task 4: Formal H01 Evidence and Provenance

**Files:**
- Create: `tests/test_h01_evidence.py`
- Create: `scripts/generate_h01_evidence.py`
- Create: all files under `docs/evidence/A/H01_2026-10-29/`

**Interfaces:**
- Consumes: the Task 3 CLI and its fixed `source_revision`.
- Produces: verified success, missing-RUL, rejected-input, log, input, and manifest artifacts.

- [ ] **Step 1: Write the failing evidence verifier**

Create `tests/test_h01_evidence.py` with:

```python
import hashlib
import json
from pathlib import Path

from backend.contracts import HealthEstimate


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "A" / "H01_2026-10-29"


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
        + "\n"
    ).encode("utf-8")


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_h01_artifacts_and_hashes_are_self_consistent():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["kind"] == "H01_formal_health_estimate_evidence"
    assert manifest["source"] == "synthetic"
    assert manifest["is_real_satellite_measurement"] is False
    assert len(manifest["source_revision"]) == 40
    for relative, expected in manifest["artifact_sha256"].items():
        assert sha256(EVIDENCE / relative) == expected


def test_success_is_frozen_contract_and_missing_rul_view_references_it():
    success_path = EVIDENCE / "health_success.json"
    success = HealthEstimate.model_validate_json(success_path.read_text(encoding="utf-8"))
    missing = json.loads((EVIDENCE / "health_missing_rul.json").read_text(encoding="utf-8"))
    assert success.rul_est is None and success.rul_unit is None
    assert "RUL_UNAVAILABLE" in success.reason_codes
    assert missing["status"] == "accepted_with_missing_rul"
    assert missing["source_artifact"] == "health_success.json"
    assert missing["source_artifact_sha256"] == sha256(success_path)
    assert missing["rul_est"] is None and missing["rul_unit"] is None


def test_invalid_example_is_a_controlled_rejection():
    invalid = json.loads((EVIDENCE / "health_invalid.json").read_text(encoding="utf-8"))
    assert invalid["status"] == "rejected"
    assert invalid["error_code"] == "OBSERVATION_INVALID"
    assert invalid["exit_code"] == 2


def test_manifest_hashes_config_and_canonical_call_input():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    history = json.loads(
        (EVIDENCE / "inputs" / "health_history_success.json").read_text(encoding="utf-8")
    )
    config = ROOT / "configs" / "health_observation.json"
    call = {"history": history, "now_s": manifest["now_s"]}
    assert manifest["config_sha256"] == sha256(config)
    assert manifest["history_input_sha256"] == hashlib.sha256(json_bytes(history)).hexdigest()
    assert manifest["call_input_sha256"] == hashlib.sha256(json_bytes(call)).hexdigest()
```

- [ ] **Step 2: Run the evidence verifier and verify RED**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest tests\test_h01_evidence.py -q `
  --noconftest -p no:cacheprovider --basetemp runs\a_n1_formal_07\pytest
```

Expected: tests fail with missing `docs/evidence/A/H01_2026-10-29` artifacts.

- [ ] **Step 3: Create the two exact input fixtures**

Create `inputs/health_history_success.json` as:

```json
[
  {
    "source": "synthetic",
    "soc_observed": 0.6,
    "capacity_Wh_observed": 12.0,
    "observed_at_s": 8.0,
    "available_at_s": 10.0
  }
]
```

Create `inputs/health_history_invalid.json` as:

```json
[
  {
    "source": "simulation_truth",
    "soc_observed": 0.6,
    "capacity_Wh_observed": 12.0,
    "observed_at_s": 8.0,
    "available_at_s": 10.0
  }
]
```

- [ ] **Step 4: Write the deterministic evidence generator**

Create `scripts/generate_h01_evidence.py` with:

```python
"""Generate H01 evidence from the committed formal health adapter."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.contracts import HealthEstimate


EVIDENCE = ROOT / "docs" / "evidence" / "A" / "H01_2026-10-29"


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value):
    path.write_bytes(json_bytes(value))


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, check=False)


def command_text(command):
    return subprocess.list2cmdline([str(part) for part in command])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    if len(args.source_revision) != 40 or any(
        character not in "0123456789abcdef" for character in args.source_revision
    ):
        raise SystemExit("source revision must be a lowercase 40-character Git SHA")

    success_input = EVIDENCE / "inputs" / "health_history_success.json"
    invalid_input = EVIDENCE / "inputs" / "health_history_invalid.json"
    success_command = [
        sys.executable, "-m", "backend.health.estimator", "--history",
        str(success_input), "--now-s", "10",
    ]
    invalid_command = [
        sys.executable, "-m", "backend.health.estimator", "--history",
        str(invalid_input), "--now-s", "10",
    ]
    success = run(success_command)
    invalid = run(invalid_command)
    if success.returncode != 0 or success.stderr:
        raise SystemExit("formal success CLI did not produce a clean success")
    if invalid.returncode != 2 or invalid.stdout:
        raise SystemExit("formal invalid CLI did not produce a controlled rejection")

    success_path = EVIDENCE / "health_success.json"
    success_path.write_bytes(success.stdout)
    success_model = HealthEstimate.model_validate_json(success.stdout)
    invalid_payload = json.loads(invalid.stderr)
    invalid_payload["exit_code"] = invalid.returncode
    write_json(EVIDENCE / "health_invalid.json", invalid_payload)
    write_json(
        EVIDENCE / "health_missing_rul.json",
        {
            "kind": "H01_missing_rul_audit",
            "status": "accepted_with_missing_rul",
            "source_artifact": "health_success.json",
            "source_artifact_sha256": sha256(success_path),
            "rul_est": success_model.rul_est,
            "rul_unit": success_model.rul_unit,
            "reason_codes": success_model.reason_codes,
            "note": "Audit view of the same successful estimate; not a second experiment",
        },
    )

    pip_command = [sys.executable, "-m", "pip", "check"]
    pip_result = run(pip_command)
    basetemp = ROOT / "runs" / ("h01_evidence_pytest_" + uuid4().hex)
    test_command = [
        sys.executable, "-m", "pytest",
        "tests/test_health_contract_adapter.py",
        "tests/test_health_estimator.py",
        "tests/test_contracts.py",
        "tests/test_h00_review_regressions.py",
        "-q", "--noconftest", "-p", "no:cacheprovider",
        "--basetemp", str(basetemp),
    ]
    test_result = run(test_command)
    if pip_result.returncode != 0 or test_result.returncode != 0:
        raise SystemExit("dependency or selected test verification failed")
    smoke = "\n".join(
        [
            "H01 formal adapter smoke",
            "python=" + sys.version.replace("\n", " "),
            "pip_command=" + command_text(pip_command),
            "pip_exit=" + str(pip_result.returncode),
            pip_result.stdout.decode("utf-8", errors="replace").strip(),
            "success_command=" + command_text(success_command),
            "success_exit=" + str(success.returncode),
            "invalid_command=" + command_text(invalid_command),
            "invalid_exit=" + str(invalid.returncode),
            "test_command=" + command_text(test_command),
            "test_exit=" + str(test_result.returncode),
            test_result.stdout.decode("utf-8", errors="replace").strip(),
        ]
    ) + "\n"
    (EVIDENCE / "smoke.log").write_bytes(smoke.encode("utf-8"))

    history = json.loads(success_input.read_text(encoding="utf-8"))
    call = {"history": history, "now_s": 10.0}
    artifact_names = [
        "inputs/health_history_success.json",
        "inputs/health_history_invalid.json",
        "health_success.json",
        "health_missing_rul.json",
        "health_invalid.json",
        "smoke.log",
    ]
    config = ROOT / "configs" / "health_observation.json"
    write_json(
        EVIDENCE / "manifest.json",
        {
            "schema_version": "1.0",
            "kind": "H01_formal_health_estimate_evidence",
            "source": "synthetic",
            "is_real_satellite_measurement": False,
            "is_new_model_training_result": False,
            "source_revision": args.source_revision,
            "config_path": "configs/health_observation.json",
            "config_sha256": sha256(config),
            "history_input_sha256": hashlib.sha256(json_bytes(history)).hexdigest(),
            "call_input_sha256": hashlib.sha256(json_bytes(call)).hexdigest(),
            "now_s": 10.0,
            "artifact_sha256": {
                name: sha256(EVIDENCE / name) for name in artifact_names
            },
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Generate evidence from the fixed implementation commit**

Run:

```powershell
$sourceRevision = git rev-parse HEAD
.\runs\a_n1_formal_env\venv\Scripts\python.exe scripts\generate_h01_evidence.py `
  --source-revision $sourceRevision
```

Expected: exit code 0; the success CLI exits 0, invalid CLI exits 2, `pip check` passes, selected tests pass, and all six artifact hashes are written from actual bytes.

- [ ] **Step 6: Run the evidence verifier and verify GREEN**

Run the Step 2 command with `--basetemp runs\a_n1_formal_08\pytest`.

Expected: all four evidence tests pass.

- [ ] **Step 7: Scan for placeholders and commit evidence**

Run:

```powershell
rg -n "TBD|TODO|PLACEHOLDER" docs\evidence\A\H01_2026-10-29
git diff --check
```

Expected: no placeholder matches and no whitespace errors.

Commit:

```powershell
git add scripts\generate_h01_evidence.py tests\test_h01_evidence.py `
  docs\evidence\A\H01_2026-10-29
git commit -m "test(health): record formal H01 evidence"
```

---

### Task 5: Formal H01 Documentation and Handoff

**Files:**
- Modify: `docs/health_contract.md`
- Modify: `docs/handoffs/H01_health_estimate.md`

**Interfaces:**
- Consumes: verified Task 4 evidence and its `source_revision`.
- Produces: B-readable formal handoff with exact commands and limitations.

- [ ] **Step 1: Update the health contract boundary**

In `docs/health_contract.md`, preserve the legacy checkpoint sections and add a formal adapter section containing:

```markdown
## Formal synthetic HealthEstimate adapter

`backend.health.estimator.estimate_health(history, now_s)` returns the frozen
`backend.contracts.HealthEstimate`. It accepts only explicit synthetic SOC/capacity
observations in seconds, loads `configs/health_observation.json` relative to the
module, and preserves unavailable RUL as `null` plus `RUL_UNAVAILABLE`.

The adapter does not consume the legacy checkpoint `raw_fraction`. The legacy A1
evidence remains checkpoint-behavior evidence and is not a formal HealthEstimate.
```

- [ ] **Step 2: Replace the internal-draft H01 status with ready-for-review**

Update `docs/handoffs/H01_health_estimate.md` to include all of the following exact facts:

- status `ready_for_review`, not `accepted`;
- exact Task 3 `source_revision`;
- frozen signature and return type;
- config, units, time filtering, RUL-null, and synthetic-only boundaries;
- evidence directory and manifest;
- the two CLI commands from Task 4;
- B acceptance: run one success, inspect the missing-RUL view, run one rejection, validate `HealthEstimate`, and recompute hashes;
- rejection conditions: future leakage, `raw_fraction` substitution, zero-filled RUL, non-Wh energy, or a non-H00 return type;
- explicit exclusions: A-N2, A-N3, guard, simulator, API, real measurements, and performance claims.

- [ ] **Step 3: Verify the handoff has no stale draft claim**

Run:

```powershell
rg -n "internal_core_ready_for_review|尚未导入|尚未生成正式|等待H00" `
  docs\handoffs\H01_health_estimate.md docs\health_contract.md
```

Expected: no stale waiting/draft statements remain. Historical A1 limitations stay intact.

- [ ] **Step 4: Commit the formal handoff**

```powershell
git add docs\health_contract.md docs\handoffs\H01_health_estimate.md
git commit -m "docs(handoff): deliver formal H01 health estimate"
```

---

### Task 6: Final Verification and Branch Handoff

**Files:**
- Verification only.

**Interfaces:**
- Consumes: all earlier tasks.
- Produces: a clean, evidence-backed A-N1 formal delivery ready for B review.

- [ ] **Step 1: Verify locked dependencies**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe --version
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pip check
```

Expected: Python 3.12.x and `No broken requirements found.`

- [ ] **Step 2: Run all A-N1, evidence, H00, and legacy health tests**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest `
  tests\test_health_contract_adapter.py `
  tests\test_h01_evidence.py `
  tests\test_health_estimator.py `
  tests\test_contracts.py `
  tests\test_h00_review_regressions.py `
  tests\test_health.py `
  tests\test_legacy_audit.py -q --noconftest -p no:cacheprovider `
  --basetemp runs\a_n1_formal_09\pytest `
  --junitxml runs\a_n1_formal_09\results.xml
```

Expected: all selected tests pass with 0 failures and 0 errors.

- [ ] **Step 3: Run the full repository suite**

Run:

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m pytest tests -q --noconftest -p no:cacheprovider `
  --basetemp runs\a_n1_formal_10\pytest `
  --junitxml runs\a_n1_formal_10\full.xml
```

Expected: every collected test passes. Report the actual count; do not copy an older count.

- [ ] **Step 4: Prove public contracts and legacy assets were not changed**

Run:

```powershell
git diff --exit-code origin/main -- backend/contracts.py configs/schema.json
git status --short
git diff --check origin/main...HEAD
```

Expected: no public-contract diff, no unstaged changes, and no whitespace errors. Files under `交付包/` must not appear in any commit.

- [ ] **Step 5: Inspect commit and delivery scope**

Run:

```powershell
git log --oneline --decorate origin/main..HEAD
git diff --stat origin/main...HEAD
git status --short --branch
```

Expected: only A-owned core history, the formal adapter, tests, H01 evidence/docs, and A review records are present; no B-R3 implementation or C frontend code is included.

- [ ] **Step 6: Complete the development branch workflow**

Invoke `superpowers:verification-before-completion`, then `superpowers:finishing-a-development-branch`. Present the verified integration/push choices to the user; do not push, merge, or open a PR without their choice.
