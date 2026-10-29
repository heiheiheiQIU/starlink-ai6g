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
