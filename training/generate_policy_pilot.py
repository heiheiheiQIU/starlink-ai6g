"""Sample public, protocol-clean observations from real pilot evolution."""

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
import sys
from collections import Counter
from pathlib import Path
from time import process_time

from backend.contracts import Action, Observation, validate_teacher_result
from backend.policies.teacher import TeacherConfig, solve_teacher
from backend.simulator.engine import SimulatorState, create_state, observe, step
from training.pilot_scenarios import ROOT, canonical_json, sha256_json, write_source_protocol


class PilotDataError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def admit_state(state: SimulatorState) -> Observation:
    protocol = state.protocol_state
    if (state.inflight is not None
            or protocol.retry_required_key is not None
            or protocol.pending):
        raise PilotDataError(
            "SOURCE_PROTOCOL_STATE",
            "State has inflight, retry, or pending protocol work",
        )
    observation = observe(state)
    if observation.health.available_at_s > observation.sim_time_s:
        raise PilotDataError("FUTURE_HEALTH", "Health is not yet available")
    if any(task.arrival_s > observation.sim_time_s for task in observation.tasks):
        raise PilotDataError("FUTURE_TASK", "Future task leaked into observation")
    if any(
        point.robust_loss_prob != 0.0 or point.fast_loss_prob != 0.0
        for window in observation.forecast_windows
        for point in window.loss_profile
    ):
        raise PilotDataError("UNSUPPORTED_LOSS", "Pilot labels require zero loss")
    return observation


def _source_record(
    source: dict[str, object], capture_index: int, observation: Observation
) -> dict[str, object]:
    payload = observation.model_dump(mode="json")
    return {
        "source_id": source["source_id"],
        "family": source["family"],
        "seed": source["seed"],
        "capture_index": capture_index,
        "state_id": f"{source['source_id']}:{capture_index}",
        "observation": payload,
        "observation_sha256": sha256_json(payload),
    }


def sample_source(source: dict[str, object]) -> list[dict[str, object]]:
    state = create_state(
        source["scenario"], run_id=str(source["source_id"]), policy_id="pilot-source"
    )
    captured = []
    capture_steps = set(source["capture_after_steps"])
    if 0 in capture_steps:
        captured.append(_source_record(source, 0, admit_state(state)))
    for index, command in enumerate(source["evolution_steps"], start=1):
        state = step(
            state, Action.model_validate(command["action"]), float(command["dt_s"])
        ).next_state
        if index in capture_steps:
            captured.append(_source_record(source, index, admit_state(state)))
    if not 2 <= len(captured) <= 4:
        raise PilotDataError("CAPTURE_COUNT", "Each source needs 2..4 states")
    return captured


def label_state(
    record: dict[str, object], *, teacher_config: dict[str, object],
    teacher_config_sha256: str, budget_ms: int,
) -> dict[str, object]:
    observation = Observation.model_validate(record["observation"])
    before = canonical_json(observation.model_dump(mode="json"))
    diagnostics = {}
    result = validate_teacher_result(observation, solve_teacher(
        observation, budget_ms=budget_ms, config=teacher_config, diagnostics=diagnostics,
    ))
    if canonical_json(observation.model_dump(mode="json")) != before:
        raise PilotDataError("OBSERVATION_MUTATED", "Teacher modified its input")
    for candidate in diagnostics.get("candidates", []):
        candidate.pop("elapsed_ms", None)
    eligible = result.solver_status == "OPTIMAL" and result.gap == 0.0
    labelled = {
        **copy.deepcopy(record),
        "schema_version": "pilot-teacher-record-v1",
        "dataset_version": "a-n4-pilot-v1",
        "teacher_version": diagnostics["teacher_version"],
        "teacher_config_sha256": teacher_config_sha256,
        "candidate_scores": [row.model_dump(mode="json") for row in result.candidate_scores],
        "solver_status": result.solver_status,
        "gap": result.gap,
        "elapsed_ms": result.elapsed_ms,
        "diagnostics": diagnostics,
        "label_eligible": eligible,
        "exclusion_reasons": [] if eligible else [result.solver_status],
    }
    labelled["label_content_sha256"] = sha256_json({
        key: value for key, value in labelled.items() if key != "elapsed_ms"
    })
    return labelled


def partition_attempts(
    attempts: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    samples, diagnostics = [], []
    for row in attempts:
        eligible = (row.get("label_eligible") is True
                    and row.get("solver_status") == "OPTIMAL" and row.get("gap") == 0.0)
        (samples if eligible else diagnostics).append(row)
    return samples, diagnostics


def _check_destination(output):
    if output.is_symlink() or output.is_junction() or (output.exists() and (
            not output.is_dir() or any(output.iterdir()))):
        raise PilotDataError("OUTPUT_NOT_EMPTY", "Destination must be absent or empty")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _load_config(raw):
    config = json.loads(raw)
    fixed = {
        "schema_version": "policy-pilot-config-v1", "dataset_version": "a-n4-pilot-v1",
        "source_count": 30, "split_seed": 20261104,
        "split_counts": {"train": 18, "validation": 6, "test": 6},
        "states_per_source_min": 2, "states_per_source_max": 4,
        "valid_state_min": 60, "valid_state_max": 120,
        "teacher_version": "bounded-forecast-r4-v1", "teacher_budget_ms": 1000,
        "cpu_budget_s": 7200, "limited_result_stop_count": 3, "training_enabled": False,
    }
    for key, expected in fixed.items():
        if canonical_json(config.get(key)) != canonical_json(expected):
            raise PilotDataError("INVALID_CONFIG", f"Frozen field differs: {key}")
    for key in ("teacher_config_path", "output_path"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise PilotDataError("INVALID_CONFIG", f"Missing path: {key}")
    return config


def _check_record(record, source, state_ids, content_hashes):
    def reject_hidden(value):
        if isinstance(value, dict):
            forbidden = {"protocol_state", "true_windows", "future_arrivals", "evaluation_truth",
                         "energy_true_wh", "true_capacity", "capacity_true_wh", "soc_true", "actual_future_loss"}
            for key, child in value.items():
                if key.lower() in forbidden:
                    raise PilotDataError("LEAK_FIELD", key)
                reject_hidden(child)
        elif isinstance(value, list):
            for child in value:
                reject_hidden(child)

    reject_hidden(record)
    if (any(record.get(key) != source[key] for key in ("source_id", "family", "seed"))
            or record.get("state_id") != f"{source['source_id']}:{record.get('capture_index')}"):
        raise PilotDataError("SOURCE_IDENTITY", "Sample identity differs from source")
    payload = record["observation"]
    if record["observation_sha256"] != sha256_json(payload):
        raise PilotDataError("OBSERVATION_HASH", "Sample hash differs")
    Observation.model_validate(payload)
    content = {key: value for key, value in payload.items() if key not in {"run_id", "policy_id"}}
    content_hash = sha256_json(content)
    if record["state_id"] in state_ids or content_hash in content_hashes:
        raise PilotDataError("DUPLICATE_STATE", "Repeated state identity or observation content")
    state_ids.add(record["state_id"])
    content_hashes.add(content_hash)


def generate_pilot(config_path: Path, output_dir: Path) -> dict[str, object]:
    """Publish bounded, untrained pilot evidence only after integrity verification."""
    output = Path(output_dir).absolute()
    staging = None
    prefix = f".{output.name}.pilot-"
    try:
        _check_destination(output)
        config_path = Path(config_path).resolve()
        config_bytes = config_path.read_bytes()
        config = _load_config(config_bytes)
        teacher_path = Path(config["teacher_config_path"])
        if not teacher_path.is_absolute():
            teacher_path = ROOT / teacher_path
        teacher_path = teacher_path.resolve()
        teacher_bytes = teacher_path.read_bytes()
        teacher_config = json.loads(teacher_bytes)
        teacher = TeacherConfig.model_validate(teacher_config)
        if teacher.version != config["teacher_version"]:
            raise PilotDataError("INVALID_CONFIG", "Teacher version differs")
        teacher_sha = _sha256(teacher_bytes)
        # engine.step also dispatches to r3_engine; bind its transitive simulator
        # helpers as well as the common policy planning used by the teacher.
        code_paths = [Path(__file__).resolve(), ROOT / "training/pilot_scenarios.py",
                      ROOT / "backend/policies/teacher.py", ROOT / "backend/policies/common.py",
                      ROOT / "backend/contracts.py",
                      *sorted((ROOT / "backend/simulator").glob("*.py"))]
        frozen = {config_path: config_bytes, teacher_path: teacher_bytes,
                  **{path: path.read_bytes() for path in code_paths}}
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=prefix, dir=output.parent))
        paths = write_source_protocol(staging, split_seed=config["split_seed"])
        protocol_bytes = {path: path.read_bytes() for path in paths.values()}
        sources = [json.loads(line) for line in paths["sources"].read_text(encoding="utf-8").splitlines()]
        split_manifest = json.loads(paths["splits"].read_bytes())
        source_ids = [source["source_id"] for source in sources]
        split_by_source = {}
        for split, ids in split_manifest["splits"].items():
            if split not in config["split_counts"] or len(ids) != config["split_counts"][split]:
                raise PilotDataError("SOURCE_SPLITS", "Wrong split counts")
            for source_id in ids:
                if source_id in split_by_source:
                    raise PilotDataError("SOURCE_SPLITS", "Duplicate split membership")
                split_by_source[source_id] = split
        if (len(sources) != 30 or len(set(source_ids)) != 30
                or set(source_ids) != set(split_by_source)):
            raise PilotDataError("SOURCE_SPLITS", "Incomplete or duplicate source identities")
        attempts, failures, attempted_sources = [], [], set()
        state_ids, content_hashes = set(), set()
        integrity_failure_count = 0
        limited_count = 0
        stop_reason = None
        started = process_time()
        for source in sorted(sources, key=lambda row: row["source_id"]):
            if process_time() - started >= config["cpu_budget_s"]:
                stop_reason = "CPU_BUDGET"
                break
            attempted_sources.add(source["source_id"])
            try:
                records = sample_source(source)
            except Exception as error:
                failures.append({"source_id": source["source_id"], "code": getattr(error, "code", "SAMPLING_FAILED")})
                attempts.append({"source_id": source["source_id"], "split": split_by_source[source["source_id"]],
                                 "solver_status": "ERROR", "gap": None, "label_eligible": False,
                                 "exclusion_reasons": [getattr(error, "code", "SAMPLING_FAILED")]})
                continue
            for record in sorted(records, key=lambda row: row["capture_index"]):
                if process_time() - started >= config["cpu_budget_s"]:
                    stop_reason = "CPU_BUDGET"
                    break
                record = {**record, "split": split_by_source[source["source_id"]]}
                capture = record.get("capture_index")
                capture = capture if type(capture) is int else None
                # Error evidence is built from trusted identity and validated
                # public fields only, never by expanding an untrusted record.
                safe_record = {
                    "source_id": source["source_id"], "family": source["family"],
                    "seed": source["seed"], "capture_index": capture,
                    "state_id": f"{source['source_id']}:{capture}",
                    "split": split_by_source[source["source_id"]],
                }
                try:
                    _check_record(record, source, state_ids, content_hashes)
                    public_payload = Observation.model_validate(record["observation"]).model_dump(mode="json")
                    safe_record["observation"] = public_payload
                    safe_record["observation_sha256"] = sha256_json(public_payload)
                    labelled = label_state(record, teacher_config=teacher_config,
                                           teacher_config_sha256=teacher_sha, budget_ms=1000)
                except Exception as error:
                    code = getattr(error, "code", "LABEL_FAILED")
                    if isinstance(error, PilotDataError):
                        integrity_failure_count += 1
                    labelled = {**safe_record, "solver_status": "ERROR", "gap": None,
                                "label_eligible": False, "exclusion_reasons": [code],
                                "teacher_version": teacher.version, "teacher_config_sha256": teacher_sha,
                                "diagnostics": {"error_type": type(error).__name__, "code": code}}
                attempts.append(labelled)
                if labelled["solver_status"] in {"TIME_LIMIT_FEASIBLE", "NODE_LIMIT_FEASIBLE"}:
                    limited_count += 1
                if limited_count >= config["limited_result_stop_count"]:
                    stop_reason = "REPEATED_SOLVER_LIMIT"
                    break
            if stop_reason:
                break
        cpu_elapsed = process_time() - started
        if cpu_elapsed >= config["cpu_budget_s"] and stop_reason is None:
            stop_reason = "CPU_BUDGET"
        samples, diagnostics = partition_attempts(attempts)
        ready = (len(attempted_sources) == 30 and 60 <= len(samples) <= 120
                 and not failures and not any(row["solver_status"] == "ERROR" for row in attempts)
                 and stop_reason is None)
        summary = {
            "status": "ready_for_audit" if ready else "blocked", "training_enabled": False,
            "sources_attempted": len(attempted_sources), "total": len(attempts),
            "eligible": len(samples), "ineligible": len(diagnostics),
            "stop_reason": stop_reason, "limited_result_count": limited_count,
            "cpu_elapsed_s": cpu_elapsed, "failures": failures,
            "integrity_failure_count": integrity_failure_count,
            "solver_status_counts": dict(sorted(Counter(row["solver_status"] for row in attempts).items())),
            "exclusion_reason_counts": dict(sorted(Counter(
                reason for row in diagnostics for reason in row.get("exclusion_reasons", [row["solver_status"]])
            ).items())),
        }
        contents = {name: "".join(canonical_json(row) + "\n" for row in rows)
                    for name, rows in [("attempts.jsonl", attempts), ("samples.jsonl", samples),
                                       ("diagnostics.jsonl", diagnostics)]}
        contents["summary.json"] = canonical_json(summary) + "\n"
        for name, value in contents.items():
            (staging / name).write_text(value, encoding="utf-8", newline="\n")
        expected_bytes = {**{path.name: raw for path, raw in protocol_bytes.items()},
                          **{name: value.encode("utf-8") for name, value in contents.items()}}
        manifest = {
            "schema_version": "pilot-manifest-v1", "dataset_version": config["dataset_version"],
            "training_enabled": False, "teacher_version": teacher.version,
            "teacher_config_sha256": teacher_sha, "budget_ms": 1000,
            "cpu_budget_s": 7200, "config_sha256": _sha256(frozen[config_path]),
            "code_sha256": {path.relative_to(ROOT).as_posix(): _sha256(frozen[path]) for path in code_paths},
            "output_sha256": {name: _sha256(raw) for name, raw in expected_bytes.items()},
            "file_row_counts": {name: len(raw.splitlines()) for name, raw in expected_bytes.items()},
        }
        manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
        (staging / "manifest.json").write_bytes(manifest_bytes)
        expected_bytes["manifest.json"] = manifest_bytes
        for name, expected in expected_bytes.items():
            raw = (staging / name).read_bytes()
            if raw != expected or (name != "manifest.json" and _sha256(raw) != manifest["output_sha256"][name]):
                raise PilotDataError("OUTPUT_VERIFICATION_FAILED", name)
            for line in raw.decode("utf-8").splitlines():
                json.loads(line)
        for path, raw in frozen.items():
            if path.read_bytes() != raw:
                code = "CONFIG_CHANGED" if path in {teacher_path, config_path} else "CODE_CHANGED"
                raise PilotDataError(code, str(path))
        _check_destination(output)
        if output.exists():
            output.rmdir()
        staging.rename(output)
        staging = None
        return summary
    except PilotDataError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise PilotDataError("GENERATION_FAILED", str(error)) from error
    finally:
        if (staging is not None and staging.parent.resolve() == output.parent.resolve()
                and staging.name.startswith(prefix) and not staging.is_symlink()
                and not staging.is_junction()):
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = generate_pilot(args.config, args.output)
    except PilotDataError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(canonical_json(summary))
    return 0 if summary["status"] == "ready_for_audit" else 1


if __name__ == "__main__":
    raise SystemExit(main())
