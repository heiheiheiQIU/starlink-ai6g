import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.contracts import Action, Observation
from backend.simulator.engine import create_state, step
from training.generate_policy_pilot import PilotDataError, admit_state, sample_source
from training.pilot_scenarios import build_sources, sha256_json


def test_only_optimal_zero_gap_records_enter_samples():
    from training.generate_policy_pilot import partition_attempts
    attempts = [
        dict(state_id="a", solver_status="OPTIMAL", gap=0.0, label_eligible=True),
        dict(state_id="b", solver_status="TIME_LIMIT_FEASIBLE", gap=0.5, label_eligible=False),
        dict(state_id="c", solver_status="UNSUPPORTED_LOSS", gap=None, label_eligible=False),
        dict(state_id="d", solver_status="OPTIMAL", gap=0.1, label_eligible=True),
    ]
    samples, diagnostics = partition_attempts(attempts)
    assert [r["state_id"] for r in samples] == ["a"]
    assert [r["state_id"] for r in diagnostics] == ["b", "c", "d"]


def test_publication_refuses_nonempty_destination(tmp_path):
    from training.generate_policy_pilot import generate_pilot
    output = tmp_path / "out"
    output.mkdir()
    (output / "keep.txt").write_text("user data", encoding="utf-8")
    with pytest.raises(PilotDataError, match="OUTPUT_NOT_EMPTY"):
        generate_pilot(Path("missing-config.json"), output)
    assert (output / "keep.txt").read_text() == "user data"


def test_real_labels_are_stable_without_runtime_timing():
    from training.generate_policy_pilot import label_state
    teacher_path = Path(__file__).resolve().parents[1] / "configs/teacher.json"
    config = json.loads(teacher_path.read_bytes())
    record = {**sample_source(build_sources()[24])[0], "split": "test"}
    kwargs = dict(teacher_config=config,
                  teacher_config_sha256=hashlib.sha256(teacher_path.read_bytes()).hexdigest(),
                  budget_ms=1000)
    first, second = label_state(record, **kwargs), label_state(record, **kwargs)
    for key in ("source_id", "split", "solver_status", "candidate_scores", "gap", "label_content_sha256"):
        assert first[key] == second[key]
    stable = {k: v for k, v in first.items() if k not in {"elapsed_ms", "label_content_sha256"}}
    assert first["label_content_sha256"] == sha256_json(stable)
    assert all("elapsed_ms" not in c for c in first["diagnostics"].get("candidates", []))


@pytest.fixture
def pilot_run(tmp_path, monkeypatch):
    import training.generate_policy_pilot as pilot
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/policy_pilot.json").read_bytes())
    teacher = tmp_path / "teacher.json"
    teacher.write_bytes((root / "configs/teacher.json").read_bytes())
    config["teacher_config_path"] = str(teacher)
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    calls = []

    def label(record, **kwargs):
        calls.append(record)
        return {**record, "solver_status": "OPTIMAL", "gap": 0.0, "label_eligible": True}

    monkeypatch.setattr(pilot, "label_state", label, raising=False)
    return pilot, path, teacher, calls


def test_package_freezes_splits_and_verifies_all_advertised_hashes(pilot_run, tmp_path):
    pilot, path, _, calls = pilot_run
    output = tmp_path / "out"
    summary = pilot.generate_pilot(path, output)
    assert summary["status"] == "ready_for_audit"
    assert summary["sources_attempted"] == 30
    assert 60 <= summary["eligible"] <= 120
    assert summary["training_enabled"] is False
    splits = json.loads((output / "source_splits.json").read_bytes())["splits"]
    assert all(row["source_id"] in splits[row["split"]] for row in calls)
    manifest = json.loads((output / "manifest.json").read_bytes())
    assert set(manifest["output_sha256"]) == {"sources.jsonl", "source_splits.json", "attempts.jsonl", "samples.jsonl", "diagnostics.jsonl", "summary.json"}
    for name, expected in manifest["output_sha256"].items():
        raw = (output / name).read_bytes()
        assert b"\r" not in raw
        assert hashlib.sha256(raw).hexdigest() == expected


def test_cpu_budget_publishes_completed_evidence(pilot_run, monkeypatch, tmp_path):
    pilot, path, _, calls = pilot_run
    ticks = iter([0.0, 0.0, 0.0, 7201.0])
    monkeypatch.setattr(pilot, "process_time", lambda: next(ticks, 7201.0), raising=False)
    summary = pilot.generate_pilot(path, tmp_path / "out")
    assert summary["status"] == "blocked"
    assert summary["stop_reason"] == "CPU_BUDGET"
    assert len(calls) == 1


def test_solver_limit_count_is_cumulative(pilot_run, monkeypatch, tmp_path):
    pilot, path, _, _ = pilot_run
    statuses = iter(["TIME_LIMIT_FEASIBLE", "OPTIMAL", "NODE_LIMIT_FEASIBLE", "OPTIMAL", "TIME_LIMIT_FEASIBLE"])

    def label(record, **kwargs):
        status = next(statuses)
        return {**record, "solver_status": status, "gap": 0.0 if status == "OPTIMAL" else 0.5,
                "label_eligible": status == "OPTIMAL"}

    monkeypatch.setattr(pilot, "label_state", label)
    output = tmp_path / "out"
    summary = pilot.generate_pilot(path, output)
    assert summary["stop_reason"] == "REPEATED_SOLVER_LIMIT"
    assert summary["limited_result_count"] == 3
    assert summary["total"] == 5
    assert len((output / "diagnostics.jsonl").read_text().splitlines()) == 3


def test_changed_teacher_config_blocks_publication_and_cleans_staging(pilot_run, monkeypatch, tmp_path):
    pilot, path, teacher, _ = pilot_run

    def label(record, **kwargs):
        teacher.write_bytes(teacher.read_bytes() + b"\n")
        return {**record, "solver_status": "OPTIMAL", "gap": 0.0, "label_eligible": True}

    monkeypatch.setattr(pilot, "label_state", label)
    output = tmp_path / "out"
    with pytest.raises(PilotDataError, match="CONFIG_CHANGED"):
        pilot.generate_pilot(path, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".out.pilot-*"))


def test_teacher_exceptions_are_retained_as_diagnostics(pilot_run, monkeypatch, tmp_path):
    pilot, path, _, _ = pilot_run
    monkeypatch.setattr(pilot, "label_state", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("solver broke")))
    output = tmp_path / "out"
    summary = pilot.generate_pilot(path, output)
    assert summary["status"] == "blocked"
    attempts = [json.loads(line) for line in (output / "attempts.jsonl").read_text().splitlines()]
    assert attempts and all(row["solver_status"] == "ERROR" for row in attempts)
    assert (output / "samples.jsonl").read_bytes() == b""
    assert (output / "diagnostics.jsonl").read_bytes() == (output / "attempts.jsonl").read_bytes()


def test_candidate_and_total_timings_do_not_affect_stable_hash(monkeypatch):
    import training.generate_policy_pilot as pilot
    from backend.contracts import TeacherCandidateScore, TeacherResult
    timing = iter([1.0, 9.0])

    def teacher(observation, budget_ms, *, config, diagnostics):
        elapsed = next(timing)
        diagnostics.update(teacher_version="bounded-forecast-r4-v1",
                           candidates=[{"elapsed_ms": elapsed, "nodes": 1}])
        candidates = [TeacherCandidateScore(task_id=t.task_id, mode=m, score=0.0, feasible=False)
                      for t in observation.tasks for m in ("robust", "fast")]
        candidates.append(TeacherCandidateScore(task_id=None, mode="idle", score=0.0, feasible=True))
        return TeacherResult(candidate_scores=candidates, solver_status="OPTIMAL", gap=0.0, elapsed_ms=elapsed)

    monkeypatch.setattr(pilot, "solve_teacher", teacher)
    row = {**sample_source(build_sources()[0])[0], "split": "train"}
    first = pilot.label_state(row, teacher_config={}, teacher_config_sha256="frozen", budget_ms=1000)
    second = pilot.label_state(row, teacher_config={}, teacher_config_sha256="frozen", budget_ms=1000)
    assert first["elapsed_ms"] != second["elapsed_ms"]
    assert first["label_content_sha256"] == second["label_content_sha256"]


@pytest.mark.parametrize("mutation", ["hash", "duplicate", "source_id", "hidden"])
def test_sampling_integrity_failures_block_readiness(pilot_run, monkeypatch, tmp_path, mutation):
    pilot, path, _, calls = pilot_run
    original = pilot.sample_source

    def sample(source):
        rows = original(source)
        if mutation == "hash":
            rows[0]["observation_sha256"] = "bad"
        elif mutation == "duplicate":
            rows[1] = copy.deepcopy(rows[0])
        elif mutation == "source_id":
            rows[0]["source_id"] = "other"
        else:
            rows[0]["observation"]["evaluation_truth"] = {}
            rows[0]["observation_sha256"] = sha256_json(rows[0]["observation"])
        return rows

    monkeypatch.setattr(pilot, "sample_source", sample)
    summary = pilot.generate_pilot(path, tmp_path / "out")
    assert summary["status"] == "blocked"
    assert summary["eligible"] < summary["total"]
    assert summary["integrity_failure_count"] > 0


def test_source_protocol_change_during_generation_blocks_publication(pilot_run, monkeypatch, tmp_path):
    pilot, path, _, _ = pilot_run
    original = pilot.label_state

    def label(record, **kwargs):
        source_path = next(tmp_path.glob(".out.pilot-*/sources.jsonl"))
        source_path.write_bytes(source_path.read_bytes() + b"\n")
        return original(record, **kwargs)

    monkeypatch.setattr(pilot, "label_state", label)
    with pytest.raises(PilotDataError, match="OUTPUT_VERIFICATION_FAILED"):
        pilot.generate_pilot(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("key,value", [("training_enabled", True), ("cpu_budget_s", 7201), ("teacher_budget_ms", 999)])
def test_frozen_config_fields_are_validated(pilot_run, tmp_path, key, value):
    pilot, path, _, calls = pilot_run
    config = json.loads(path.read_bytes())
    config[key] = value
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(PilotDataError, match="INVALID_CONFIG"):
        pilot.generate_pilot(path, tmp_path / "out")
    assert calls == []


@pytest.mark.parametrize("status,exit_code", [("ready_for_audit", 0), ("blocked", 1)])
def test_cli_generates_package_and_reports_readiness(monkeypatch, capsys, status, exit_code):
    import training.generate_policy_pilot as pilot
    import sys
    monkeypatch.setattr(sys, "argv", ["pilot", "--config", "pilot.json", "--output", "package"])
    calls = []
    monkeypatch.setattr(pilot, "generate_pilot", lambda config, output: calls.append((config, output)) or {"status": status})
    assert pilot.main() == exit_code
    assert calls == [(Path("pilot.json"), Path("package"))]
    assert json.loads(capsys.readouterr().out) == {"status": status}


def test_sampling_uses_real_steps_and_preserves_source_identity():
    source = build_sources()[0]
    rows = sample_source(source)
    assert 2 <= len(rows) <= 4
    assert {row["source_id"] for row in rows} == {source["source_id"]}
    assert len({row["observation"]["sim_time_s"] for row in rows}) >= 2


@pytest.mark.parametrize("mutation", ["inflight", "retry", "pending"])
def test_admission_rejects_unresolved_private_protocol_state(mutation):
    source = build_sources()[0]
    state = create_state(source["scenario"], run_id=source["source_id"], policy_id="pilot")
    advanced = step(state, Action.model_validate(source["evolution_steps"][0]["action"]), 2.0).next_state
    if mutation == "inflight":
        state = advanced
    elif mutation == "retry":
        state.protocol_state.retry_required_key = ("T00", 0)
    else:
        state.protocol_state.pending.append(copy.deepcopy(advanced.protocol_state.pending[0]))
    with pytest.raises(PilotDataError, match="SOURCE_PROTOCOL_STATE") as error:
        admit_state(state)
    assert error.value.code == "SOURCE_PROTOCOL_STATE"


def test_records_are_public_observations_with_block_aligned_partial_delivery():
    forbidden = {"protocol_state", "true_windows", "future_arrivals", "energy_true_Wh", "evaluation_truth"}

    def check_keys(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    rows = [row for source in build_sources() for row in sample_source(source)]
    assert any(row["observation"]["sim_time_s"] > 0 for row in rows)
    partial = False
    for row in rows:
        check_keys(row)
        observation = Observation.model_validate(row["observation"])
        assert row["observation_sha256"] == sha256_json(row["observation"])
        for task in observation.tasks:
            assert task.remaining_bytes > 0
            assert (task.payload_bytes - task.remaining_bytes) % 1024 == 0
            partial |= task.remaining_bytes < task.payload_bytes
    assert partial


def test_sampling_is_deterministic_and_records_have_only_public_fields():
    source = build_sources()[0]
    rows = sample_source(source)
    assert rows == sample_source(source)
    assert len({row["state_id"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == {"source_id", "family", "seed", "capture_index", "state_id", "observation", "observation_sha256"}
        assert row["seed"] == source["seed"]
        assert row["family"] == source["family"]


@pytest.mark.parametrize("captures", [[0], [0, 1, 2, 3, 4]])
def test_capture_count_is_enforced(captures):
    source = copy.deepcopy(build_sources()[1])
    source["capture_after_steps"] = captures
    if len(captures) > 4:
        source["evolution_steps"] *= 2
    with pytest.raises(PilotDataError, match="CAPTURE_COUNT"):
        sample_source(source)


@pytest.mark.parametrize("mutation,code", [
    ("health", "FUTURE_HEALTH"),
    ("task", "FUTURE_TASK"),
    ("robust_loss_prob", "UNSUPPORTED_LOSS"),
    ("fast_loss_prob", "UNSUPPORTED_LOSS"),
])
def test_admission_rejects_unsupported_public_observation(monkeypatch, mutation, code):
    from backend.simulator.engine import observe

    source = build_sources()[0]
    state = create_state(source["scenario"], run_id=source["source_id"], policy_id="pilot")
    observation = observe(state).model_copy(deep=True)
    if mutation == "health":
        observation.health.available_at_s = observation.sim_time_s + 1
    elif mutation == "task":
        observation.tasks[0].arrival_s = observation.sim_time_s + 1
    else:
        setattr(observation.forecast_windows[0].loss_profile[0], mutation, 0.1)
    monkeypatch.setattr("training.generate_policy_pilot.observe", lambda _: observation)
    with pytest.raises(PilotDataError, match=code) as error:
        admit_state(state)
    assert error.value.code == code
