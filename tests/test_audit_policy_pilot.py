import hashlib
import json
from pathlib import Path

import pytest

import training.generate_policy_pilot as generator
import training.audit_policy_pilot as pilot_auditor
import training.audit_policy_dataset as dataset_auditor
from backend.contracts import TeacherCandidateScore, TeacherResult
from backend.policies.common import plan_candidate
from backend.policies.teacher import TeacherConfig
from training.audit_policy_pilot import audit_pilot, main, render_pilot_audit, verify_split_inheritance


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def rewrite(package, name, value):
    raw = ("".join(json.dumps(row) + "\n" for row in value) if name.endswith("jsonl")
           else json.dumps(value) + "\n").encode()
    (package / name).write_bytes(raw)
    manifest = json.loads((package / "manifest.json").read_bytes())
    manifest["output_sha256"][name] = hashlib.sha256(raw).hexdigest()
    manifest["file_row_counts"][name] = len(raw.splitlines())
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def pilot_package(tmp_path, monkeypatch):
    def fake_teacher(observation, budget_ms, *, config=None, diagnostics=None):
        diagnostics.update(teacher_version="bounded-forecast-r4-v1", candidates=[])
        return TeacherResult(candidate_scores=[
            TeacherCandidateScore(task_id=task.task_id, mode=mode,
                                 score=1.0 if mode == "robust" else 0.5,
                                 feasible=plan_candidate(observation, task, mode, TeacherConfig.model_validate(config).policy).feasible)
            for task in observation.tasks for mode in ("robust", "fast")
        ] + [TeacherCandidateScore(task_id=None, mode="idle", score=0.0, feasible=True)],
            solver_status="OPTIMAL", gap=0.0, elapsed_ms=1.0)
    monkeypatch.setattr(generator, "solve_teacher", fake_teacher)
    output = tmp_path / "package"
    generator.generate_pilot(Path("configs/policy_pilot.json"), output)
    return output


def test_audit_verifies_sources_splits_hashes_and_label_semantics(pilot_package):
    audit = audit_pilot(pilot_package)
    assert audit["status"] == "accepted_for_receiver_review"
    assert audit["source_count"] == 30
    assert audit["split_counts"] == {"train": 18, "validation": 6, "test": 6}
    for key in ("cross_split_source_count", "duplicate_source_content_count", "duplicate_observation_content_count"):
        assert audit[key] == 0
    assert audit["eligible_count"] == len(read_rows(pilot_package / "samples.jsonl"))
    assert audit["family_counts"]["low_energy"]["sources"] == 2
    assert audit["plan_rejections"]["robust"]["first_failed_check_counts"]["NO_VISIBLE_WINDOW"] > 0
    assert audit["label_quality"]["idle_in_optimal_set"] != audit["label_quality"]["tied_optimal_set"]
    assert audit["inputs"]["verifier_code_sha256"] == {
        "training/audit_policy_dataset.py": hashlib.sha256(
            Path(dataset_auditor.__file__).read_bytes()
        ).hexdigest(),
        "training/audit_policy_pilot.py": hashlib.sha256(
            Path(pilot_auditor.__file__).read_bytes()
        ).hexdigest(),
    }
    text = render_pilot_audit(audit)
    for phrase in ("synthetic pilot", "not a formal experiment", "idle_in_optimal_set", "tied_optimal_set", "B acceptance", "UNSUPPORTED", "ERROR", "Verifier code SHA256"):
        assert phrase in text


def test_rehashed_source_protocol_drift_is_rejected(pilot_package):
    rows = read_rows(pilot_package / "sources.jsonl")
    rows[0]["scenario"]["initial_energy_Wh"] += 0.01
    identity = json.loads(json.dumps(rows[0]["scenario"]))
    identity.pop("scenario_id", None)
    if isinstance(identity.get("channel"), dict):
        identity["channel"].pop("seed", None)
    rows[0]["content_sha256"] = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    rewrite(pilot_package, "sources.jsonl", rows)
    with pytest.raises(ValueError, match="SOURCE_PROTOCOL_MISMATCH"):
        audit_pilot(pilot_package)


def test_rehashed_split_protocol_drift_is_rejected(pilot_package):
    splits = json.loads((pilot_package / "source_splits.json").read_bytes())
    splits["split_seed"] += 1
    rewrite(pilot_package, "source_splits.json", splits)
    with pytest.raises(ValueError, match="SOURCE_SPLIT_PROTOCOL_MISMATCH"):
        audit_pilot(pilot_package)


def test_unknown_attempt_source_has_deliberate_error(pilot_package):
    rows = read_rows(pilot_package / "attempts.jsonl")
    rows[0]["source_id"] = "invented"
    rewrite(pilot_package, "attempts.jsonl", rows)
    with pytest.raises(ValueError, match="UNKNOWN_ATTEMPT_SOURCE"):
        audit_pilot(pilot_package)


def test_split_verification_rejects_state_moved_to_another_split():
    with pytest.raises(ValueError, match="SOURCE_SPLIT_MISMATCH"):
        verify_split_inheritance([{"source_id": "a", "split": "validation"}],
                                 {"splits": {"train": ["a"], "validation": [], "test": []}})


@pytest.mark.parametrize("mutation,code", [
    ("hash", "OUTPUT_HASH"), ("filenames", "OUTPUT_FILES"),
    ("source_hash", "SOURCE_HASH"), ("duplicate_source", "DUPLICATE_SOURCE"),
    ("split", "SOURCE_SPLIT"), ("observation", "OBSERVATION_HASH"),
    ("partition", "ATTEMPT_PARTITION"), ("eligibility", "LABEL_ELIGIBILITY"),
    ("summary", "SUMMARY"), ("nan", "FINITE"), ("duplicate_state", "DUPLICATE_STATE"),
])
def test_independent_recomputation_rejects_rehashed_tampering(pilot_package, mutation, code):
    if mutation == "hash":
        with (pilot_package / "samples.jsonl").open("ab") as stream:
            stream.write(b" ")
    elif mutation == "filenames":
        manifest = json.loads((pilot_package / "manifest.json").read_bytes())
        del manifest["output_sha256"]["sources.jsonl"]
        (pilot_package / "manifest.json").write_text(json.dumps(manifest))
    elif mutation in {"source_hash", "duplicate_source"}:
        rows = read_rows(pilot_package / "sources.jsonl")
        if mutation == "source_hash":
            rows[0]["content_sha256"] = "0" * 64
        else:
            rows[1] = rows[0]
        rewrite(pilot_package, "sources.jsonl", rows)
    elif mutation == "summary":
        summary = json.loads((pilot_package / "summary.json").read_bytes())
        summary["eligible"] += 1
        rewrite(pilot_package, "summary.json", summary)
    else:
        rows = read_rows(pilot_package / "attempts.jsonl")
        if mutation == "split":
            rows[0]["split"] = "validation" if rows[0]["split"] != "validation" else "train"
        elif mutation == "observation":
            rows[0]["observation"]["sim_time_s"] += 0.1
        elif mutation == "partition":
            rewrite(pilot_package, "samples.jsonl", [])
        elif mutation == "eligibility":
            rows[0]["gap"] = 0.1
        elif mutation == "nan":
            rows[0]["elapsed_ms"] = float("nan")
        elif mutation == "duplicate_state":
            rows.append(rows[0])
        rewrite(pilot_package, "attempts.jsonl", rows)
    with pytest.raises(ValueError, match=code):
        audit_pilot(pilot_package)


def test_blocked_empty_package_and_cli_verify(pilot_package, tmp_path, capsys):
    for name in ("attempts.jsonl", "samples.jsonl", "diagnostics.jsonl"):
        rewrite(pilot_package, name, [])
    summary = json.loads((pilot_package / "summary.json").read_bytes())
    summary.update(status="blocked", sources_attempted=0, total=0, eligible=0, ineligible=0,
                   stop_reason="CPU_BUDGET", cpu_elapsed_s=7200, solver_status_counts={})
    rewrite(pilot_package, "summary.json", summary)
    audit = audit_pilot(pilot_package)
    assert audit["status"] == "blocked_diagnostics_verified"
    for key in ("label_quality", "coverage", "teacher"):
        assert audit[key] == {"not_computed_reason": "NO_ELIGIBLE_LABELS"}
    output = tmp_path / "audit"
    assert main(["--package", str(pilot_package), "--output-dir", str(output)]) == 1
    assert main(["--package", str(pilot_package), "--output-dir", str(output), "--verify"]) == 0
    (output / "audit.json").write_text("{}")
    assert main(["--package", str(pilot_package), "--output-dir", str(output), "--verify"]) == 2


def test_cli_ready_and_corrupt(pilot_package, tmp_path):
    output = tmp_path / "audit"
    assert main(["--package", str(pilot_package), "--output-dir", str(output)]) == 0
    assert main(["--package", str(pilot_package), "--output-dir", str(output), "--verify"]) == 0
    (pilot_package / "samples.jsonl").write_bytes(b"broken")
    assert main(["--package", str(pilot_package), "--output-dir", str(output)]) == 2


def stable_label_hash(row):
    raw = json.dumps({key: value for key, value in row.items()
                      if key not in {"elapsed_ms", "label_content_sha256"}},
                     ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.mark.parametrize("status,reason,keep_scores", [
    ("UNSUPPORTED_LOSS", "not_applicable_teacher_preflight", True),
    ("ERROR", "not_available_error", False),
    ("ERROR", "not_available_error", True),
])
def test_preflight_and_error_diagnostics_are_honest(pilot_package, status, reason, keep_scores):
    rows = read_rows(pilot_package / "attempts.jsonl")
    for row in rows:
        row.update(solver_status=status, gap=None, label_eligible=False, exclusion_reasons=[status])
        if status == "ERROR" and not keep_scores:
            del row["candidate_scores"]
            del row["label_content_sha256"]
        else:
            for label in row["candidate_scores"]:
                label.update(feasible=label["mode"] == "idle", score=0.0)
            row["label_content_sha256"] = stable_label_hash(row)
    rewrite(pilot_package, "attempts.jsonl", rows)
    rewrite(pilot_package, "samples.jsonl", [])
    rewrite(pilot_package, "diagnostics.jsonl", rows)
    summary = json.loads((pilot_package / "summary.json").read_bytes())
    summary.update(status="blocked", eligible=0, ineligible=len(rows),
                   solver_status_counts={status: len(rows)}, exclusion_reason_counts={status: len(rows)})
    rewrite(pilot_package, "summary.json", summary)
    audit = audit_pilot(pilot_package)
    assert audit["status"] == "blocked_diagnostics_verified"
    assert audit["feasibility_crosscheck_counts"] == {reason: len(rows)}
    if status != "ERROR":
        assert audit["plan_rejections"]["robust"]["checked_count"] > 0


def test_recomputed_plan_rejects_rehashed_feasibility_lie(pilot_package):
    rows = read_rows(pilot_package / "attempts.jsonl")
    row = rows[0]
    row["candidate_scores"][0]["feasible"] = not row["candidate_scores"][0]["feasible"]
    row["label_content_sha256"] = stable_label_hash(row)
    rewrite(pilot_package, "attempts.jsonl", rows)
    rewrite(pilot_package, "samples.jsonl", rows)
    with pytest.raises(ValueError, match="PLAN_FEASIBILITY_MISMATCH"):
        audit_pilot(pilot_package)


def test_optimal_rows_have_verified_feasibility(pilot_package):
    audit = audit_pilot(pilot_package)
    assert audit["feasibility_crosscheck_counts"] == {"verified": audit["eligible_count"]}


@pytest.mark.parametrize("status", ["TIME_LIMIT_FEASIBLE", "NODE_LIMIT_FEASIBLE"])
def test_limited_rows_still_require_plan_crosscheck(pilot_package, status):
    rows = read_rows(pilot_package / "attempts.jsonl")[:3]
    for row in rows:
        row.update(solver_status=status, gap=0.5, label_eligible=False, exclusion_reasons=[status])
        row["label_content_sha256"] = stable_label_hash(row)
    for name, values in (("attempts.jsonl", rows), ("samples.jsonl", []), ("diagnostics.jsonl", rows)):
        rewrite(pilot_package, name, values)
    summary = json.loads((pilot_package / "summary.json").read_bytes())
    summary.update(status="blocked", sources_attempted=len({row["source_id"] for row in rows}),
                   total=3, eligible=0, ineligible=3, limited_result_count=3,
                   stop_reason="REPEATED_SOLVER_LIMIT", solver_status_counts={status: 3},
                   exclusion_reason_counts={status: 3})
    rewrite(pilot_package, "summary.json", summary)
    audit = audit_pilot(pilot_package)
    assert audit["feasibility_crosscheck_counts"] == {"verified": 3}


@pytest.mark.parametrize("kind", ["source", "observation", "split", "json_key"])
def test_duplicate_contents_and_split_membership_are_rejected(pilot_package, kind):
    if kind == "source":
        rows = read_rows(pilot_package / "sources.jsonl")
        rows[1]["scenario"] = rows[0]["scenario"]
        rows[1]["content_sha256"] = rows[0]["content_sha256"]
        rewrite(pilot_package, "sources.jsonl", rows)
        code = "DUPLICATE_SOURCE_CONTENT"
    elif kind == "observation":
        rows = read_rows(pilot_package / "attempts.jsonl")
        rows[1]["observation"] = rows[0]["observation"]
        rows[1]["observation_sha256"] = rows[0]["observation_sha256"]
        rewrite(pilot_package, "attempts.jsonl", rows)
        code = "DUPLICATE_OBSERVATION_CONTENT"
    elif kind == "split":
        splits = json.loads((pilot_package / "source_splits.json").read_bytes())
        splits["splits"]["test"][0] = splits["splits"]["train"][0]
        rewrite(pilot_package, "source_splits.json", splits)
        code = "SOURCE_SPLIT_COMPLETENESS"
    else:
        manifest = (pilot_package / "manifest.json").read_text()
        (pilot_package / "manifest.json").write_text('{"schema_version":"bad",' + manifest[1:])
        code = "DUPLICATE_JSON_KEY"
    with pytest.raises(ValueError, match=code):
        audit_pilot(pilot_package)


@pytest.mark.parametrize("field,value", [("failures", [{"source_id": "invented", "code": "X"}]),
                                        ("integrity_failure_count", 1), ("cpu_elapsed_s", -1),
                                        ("stop_reason", "REPEATED_SOLVER_LIMIT")])
def test_summary_auxiliary_claims_are_not_blindly_trusted(pilot_package, field, value):
    summary = json.loads((pilot_package / "summary.json").read_bytes())
    summary[field] = value
    summary["status"] = "blocked" if field in {"stop_reason", "failures"} else summary["status"]
    rewrite(pilot_package, "summary.json", summary)
    with pytest.raises(ValueError, match="SUMMARY"):
        audit_pilot(pilot_package)
