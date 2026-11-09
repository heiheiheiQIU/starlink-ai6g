"""Recompute auditable teacher labels from public observations only."""

from __future__ import annotations

import copy
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

from backend.contracts import Observation, validate_teacher_result
from backend.policies.teacher import TeacherConfig, solve_teacher


LABEL_CONTENT_FIELDS = (
    "dataset_version", "sample_id", "scenario_id", "source_group_id", "state_id", "source_revision",
    "source_observation_sha256", "observation", "teacher_version",
    "teacher_config_sha256", "candidate_scores", "solver_status",
    "gap", "diagnostics", "label_eligible", "exclusion_reasons",
    "observation_content_sha256",
)
EXECUTION_ID_FIELDS = frozenset({"run_id", "policy_id"})
DATASET_VERSION = "a-n3-teacher-20-v2"
LEAK_FIELDS = {
    "true_capacity", "capacity_true_wh", "future_arrivals",
    "actual_future_loss", "evaluation_truth", "energy_true_wh", "soc_true",
}


class TeacherDataError(ValueError):
    """Controlled data boundary failure, with a machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def observation_content_sha256(payload: dict[str, object]) -> str:
    """Identify a public decision input independently of execution labels."""
    content = copy.deepcopy(payload)
    for field in EXECUTION_ID_FIELDS:
        content.pop(field, None)
    return sha256_text(canonical_json(content))


def _source_group_id(source: dict[str, object]) -> str:
    value = source.get("source_group_id", source.get("scenario_id"))
    if not isinstance(value, str) or not value.strip():
        raise TeacherDataError("INVALID_SOURCE_GROUP", "source_group_id must be nonempty")
    return value


def label_content_sha256(record: dict[str, object]) -> str:
    return sha256_text(canonical_json({key: record[key] for key in LABEL_CONTENT_FIELDS}))


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reject_leaks(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in LEAK_FIELDS:
                raise TeacherDataError("LEAK_FIELD", f"Hidden-truth field: {key}")
            _reject_leaks(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_leaks(child)


def generate_record(
    source: dict[str, object],
    *,
    source_revision: str,
    budget_ms: int,
    teacher_config_path: Path,
) -> dict[str, object]:
    """Solve one source observation; never reuse labels in its envelope."""
    try:
        sample_id = source["sample_id"]
        payload = source["observation"]
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError("sample_id must be a nonempty string")
        _reject_leaks(payload)
        before = canonical_json(payload)
        observation = Observation.model_validate(payload)
        parsed_before = canonical_json(observation.model_dump(mode="json"))
        group_id = _source_group_id(source)
        content_sha256 = observation_content_sha256(payload)
    except TeacherDataError:
        raise
    except (KeyError, ValueError, TypeError) as error:
        raise TeacherDataError("INVALID_OBSERVATION", str(error)) from error

    config_bytes = teacher_config_path.read_bytes()
    config = json.loads(config_bytes)
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    diagnostics: dict[str, object] = {}
    result = solve_teacher(observation, budget_ms=budget_ms,
                           config=config, diagnostics=diagnostics)
    try:
        unchanged = (canonical_json(payload) == before and
                     canonical_json(observation.model_dump(mode="json")) == parsed_before)
    except (ValueError, TypeError):
        unchanged = False
    if not unchanged:
        raise TeacherDataError("OBSERVATION_MUTATED", "Teacher modified its observation")

    try:
        result = validate_teacher_result(observation, result)
        keys = [(item.task_id, item.mode) for item in result.candidate_scores]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate candidate keys")
        if any(not math.isfinite(item.score) for item in result.candidate_scores):
            raise ValueError("Candidate scores must be finite")
        if result.gap is not None and not math.isfinite(result.gap):
            raise ValueError("Gap must be finite")
    except (ValueError, TypeError) as error:
        raise TeacherDataError("INVALID_TEACHER_RESULT", str(error)) from error

    # Candidate timing is runtime evidence and cannot enter the stable label hash.
    for candidate in diagnostics.get("candidates", []):
        candidate.pop("elapsed_ms", None)

    eligible = result.solver_status == "OPTIMAL" and result.gap == 0.0
    record: dict[str, object] = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "sample_id": sample_id,
        "scenario_id": observation.run_id,
        "source_group_id": group_id,
        "state_id": sample_id,
        "source_revision": source_revision,
        "source_observation_sha256": sha256_text(before),
        "observation_content_sha256": content_sha256,
        "observation": copy.deepcopy(payload),
        "teacher_version": diagnostics["teacher_version"],
        "teacher_config_sha256": config_sha256,
        "candidate_scores": [item.model_dump(mode="json") for item in result.candidate_scores],
        "solver_status": result.solver_status,
        "gap": result.gap,
        "elapsed_ms": result.elapsed_ms,
        "diagnostics": diagnostics,
        "label_eligible": eligible,
        "exclusion_reasons": [] if eligible else [result.solver_status],
    }
    record["label_content_sha256"] = label_content_sha256(record)
    return record


def _command_path(path: Path) -> str:
    """Use portable relative paths in the recorded invocation."""
    root = Path(__file__).resolve().parents[1]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise TeacherDataError("PATH_OUTSIDE_PROJECT",
                               "Dataset paths must resolve inside the repository") from error


def _check_destination(output_dir: Path) -> None:
    if output_dir.is_symlink() or (output_dir.exists() and (
            not output_dir.is_dir() or any(output_dir.iterdir()))):
        raise TeacherDataError("OUTPUT_NOT_EMPTY", "Destination must be absent or empty")


def generate_teacher_dataset(
    *, source_path: Path, output_dir: Path, source_revision: str,
    teacher_config_path: Path, budget_ms: int, expected_count: int = 20,
) -> dict[str, object]:
    """Publish complete audit evidence, including excluded and failed samples.

    Invalid inputs fail before solving. Per-sample solver failures are evidence,
    so they block readiness but do not discard the other source observations.
    """
    staging = None
    try:
        # Validate all provenance paths before reading inputs or starting work.
        source_command = _command_path(source_path)
        output_command = _command_path(output_dir)
        config_command = _command_path(teacher_config_path)
        _check_destination(output_dir)
        if not isinstance(source_revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", source_revision):
            raise TeacherDataError("INVALID_SOURCE_REVISION", "Expected a 40-hex source revision")
        if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count < 1:
            raise TeacherDataError("UNEXPECTED_COUNT", "expected_count must be positive")
        if isinstance(budget_ms, bool) or not isinstance(budget_ms, int) or not 1 <= budget_ms <= 5000:
            raise TeacherDataError("INVALID_TEACHER_BUDGET", "budget_ms must be in 1..5000")
        source_bytes = source_path.read_bytes()
        sources = [json.loads(line) for line in source_bytes.decode("utf-8").splitlines()]
        if len(sources) != expected_count:
            raise TeacherDataError("UNEXPECTED_COUNT", f"Expected {expected_count} rows; got {len(sources)}")
        sample_ids, scenario_ids, content_hashes = set(), set(), set()
        for source in sources:
            if not isinstance(source, dict):
                raise TeacherDataError("INVALID_OBSERVATION", "Source rows must be objects")
            sample_id = source.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id.strip():
                raise TeacherDataError("INVALID_OBSERVATION", "sample_id must be a nonempty string")
            payload = source.get("observation")
            _reject_leaks(payload)
            canonical_json(payload)
            observation = Observation.model_validate(payload)
            group_id = _source_group_id(source)
            content_sha256 = observation_content_sha256(payload)
            if sample_id in sample_ids:
                raise TeacherDataError("DUPLICATE_SAMPLE_ID", sample_id)
            if observation.run_id in scenario_ids:
                raise TeacherDataError("DUPLICATE_SCENARIO_ID", observation.run_id)
            if content_sha256 in content_hashes:
                raise TeacherDataError("DUPLICATE_OBSERVATION_CONTENT", content_sha256)
            sample_ids.add(sample_id)
            scenario_ids.add(observation.run_id)
            content_hashes.add(content_sha256)
        config_bytes = teacher_config_path.read_bytes()
        config = TeacherConfig.model_validate_json(config_bytes)
        config_sha256 = hashlib.sha256(config_bytes).hexdigest()
        sources.sort(key=lambda row: (row["observation"]["run_id"], row["sample_id"]))
        records = []
        for source in sources:
            try:
                record = generate_record(source, source_revision=source_revision,
                                         budget_ms=budget_ms, teacher_config_path=teacher_config_path)
                if record["teacher_config_sha256"] != config_sha256:
                    raise TeacherDataError("CONFIG_CHANGED", "Teacher config changed during generation")
            except Exception as error:
                code = error.code if isinstance(error, TeacherDataError) else "SAMPLE_GENERATION_FAILED"
                failure = ({"code": code, "message": str(error)}
                           if isinstance(error, TeacherDataError) else {
                               "code": code, "exception_type": type(error).__name__,
                               "message": "Unexpected sample generation failure",
                           })
                record = {
                    "schema_version": "1.0", "dataset_version": DATASET_VERSION,
                    "sample_id": source["sample_id"], "state_id": source["sample_id"],
                    "scenario_id": source["observation"]["run_id"],
                    "source_group_id": _source_group_id(source),
                    "observation": copy.deepcopy(source["observation"]),
                    "source_observation_sha256": sha256_text(canonical_json(source["observation"])),
                    "observation_content_sha256": observation_content_sha256(source["observation"]),
                    "source_revision": source_revision, "teacher_version": config.version,
                    "teacher_config_sha256": config_sha256, "solver_status": "ERROR",
                    "gap": None, "label_eligible": False, "exclusion_reasons": [code],
                    "error": failure,
                }
            records.append(record)
        status_counts = dict(sorted(Counter(r["solver_status"] for r in records).items()))
        eligible = sum(r["label_eligible"] for r in records)
        failures = sum("error" in r for r in records)
        total = len(records)
        ready = (total == expected_count and eligible == expected_count and failures == 0
                 and status_counts == {"OPTIMAL": expected_count})
        summary = {"status": "ready_for_split" if ready else "blocked", "total": total,
                   "eligible": eligible, "ineligible": total - eligible, "failures": failures,
                   "solver_status_counts": status_counts}
        samples_text = "".join(canonical_json(row) + "\n" for row in records)
        summary_text = canonical_json(summary) + "\n"
        command = ["python", "-m", "training.generate_teacher_data", "--source", source_command,
                   "--output", output_command, "--source-revision", source_revision,
                   "--teacher-config", config_command, "--budget-ms", str(budget_ms),
                   "--expected-count", str(expected_count)]
        manifest = {
            "dataset_version": DATASET_VERSION,
            "source_revision": source_revision,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "teacher_config_sha256": config_sha256, "teacher_version": config.version,
            "budget_ms": budget_ms, "expected_count": expected_count,
            "schema_versions": {"observation": "1.0", "teacher_record": "1.0", "manifest": "1.0"},
            "command": command,
            "file_row_counts": {"source": len(sources), "samples.jsonl": total, "summary.json": 1},
            "output_sha256": {"samples.jsonl": sha256_text(samples_text),
                              "summary.json": sha256_text(summary_text)},
        }
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
        contents = {"samples.jsonl": samples_text, "summary.json": summary_text,
                    "manifest.json": canonical_json(manifest) + "\n"}
        for name, value in contents.items():
            with (staging / name).open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(value)
        for name, value in contents.items():
            raw = (staging / name).read_bytes()
            if raw != value.encode("utf-8"):
                raise TeacherDataError("OUTPUT_VERIFICATION_FAILED", name)
            for line in raw.decode("utf-8").splitlines():
                json.loads(line)
        _check_destination(output_dir)
        if output_dir.exists():
            output_dir.rmdir()  # Only an empty directory can be removed here.
        staging.rename(output_dir)
        staging = None
        return summary
    except TeacherDataError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise TeacherDataError("DATASET_GENERATION_FAILED", str(error)) from error
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--teacher-config", type=Path, required=True)
    parser.add_argument("--budget-ms", type=int, required=True)
    parser.add_argument("--expected-count", type=int, default=20)
    args = parser.parse_args()
    try:
        summary = generate_teacher_dataset(source_path=args.source, output_dir=args.output,
            source_revision=args.source_revision, teacher_config_path=args.teacher_config,
            budget_ms=args.budget_ms, expected_count=args.expected_count)
    except TeacherDataError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(canonical_json(summary))
    return 0 if summary["status"] == "ready_for_split" else 1


if __name__ == "__main__":
    raise SystemExit(main())
