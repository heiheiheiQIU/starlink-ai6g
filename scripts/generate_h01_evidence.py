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
