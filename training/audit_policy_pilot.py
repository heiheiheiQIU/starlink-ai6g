"""Independently verify synthetic pilot evidence; training remains disabled."""

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

from backend.contracts import Observation, TeacherResult, validate_teacher_result
from backend.policies.common import plan_candidate
from backend.policies.teacher import TeacherConfig
from training.audit_policy_dataset import audit_rows

ROOT = Path(__file__).resolve().parents[1]
FILES = {"sources.jsonl", "source_splits.json", "attempts.jsonl", "samples.jsonl",
         "diagnostics.jsonl", "summary.json"}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _content_hash(value):
    return _digest(_canonical(value).encode("utf-8"))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _finite(value):
    if isinstance(value, float):
        _require(math.isfinite(value), "NON_FINITE_JSON")
    elif isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)


def _parse(raw):
    value = json.loads(raw, object_pairs_hook=_pairs)
    _finite(value)
    _require(isinstance(value, dict), "JSON_OBJECT_REQUIRED")
    return value


def verify_split_inheritance(rows, split_manifest) -> None:
    expected = {}
    for split, ids in split_manifest["splits"].items():
        for source_id in ids:
            _require(source_id not in expected, "SOURCE_SPLIT_DUPLICATE")
            expected[source_id] = split
    for row in rows:
        _require(row.get("source_id") in expected and expected[row["source_id"]] == row.get("split"),
                 f"SOURCE_SPLIT_MISMATCH: {row.get('source_id')}")


def _public_only(value):
    forbidden = {"protocol_state", "true_windows", "future_arrivals", "evaluation_truth",
                 "energy_true_wh", "true_capacity", "capacity_true_wh", "soc_true", "actual_future_loss"}
    if isinstance(value, dict):
        for key, child in value.items():
            _require(key.lower() not in forbidden, "LEAK_FIELD")
            _public_only(child)
    elif isinstance(value, list):
        for child in value:
            _public_only(child)


def audit_pilot(package_dir) -> dict[str, object]:
    package = Path(package_dir)
    manifest = _parse((package / "manifest.json").read_bytes())
    _require(manifest.get("schema_version") == "pilot-manifest-v1" and
             manifest.get("dataset_version") == "a-n4-pilot-v1" and
             manifest.get("training_enabled") is False, "MANIFEST_PROTOCOL")
    outputs = manifest.get("output_sha256", {})
    _require(set(outputs) == FILES and set(manifest.get("file_row_counts", {})) == FILES, "OUTPUT_FILES")
    parsed, verified = {}, {}
    for name in sorted(FILES):
        raw = (package / name).read_bytes()
        verified[name] = _digest(raw)
        _require(re.fullmatch(r"[0-9a-f]{64}", str(outputs[name])) and verified[name] == outputs[name], "OUTPUT_HASH: " + name)
        _require(manifest["file_row_counts"][name] == len(raw.splitlines()), "OUTPUT_ROW_COUNT")
        parsed[name] = ([_parse(line) for line in raw.splitlines()] if name.endswith("jsonl") else _parse(raw))
    code_names = {"training/generate_policy_pilot.py", "training/pilot_scenarios.py",
                  "backend/policies/teacher.py", "backend/policies/common.py", "backend/contracts.py",
                  *(path.relative_to(ROOT).as_posix() for path in (ROOT / "backend/simulator").glob("*.py"))}
    _require(set(manifest.get("code_sha256", {})) == code_names, "CODE_FILES")
    for name in sorted(code_names):
        _require(manifest["code_sha256"][name] == _digest((ROOT / name).read_bytes()), "CODE_HASH: " + name)
    config_raw = (ROOT / "configs/policy_pilot.json").read_bytes()
    _require(manifest.get("config_sha256") == _digest(config_raw), "CONFIG_HASH")
    config = _parse(config_raw)
    teacher_path = Path(config["teacher_config_path"])
    if not teacher_path.is_absolute():
        teacher_path = ROOT / teacher_path
    teacher_raw = teacher_path.read_bytes()
    _require(manifest.get("teacher_config_sha256") == _digest(teacher_raw), "TEACHER_CONFIG_HASH")
    teacher = TeacherConfig.model_validate(_parse(teacher_raw))
    _require(manifest.get("teacher_version") == teacher.version and manifest.get("budget_ms") == 1000
             and manifest.get("cpu_budget_s") == 7200, "TEACHER_PROTOCOL")

    sources = parsed["sources.jsonl"]
    source_ids = [source["source_id"] for source in sources]
    _require(len(set(source_ids)) == len(source_ids), "DUPLICATE_SOURCE")
    _require(len(sources) == 30, "SOURCE_COUNT")
    source_by_id = dict(zip(source_ids, sources))
    source_hashes = set()
    for source in sources:
        identity = copy.deepcopy(source["scenario"])
        identity.pop("scenario_id", None)
        if isinstance(identity.get("channel"), dict):
            identity["channel"].pop("seed", None)
        content_hash = _content_hash(identity)
        _require(source.get("content_sha256") == content_hash, "SOURCE_HASH")
        _require(content_hash not in source_hashes, "DUPLICATE_SOURCE_CONTENT")
        source_hashes.add(content_hash)
    splits = parsed["source_splits.json"]
    expected_counts = {"train": 18, "validation": 6, "test": 6}
    _require(set(splits["splits"]) == set(expected_counts), "SOURCE_SPLIT_NAMES")
    members = [sid for ids in splits["splits"].values() for sid in ids]
    _require(len(members) == len(set(members)) == 30 and set(members) == set(source_ids), "SOURCE_SPLIT_COMPLETENESS")
    split_counts = {key: len(ids) for key, ids in splits["splits"].items()}
    _require(split_counts == expected_counts and splits.get("counts") == split_counts, "SOURCE_SPLIT_COUNTS")
    attempts, samples, diagnostics = (parsed[name] for name in ("attempts.jsonl", "samples.jsonl", "diagnostics.jsonl"))
    for rows in (attempts, samples, diagnostics):
        verify_split_inheritance(rows, splits)

    seen_ids, observation_hashes = set(), set()
    plans = {mode: {"checked_count": 0, "rejected_count": 0, "first_failed_check_counts": Counter()}
             for mode in ("robust", "fast")}
    candidate_diagnostics = {mode: Counter() for mode in ("robust", "fast", "idle")}
    crosschecks = Counter()
    family_counts = {family: {"sources": 0, "sampled_states": 0, "eligible_states": 0}
                     for family in sorted({source["family"] for source in sources})}
    for source in sources:
        family_counts[source["family"]]["sources"] += 1
    for row in attempts:
        _public_only(row)
        source = source_by_id[row["source_id"]]
        identity = row.get("state_id", "source-error:" + row["source_id"])
        _require(identity not in seen_ids, "DUPLICATE_STATE")
        seen_ids.add(identity)
        eligible = row.get("solver_status") == "OPTIMAL" and row.get("gap") == 0.0
        _require(type(row.get("label_eligible")) is bool and row["label_eligible"] == eligible, "LABEL_ELIGIBILITY")
        if "state_id" in row:
            _require(row["state_id"] == f"{row['source_id']}:{row.get('capture_index')}" and
                     row.get("family") == source["family"] and row.get("seed") == source["seed"], "STATE_IDENTITY")
        if "observation" in row:
            payload = row["observation"]
            _require(row.get("observation_sha256") == _content_hash(payload), "OBSERVATION_HASH")
            observation = Observation.model_validate(payload)
            content_hash = _content_hash({key: value for key, value in payload.items() if key not in {"run_id", "policy_id"}})
            _require(content_hash not in observation_hashes, "DUPLICATE_OBSERVATION_CONTENT")
            observation_hashes.add(content_hash)
            family_counts[source["family"]]["sampled_states"] += 1
        else:
            _require(row["solver_status"] == "ERROR" and not eligible, "MISSING_OBSERVATION")
        if "candidate_scores" in row:
            _require("observation" in row, "MISSING_OBSERVATION")
            result = validate_teacher_result(observation, TeacherResult.model_validate({
                key: row[key] for key in ("candidate_scores", "solver_status", "gap", "elapsed_ms")}))
            _require(row.get("teacher_version") == teacher.version and
                     row.get("teacher_config_sha256") == _digest(teacher_raw), "LABEL_TEACHER_BINDING")
            _require(row.get("label_content_sha256") == _content_hash({
                key: value for key, value in row.items() if key not in {"elapsed_ms", "label_content_sha256"}}), "LABEL_HASH")
            labels = {(label.task_id, label.mode): label for label in result.candidate_scores}
            planned_status = row["solver_status"] in {"OPTIMAL", "TIME_LIMIT_FEASIBLE", "NODE_LIMIT_FEASIBLE"}
            crosschecks["not_available_error" if row["solver_status"] == "ERROR" else
                        "verified" if planned_status else "not_applicable_teacher_preflight"] += 1
            for task in observation.tasks:
                for mode in ("robust", "fast"):
                    if (task.task_id, mode) not in labels:
                        _require(not eligible and row["solver_status"].startswith("UNSUPPORTED"), "MISSING_CANDIDATE")
                    plan = plan_candidate(observation, task, mode, teacher.policy)
                    if planned_status:
                        _require(plan.feasible == labels[task.task_id, mode].feasible, "PLAN_FEASIBILITY_MISMATCH")
                    plans[mode]["checked_count"] += 1
                    if not plan.feasible:
                        plans[mode]["rejected_count"] += 1
                        failed = next(check.code for check in plan.checks if not check.passed)
                        plans[mode]["first_failed_check_counts"][failed] += 1
            for candidate in row.get("diagnostics", {}).get("candidates", []):
                mode = candidate["mode"]
                _require(mode in candidate_diagnostics, "DIAGNOSTIC_MODE")
                candidate_diagnostics[mode]["searched_count"] += 1
                if candidate.get("limited"):
                    candidate_diagnostics[mode][candidate["limited"]] += 1
        else:
            _require(not eligible and row["solver_status"] == "ERROR", "MISSING_LABELS")
            crosschecks["not_available_error"] += 1
        if eligible:
            family_counts[source["family"]]["eligible_states"] += 1
    expected_samples = [row for row in attempts if row["label_eligible"]]
    expected_diagnostics = [row for row in attempts if not row["label_eligible"]]
    _require(Counter(map(_canonical, samples)) == Counter(map(_canonical, expected_samples)) and
             Counter(map(_canonical, diagnostics)) == Counter(map(_canonical, expected_diagnostics)), "ATTEMPT_PARTITION")
    statuses = dict(sorted(Counter(row["solver_status"] for row in attempts).items()))
    reasons = dict(sorted(Counter(reason for row in diagnostics for reason in row.get("exclusion_reasons", [row["solver_status"]])).items()))
    summary = parsed["summary.json"]
    limited = sum(statuses.get(status, 0) for status in ("TIME_LIMIT_FEASIBLE", "NODE_LIMIT_FEASIBLE"))
    failures = [{"source_id": row["source_id"], "code": row["exclusion_reasons"][0]}
                for row in attempts if "state_id" not in row and row["solver_status"] == "ERROR"]
    integrity_failures = sum(row.get("diagnostics", {}).get("error_type") == "PilotDataError"
                             for row in diagnostics)
    recomputed = {"sources_attempted": len({row["source_id"] for row in attempts}), "total": len(attempts),
                  "eligible": len(samples), "ineligible": len(diagnostics), "limited_result_count": limited,
                  "solver_status_counts": statuses, "exclusion_reason_counts": reasons, "training_enabled": False,
                  "failures": failures, "integrity_failure_count": integrity_failures}
    for key, value in recomputed.items():
        _require(summary.get(key) == value, "SUMMARY_MISMATCH: " + key)
    elapsed = summary.get("cpu_elapsed_s")
    _require(type(elapsed) in (int, float) and elapsed >= 0, "SUMMARY_CPU_ELAPSED")
    stop_reason = summary.get("stop_reason")
    _require(stop_reason in {None, "CPU_BUDGET", "REPEATED_SOLVER_LIMIT"}, "SUMMARY_STOP_REASON")
    _require((stop_reason != "CPU_BUDGET" or elapsed >= 7200)
             and (stop_reason != "REPEATED_SOLVER_LIMIT" or limited == 3)
             and (limited < 3 or stop_reason == "REPEATED_SOLVER_LIMIT")
             and (elapsed < 7200 or stop_reason is not None), "SUMMARY_STOP_EVIDENCE")
    ready = (recomputed["sources_attempted"] == 30 and 60 <= len(samples) <= 120
             and not statuses.get("ERROR", 0) and not summary.get("failures") and summary.get("stop_reason") is None)
    _require(summary.get("status") == ("ready_for_audit" if ready else "blocked"), "SUMMARY_STATUS")
    row_audit = (audit_rows(samples, reserve_wh=0.5) if samples else
                 {key: {"not_computed_reason": "NO_ELIGIBLE_LABELS"} for key in ("label_quality", "coverage", "teacher")})
    return {
        "schema_version": "policy-pilot-audit-v1",
        "status": "accepted_for_receiver_review" if ready and samples else "blocked_diagnostics_verified",
        "source_count": len(sources), "split_counts": split_counts, "attempt_count": len(attempts),
        "eligible_count": len(samples), "diagnostic_count": len(diagnostics),
        "cross_split_source_count": 0, "duplicate_source_content_count": 0,
        "duplicate_observation_content_count": 0, "family_counts": family_counts,
        "label_quality": row_audit["label_quality"], "coverage": row_audit["coverage"], "teacher": row_audit["teacher"],
        "solver_status_counts": statuses, "exclusion_reason_counts": reasons,
        "stop_reason": summary.get("stop_reason"), "plan_rejections": plans,
        "feasibility_crosscheck_counts": dict(sorted(crosschecks.items())),
        "candidate_diagnostics_by_mode": candidate_diagnostics,
        "inputs": {"output_sha256": verified, "manifest_sha256": _digest((package / "manifest.json").read_bytes()),
                   "config_sha256": _digest(config_raw), "teacher_config_sha256": _digest(teacher_raw),
                   "code_sha256": manifest["code_sha256"]},
    }


def render_pilot_audit(audit) -> str:
    lines = ["# A-N4b synthetic pilot audit", "", "This is synthetic pilot evidence, not a formal experiment result.",
             f"Status: {audit['status']}", f"Sources: {audit['source_count']}; eligible states: {audit['eligible_count']}; diagnostics: {audit['diagnostic_count']}.",
             "", "Actual source and state counts by family:", "", "| Family | Sources | Sampled states | Eligible states |", "|---|---:|---:|---:|"]
    for family, counts in audit["family_counts"].items():
        lines.append(f"| {family} | {counts['sources']} | {counts['sampled_states']} | {counts['eligible_states']} |")
    lines.extend(["", "Label quality (idle_in_optimal_set and tied_optimal_set are separate):",
                  _canonical(audit["label_quality"]), "", "Coverage:", _canonical(audit["coverage"]),
                  "", "All attempts, including UNSUPPORTED, TIME/NODE limited and ERROR counts (absent statuses count as zero):",
                  _canonical(audit["solver_status_counts"]), "Exclusions: " + _canonical(audit["exclusion_reason_counts"]),
                  "Stop reason: " + str(audit["stop_reason"]), "", "Public plan checks: first failed ConstraintCheck per task/mode; idle has no rejection reason.",
                  _canonical(audit["plan_rejections"]), "Teacher diagnostics by mode: " + _canonical(audit["candidate_diagnostics_by_mode"]),
                  "Feasibility crosscheck: " + _canonical(audit["feasibility_crosscheck_counts"]),
                  "", "Model training remains disabled pending B acceptance.", ""])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        audit = audit_pilot(args.package)
        contents = {"audit.json": (_canonical(audit) + "\n").encode("utf-8"),
                    "README.md": render_pilot_audit(audit).encode("utf-8")}
        # Never let output overwrite package evidence, even through path aliases.
        _require(args.output_dir.resolve() != args.package.resolve(), "OUTPUT_IS_PACKAGE")
        for name, raw in contents.items():
            path = args.output_dir / name
            if args.verify or path.exists():
                _require(path.read_bytes() == raw, "AUDIT_EVIDENCE_MISMATCH: " + name)
        if not args.verify:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, raw in contents.items():
                (args.output_dir / name).write_bytes(raw)
        print(_canonical(audit))
        return 0 if args.verify or audit["status"] == "accepted_for_receiver_review" else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
