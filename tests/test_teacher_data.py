"""Independent teacher labels over the frozen public H02 observations."""

import json
import math
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

import training.generate_teacher_data as module
from training.generate_teacher_data import (
    TeacherDataError, canonical_json, generate_record, label_content_sha256, sha256_text,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "cccca9892086522624a5979216d7a2ab73209803"
TEACHER_CONFIG = ROOT / "configs/teacher.json"


def first_source():
    with (ROOT / "docs/evidence/B/H02_2026-10-29/samples.jsonl").open(encoding="utf-8") as stream:
        return json.loads(next(stream))


def generate(source):
    return generate_record(source, source_revision=SOURCE_REVISION,
                           budget_ms=1000, teacher_config_path=TEACHER_CONFIG)


def test_generate_record_recomputes_first_h02_label():
    source = first_source()
    before = canonical_json(source["observation"])
    record = generate(source)
    assert record["sample_id"] == source["sample_id"]
    assert record["scenario_id"] == source["observation"]["run_id"]
    assert record["state_id"] == source["sample_id"]
    assert record["solver_status"] == "OPTIMAL"
    assert record["gap"] == 0.0
    assert record["label_eligible"] is True
    assert record["exclusion_reasons"] == []
    assert record["observation"] == source["observation"]
    score_by_key = {(item["task_id"], item["mode"]): item
                    for item in record["candidate_scores"]}
    assert len(score_by_key) == len(record["candidate_scores"])
    assert score_by_key[("T1", "fast")]["score"] == 1.0
    assert score_by_key[("T1", "fast")]["feasible"] is True
    assert score_by_key[("T1", "robust")]["feasible"] is False
    assert all(math.isfinite(item["score"]) for item in record["candidate_scores"])
    assert math.isfinite(record["gap"])
    assert canonical_json(source["observation"]) == before
    assert record["label_content_sha256"] == label_content_sha256(record)
    assert record["teacher_version"] == "bounded-forecast-r4-v1"
    assert record["teacher_config_sha256"] == hashlib.sha256(TEACHER_CONFIG.read_bytes()).hexdigest()
    assert record["source_observation_sha256"] == sha256_text(before)
    assert record["source_revision"] == SOURCE_REVISION
    assert math.isfinite(record["elapsed_ms"])


def test_canonical_utf8_hash_and_stable_field_selection():
    assert canonical_json({"z": 1, "a": "中文"}) == '{"a":"中文","z":1}'
    assert sha256_text("中文") == hashlib.sha256("中文".encode("utf-8")).hexdigest()
    record = generate(first_source())
    expected_fields = (
        "sample_id", "scenario_id", "state_id", "source_revision",
        "source_observation_sha256", "observation", "teacher_version",
        "teacher_config_sha256", "candidate_scores", "solver_status",
        "gap", "diagnostics", "label_eligible", "exclusion_reasons",
    )
    expected = sha256_text(canonical_json({key: record[key] for key in expected_fields}))
    record.update(elapsed_ms=9999.0, generated_at="tomorrow", output_path="elsewhere",
                  label_content_sha256="ignored")
    assert label_content_sha256(record) == expected


def test_repeated_solve_has_stable_label_content_hash():
    left = generate(first_source())
    right = generate(first_source())
    assert left["label_content_sha256"] == right["label_content_sha256"]


@pytest.mark.parametrize("key", [
    "TRUE_CAPACITY", "Capacity_True_Wh", "future_arrivals", "actual_future_loss",
    "evaluation_truth", "Energy_True_Wh", "soc_true",
])
@pytest.mark.parametrize("nested", [False, True])
def test_rejects_hidden_truth_inside_observation(key, nested):
    source = first_source()
    if nested:
        source["observation"]["tasks"][0]["metadata"] = [{key: 1}]
    else:
        source["observation"][key] = 1
    with pytest.raises(TeacherDataError) as error:
        generate(source)
    assert error.value.code == "LEAK_FIELD"


def test_source_envelope_labels_and_truth_are_ignored():
    source = first_source()
    source.update(candidate_scores="obsolete", scenario_id="wrong", solver_status="wrong",
                  gap=float("nan"), elapsed_ms=-1, teacher_version="wrong",
                  evaluation_truth={"soc_true": 1})
    record = generate(source)
    assert record["solver_status"] == "OPTIMAL"
    assert record["scenario_id"] == source["observation"]["run_id"]
    assert record["candidate_scores"][1]["score"] == 1.0


@pytest.mark.parametrize("malformation", ["duplicate", "nan_score", "inf_score", "nan_gap", "inf_gap", "mutation"])
def test_rejects_malformed_solver_returns(monkeypatch, malformation):
    real_solver = module.solve_teacher

    def malformed(observation, **kwargs):
        result = real_solver(observation, **kwargs)
        if malformation == "duplicate":
            result.candidate_scores.append(result.candidate_scores[0])
        elif malformation.endswith("score"):
            result.candidate_scores[0].score = float(malformation.split("_")[0])
        elif malformation.endswith("gap"):
            result.gap = float(malformation.split("_")[0])
        else:
            observation.tasks[0].priority_weight += 1.0
        return result

    monkeypatch.setattr(module, "solve_teacher", malformed)
    with pytest.raises(TeacherDataError) as error:
        generate(first_source())
    expected = "OBSERVATION_MUTATED" if malformation == "mutation" else "INVALID_TEACHER_RESULT"
    assert error.value.code == expected


def test_non_optimal_real_result_is_retained_and_excluded():
    source = first_source()
    source["observation"]["forecast_windows"][0]["loss_profile"][0]["fast_loss_prob"] = 0.1
    record = generate(source)
    assert record["solver_status"] == "UNSUPPORTED_LOSS"
    assert record["gap"] is None
    assert record["label_eligible"] is False
    assert record["exclusion_reasons"]
    assert record["candidate_scores"]


SOURCE = ROOT / "docs/evidence/B/H02_2026-10-29/samples.jsonl"


def batch(output, source=SOURCE, **kwargs):
    options = dict(source_path=source, output_dir=output, source_revision=SOURCE_REVISION,
                   teacher_config_path=TEACHER_CONFIG, budget_ms=1000, expected_count=20)
    options.update(kwargs)
    return module.generate_teacher_dataset(**options)


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def cli_args(source, output, revision=SOURCE_REVISION):
    return ["--source", str(source), "--output", str(output), "--source-revision", revision,
            "--teacher-config", str(TEACHER_CONFIG), "--budget-ms", "1000",
            "--expected-count", "20"]


def test_batch_consumes_twenty_real_observations_and_manifest(tmp_path, monkeypatch):
    calls = []
    real_solver = module.solve_teacher

    def spy(observation, **kwargs):
        calls.append(observation.model_dump(mode="json"))
        return real_solver(observation, **kwargs)

    monkeypatch.setattr(module, "solve_teacher", spy)
    output = tmp_path / "dataset"
    source = tmp_path / "reversed.jsonl"
    source.write_text("\n".join(canonical_json(row) for row in reversed(read_rows(SOURCE))) + "\n",
                      encoding="utf-8")
    summary = batch(output, source)
    rows = read_rows(output / "samples.jsonl")
    sources = read_rows(SOURCE)
    assert len(sources) == len(rows) == len(calls) == 20
    assert {r["sample_id"] for r in rows} == {r["sample_id"] for r in sources}
    assert {r["scenario_id"] for r in rows} == {r["observation"]["run_id"] for r in sources}
    assert calls == [r["observation"] for r in rows]
    assert [r["observation"] for r in rows] == [r["observation"] for r in sorted(
        sources, key=lambda r: (r["observation"]["run_id"], r["sample_id"]))]
    assert [(r["scenario_id"], r["sample_id"]) for r in rows] == sorted(
        (r["scenario_id"], r["sample_id"]) for r in rows)
    assert all(r["solver_status"] == "OPTIMAL" and r["gap"] == 0 and r["label_eligible"] for r in rows)
    assert summary == json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "ready_for_split"
    assert summary["total"] == summary["eligible"] == 20
    assert summary["failures"] == summary["ineligible"] == 0
    assert summary["solver_status_counts"] == {"OPTIMAL": 20}
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_revision"] == SOURCE_REVISION
    assert manifest["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["teacher_config_sha256"] == hashlib.sha256(TEACHER_CONFIG.read_bytes()).hexdigest()
    assert manifest["teacher_version"] == "bounded-forecast-r4-v1"
    assert manifest["budget_ms"] == 1000
    assert manifest["schema_versions"] == {"observation": "1.0", "teacher_record": "1.0", "manifest": "1.0"}
    assert manifest["file_row_counts"] == {"source": 20, "samples.jsonl": 20, "summary.json": 1}
    assert manifest["command"][:3] == ["python", "-m", "training.generate_teacher_data"]
    assert all(not Path(arg).is_absolute() for arg in manifest["command"])
    for filename in ("samples.jsonl", "summary.json"):
        raw = (output / filename).read_bytes()
        assert manifest["output_sha256"][filename] == hashlib.sha256(raw).hexdigest()
        assert raw.endswith(b"\n")
        assert all(line == canonical_json(json.loads(line)) for line in raw.decode("utf-8").splitlines())


@pytest.mark.parametrize("defect, code", [
    ("sample", "DUPLICATE_SAMPLE_ID"), ("scenario", "DUPLICATE_SCENARIO_ID"),
    ("count", "UNEXPECTED_COUNT"), ("dirty", "OUTPUT_NOT_EMPTY"),
    ("revision", "INVALID_SOURCE_REVISION"), ("leak", "LEAK_FIELD"),
])
def test_batch_rejects_bad_inputs_before_solving_or_publication(tmp_path, monkeypatch, defect, code):
    rows = read_rows(SOURCE)
    output = tmp_path / "dataset"
    options = {}
    if defect == "sample":
        rows[-1]["sample_id"] = rows[0]["sample_id"]
    elif defect == "scenario":
        rows[-1]["observation"]["run_id"] = rows[0]["observation"]["run_id"]
    elif defect == "count":
        rows.pop()
    elif defect == "dirty":
        output.mkdir()
        (output / "keep.txt").write_text("keep", encoding="utf-8")
    elif defect == "revision":
        options["source_revision"] = "HEAD"
    elif defect == "leak":
        rows[-1]["observation"]["tasks"][0]["metadata"] = {"soc_true": 1}
    source = tmp_path / "source.jsonl"
    source.write_text("\n".join(canonical_json(row) for row in rows) + "\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(module, "solve_teacher", lambda *a, **kw: calls.append(a))
    with pytest.raises(TeacherDataError) as error:
        batch(output, source, **options)
    assert error.value.code == code
    assert calls == []
    assert not (output / "manifest.json").exists()
    if defect == "dirty":
        assert (output / "keep.txt").read_text() == "keep"
    assert not list(tmp_path.glob(".dataset.*"))


def test_batch_retains_nonoptimal_and_exception_evidence(tmp_path, monkeypatch):
    real_solver = module.solve_teacher
    calls = 0

    def limited(observation, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("solver exploded")
        result = real_solver(observation, **kwargs)
        if calls == 1:
            result.solver_status = "TIME_LIMIT_FEASIBLE"
            result.gap = None
        return result

    monkeypatch.setattr(module, "solve_teacher", limited)
    output = tmp_path / "dataset"
    summary = batch(output)
    rows = read_rows(output / "samples.jsonl")
    assert calls == len(rows) == 20
    assert summary["status"] == "blocked"
    assert summary["eligible"] == 18 and summary["ineligible"] == 2 and summary["failures"] == 1
    assert summary["solver_status_counts"] == {"OPTIMAL": 18, "TIME_LIMIT_FEASIBLE": 1, "ERROR": 1}
    assert rows[0]["solver_status"] == "TIME_LIMIT_FEASIBLE"
    assert rows[0]["label_eligible"] is False and rows[0]["exclusion_reasons"]
    assert rows[1]["label_eligible"] is False
    assert rows[1]["error"] == {"code": "SAMPLE_GENERATION_FAILED", "message": "solver exploded"}
    assert rows[1]["observation"] == sorted(read_rows(SOURCE), key=lambda r: (
        r["observation"]["run_id"], r["sample_id"]))[1]["observation"]


def test_cli_ready_and_controlled_invalid_revision(tmp_path):
    output = tmp_path / "dataset"
    result = subprocess.run([sys.executable, "-m", "training.generate_teacher_data",
                             *cli_args(SOURCE, output)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (output / "manifest.json").exists()
    invalid = subprocess.run([sys.executable, "-m", "training.generate_teacher_data",
                              *cli_args(SOURCE, tmp_path / "bad", "HEAD")], cwd=ROOT,
                             capture_output=True, text=True)
    assert invalid.returncode != 0
    assert "INVALID_SOURCE_REVISION" in invalid.stderr and "Traceback" not in invalid.stderr
    assert not (tmp_path / "bad").exists()


def test_cli_blocked_writes_evidence_and_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate_teacher_data", *cli_args(SOURCE, tmp_path / "blocked")])
    real_solver = module.solve_teacher

    def limited(observation, **kwargs):
        result = real_solver(observation, **kwargs)
        result.solver_status = "TIME_LIMIT_FEASIBLE"
        result.gap = None
        return result

    monkeypatch.setattr(module, "solve_teacher", limited)
    assert module.main() != 0
    assert len(read_rows(tmp_path / "blocked" / "samples.jsonl")) == 20
    assert json.loads((tmp_path / "blocked" / "summary.json").read_text())["status"] == "blocked"


def test_batch_verifies_closed_staged_files_before_publication(tmp_path, monkeypatch):
    original = Path.read_bytes
    observed = []

    def corrupted_read(path):
        if path.name == "samples.jsonl" and path.parent.name.startswith(".dataset."):
            observed.append(path)
            assert {p.name for p in path.parent.iterdir()} == {
                "samples.jsonl", "summary.json", "manifest.json"}
            assert not (tmp_path / "dataset").exists()
            return b"corrupt\n"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", corrupted_read)
    with pytest.raises(TeacherDataError) as error:
        batch(tmp_path / "dataset")
    assert error.value.code == "OUTPUT_VERIFICATION_FAILED"
    assert len(observed) == 1
    assert not (tmp_path / "dataset").exists()
    assert not list(tmp_path.glob(".dataset.*"))


@pytest.mark.parametrize("field, flag", [("source_path", "--source"),
    ("teacher_config_path", "--teacher-config"), ("output_dir", "--output")])
@pytest.mark.parametrize("location", ["cross_volume", "outside_project"])
def test_batch_and_cli_reject_paths_outside_repository_before_io(
        tmp_path, monkeypatch, capsys, field, flag, location):
    other_drive = "C:" if ROOT.drive.upper() != "C:" else "D:"
    outside = (Path(other_drive + "/teacher-inputs/samples.jsonl") if location == "cross_volume"
               else ROOT.parent / "teacher-inputs" / "samples.jsonl")
    output = tmp_path / "dataset"
    options = dict(source_path=SOURCE, output_dir=output, source_revision=SOURCE_REVISION,
                   teacher_config_path=TEACHER_CONFIG, budget_ms=1000, expected_count=20)
    options[field] = outside
    calls = []

    def unexpected_io(*args, **kwargs):
        calls.append(args)
        raise AssertionError("Rejected paths must fail before input reads, solving, or staging")

    monkeypatch.setattr(module, "solve_teacher", unexpected_io)
    monkeypatch.setattr(module.tempfile, "mkdtemp", unexpected_io)
    monkeypatch.setattr(Path, "read_bytes", unexpected_io)
    with pytest.raises(TeacherDataError) as error:
        module.generate_teacher_dataset(**options)
    assert error.value.code == "PATH_OUTSIDE_PROJECT"
    assert str(error.value) == "PATH_OUTSIDE_PROJECT: Dataset paths must resolve inside the repository"
    args = cli_args(SOURCE, output)
    args[args.index(flag) + 1] = str(outside)
    monkeypatch.setattr(sys, "argv", ["generate_teacher_data", *args])
    assert module.main() == 2
    assert capsys.readouterr().err.strip() == str(error.value)
    assert calls == []
    assert not output.exists()
    assert not list(tmp_path.glob(".dataset.*"))
