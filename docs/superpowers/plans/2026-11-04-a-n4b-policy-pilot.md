# A-N4b Policy Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, source-grouped A-N4b pilot that produces 60–120 auditable teacher-labelled public observations without changing the frozen A-N3 data or starting model training.

**Architecture:** A source protocol module creates 30 deterministic R3 trajectories and freezes an 18/6/6 source split before sampling. A generator advances the existing simulator, admits only protocol-clean public observations, labels them with the existing teacher, and atomically publishes eligible and diagnostic records. A separate auditor verifies hashes, split inheritance, content uniqueness, support coverage, and label quality.

**Tech Stack:** Python 3.12, Pydantic contracts, existing R3 simulator and teacher, pytest, JSON/JSONL with UTF-8 and LF.

## Global Constraints

- Work only on `codex/a-n4b-pilot`, based on `f3c6938004283140bdaf5968f71df6d8be44483e`.
- Do not depend on PR #13 and do not modify `backend/contracts.py`, `backend/policies/teacher.py`, `backend/simulator/`, `backend/api/`, legacy files, frozen A-N3 data, or old training configuration.
- Use teacher version `bounded-forecast-r4-v1`, `budget_ms=1000`, zero data/ACK loss, and the unchanged `configs/teacher.json`.
- Freeze 30 sources into 18/6/6 train/validation/test groups before state sampling.
- Admit only states with no inflight block, no retry requirement, no pending protocol event, no future task exposure, and a currently available health estimate.
- Only `OPTIMAL + gap=0` records are label-eligible; every other result remains diagnostic evidence.
- Stop at 2 CPU hours or repeated TIME/NODE limits; do not loosen the support domain to reach a count.
- Keep `training_enabled=false`; this plan does not train or publish a model.

---

## File Map

- Create `training/pilot_scenarios.py`: deterministic source construction, source hashes, and 18/6/6 split manifest.
- Create `training/generate_policy_pilot.py`: real state evolution, admission, teacher labelling, budget stop, and atomic publication.
- Create `training/audit_policy_pilot.py`: independent package verification and audit rendering.
- Create `configs/policy_pilot.json`: immutable pilot settings with training disabled.
- Create `tests/test_pilot_scenarios.py`: source protocol and split tests.
- Create `tests/test_generate_policy_pilot.py`: evolution, admission, routing, and publication tests.
- Create `tests/test_audit_policy_pilot.py`: package integrity, coverage, and semantic audit tests.
- Create `data/teacher/a_n4_pilot_v1/*`: generated pilot package only after code and targeted tests pass.
- Create `docs/handoffs/A_N4b_pilot_B_2026-11-04.md`: actual commands, hashes, counts, limits, and B acceptance request.

---

### Task 1: Deterministic source protocol and source-first split

**Files:**
- Create: `training/pilot_scenarios.py`
- Create: `configs/policy_pilot.json`
- Create: `tests/test_pilot_scenarios.py`

**Interfaces:**
- Consumes: `configs/scenarios/r3_normal.json`, `configs/teacher.json`.
- Produces: `build_sources() -> list[dict[str, object]]`, `build_source_splits(sources, *, split_seed, counts) -> dict[str, object]`, `write_source_protocol(output_dir, *, split_seed=20261104) -> dict[str, Path]`.

- [ ] **Step 1: Write failing protocol-shape and split tests**

```python
from training.pilot_scenarios import build_sources, build_source_splits

def test_sources_are_deterministic_unique_and_cover_declared_families():
    first = build_sources()
    second = build_sources()
    assert first == second
    assert len(first) == 30
    assert len({row["source_id"] for row in first}) == 30
    assert len({row["seed"] for row in first}) == 30
    assert not ({row["seed"] for row in first} & set(range(200000, 200180)))
    assert len({row["content_sha256"] for row in first}) == 30
    families = [row["family"] for row in first]
    assert families.count("decision") == 24
    assert families.count("low_energy") == 2
    assert families.count("no_window") == 2
    assert families.count("deadline_before_window") == 2

def test_source_split_is_source_first_complete_and_disjoint():
    sources = build_sources()
    manifest = build_source_splits(
        sources, split_seed=20261104, counts=(18, 6, 6)
    )
    assert manifest["counts"] == {"train": 18, "validation": 6, "test": 6}
    groups = [set(manifest["splits"][name]) for name in ("train", "validation", "test")]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3))
    assert set.union(*groups) == {row["source_id"] for row in sources}
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
python -m pytest tests/test_pilot_scenarios.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'training.pilot_scenarios'`.

- [ ] **Step 3: Implement the source protocol**

Implement these imports, constants, helpers, and public functions in
`training/pilot_scenarios.py`:

```python
import copy
import hashlib
import json
from pathlib import Path

from backend.contracts import Action
from backend.simulator.engine import ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
DATASET_VERSION = "a-n4-pilot-v1"
SOURCE_COUNT = 30
SOURCE_SEED_START = 410000
DEFAULT_SPLIT_SEED = 20261104
DEFAULT_SPLIT_COUNTS = (18, 6, 6)
IDLE = Action(
    task_id=None, mode="idle", scheduled_bytes=0,
    reason_codes=[], fallback=False,
).model_dump(mode="json")

def canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )

def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def _window(window_id: str, start_s: float, end_s: float) -> dict[str, object]:
    return {
        "window_id": window_id,
        "start_s": start_s,
        "end_s": end_s,
        "rate_profile": [{
            "time_s": start_s,
            "robust_bps": 8192.0,
            "fast_bps": 16384.0,
        }],
        "loss_profile": [{
            "time_s": start_s,
            "robust_loss_prob": 0.0,
            "fast_loss_prob": 0.0,
        }],
        "source": "synthetic",
        "forecast_version": "a-n4-pilot-forecast-v1",
    }

def _task(index: int, variant: int) -> dict[str, object]:
    payload = (1 + ((variant + index) % 4)) * 1024
    return {
        "task_id": f"T{index:02d}",
        "arrival_s": 0.0 if index == 0 else float(2 * (index % 2)),
        "deadline_s": float(8 + 4 * ((variant + index) % 6)),
        "payload_bytes": payload,
        "remaining_bytes": payload,
        "priority_weight": 1.0 + 0.5 * ((variant + index) % 5),
        "business_class": "synthetic",
        "data_location": "satellite_1",
    }

def _source(
    source_id: str, seed: int, family: str, *,
    energy_wh: float,
    tasks: list[dict[str, object]],
    windows: list[dict[str, object]],
    partial: bool,
) -> dict[str, object]:
    template = json.loads(
        (ROOT / "configs/scenarios/r3_normal.json").read_text(encoding="utf-8")
    )["scenario"]
    scenario = copy.deepcopy(template)
    scenario.update({
        "scenario_id": source_id,
        "initial_energy_Wh": energy_wh,
        "forecast_version": "a-n4-pilot-forecast-v1",
        "tasks": tasks,
        "true_windows": copy.deepcopy(windows),
        "forecast_windows": copy.deepcopy(windows),
    })
    ratio = energy_wh / 20.0
    scenario["health_observations"] = [{
        "soc_est": ratio,
        "soc_lower": ratio,
        "capacity_Wh_est": 20.0,
        "capacity_lower_Wh": 20.0,
        "energy_lower_Wh": energy_wh,
        "rul_est": None,
        "rul_unit": None,
        "uncertainty_method": "synthetic_exact_pilot",
        "model_version": "synthetic-a-n4-pilot-v1",
        "observed_at_s": 0.0,
        "available_at_s": 0.0,
        "reason_codes": ["RUL_UNAVAILABLE"],
    }]
    parsed = ScenarioConfig.model_validate(scenario).model_dump(mode="json")
    if partial:
        send = Action(
            task_id="T00", mode="robust", scheduled_bytes=1024,
            reason_codes=[], fallback=False,
        ).model_dump(mode="json")
        evolution = [
            {"dt_s": 2.0, "action": send},
            {"dt_s": 2.0, "action": IDLE},
        ]
        capture = [0, 2]
    else:
        evolution = [
            {"dt_s": 2.0, "action": IDLE},
            {"dt_s": 2.0, "action": IDLE},
        ]
        capture = [0, 1, 2] if family == "decision" else [0, 1]
    identity = copy.deepcopy(parsed)
    identity.pop("scenario_id")
    if isinstance(identity.get("channel"), dict):
        identity["channel"].pop("seed", None)
    return {
        "source_id": source_id,
        "seed": seed,
        "family": family,
        "scenario": parsed,
        "evolution_steps": evolution,
        "capture_after_steps": capture,
        "content_sha256": sha256_json(identity),
    }

def build_sources() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(24):
        count = 1 + index % 4
        tasks = [_task(task_index, index) for task_index in range(count)]
        partial = index % 4 == 0
        if partial:
            tasks[0] = {
                **tasks[0],
                "payload_bytes": 2048,
                "remaining_bytes": 2048,
            }
        windows = [
            _window(f"W{slot}", float(6 * slot), float(6 * slot + 6))
            for slot in range(1 + index % 3)
        ]
        rows.append(_source(
            f"decision_{index:02d}",
            SOURCE_SEED_START + index,
            "decision",
            energy_wh=(0.6, 1.2, 10.0)[index % 3],
            tasks=tasks,
            windows=windows,
            partial=partial,
        ))
    rows.extend([
        _source(
            "low_energy_00", 410024, "low_energy",
            energy_wh=0.49, tasks=[_task(0, 24)],
            windows=[_window("W0", 0.0, 6.0)], partial=False,
        ),
        _source(
            "low_energy_01", 410025, "low_energy",
            energy_wh=0.5309017777778, tasks=[_task(0, 25)],
            windows=[_window("W0", 0.0, 6.0)], partial=False,
        ),
        _source(
            "no_window_00", 410026, "no_window",
            energy_wh=1.2, tasks=[_task(0, 26)], windows=[], partial=False,
        ),
        _source(
            "no_window_01", 410027, "no_window",
            energy_wh=10.0, tasks=[_task(0, 27), _task(1, 27)],
            windows=[], partial=False,
        ),
        _source(
            "deadline_before_window_00", 410028, "deadline_before_window",
            energy_wh=1.2,
            tasks=[{**_task(0, 28), "deadline_s": 4.0}],
            windows=[_window("W0", 8.0, 14.0)], partial=False,
        ),
        _source(
            "deadline_before_window_01", 410029, "deadline_before_window",
            energy_wh=10.0,
            tasks=[{**_task(0, 29), "deadline_s": 6.0}],
            windows=[_window("W0", 10.0, 16.0)], partial=False,
        ),
    ])
    if len(rows) != SOURCE_COUNT:
        raise AssertionError("Pilot source count changed")
    return rows

def build_source_splits(
    sources: list[dict[str, object]], *,
    split_seed: int,
    counts: tuple[int, int, int],
) -> dict[str, object]:
    ordered = sorted(
        (str(row["source_id"]) for row in sources),
        key=lambda source_id: hashlib.sha256(
            f"{split_seed}:{source_id}".encode("utf-8")
        ).hexdigest(),
    )
    train, validation, test = counts
    if len(ordered) != sum(counts) or len(set(ordered)) != len(ordered):
        raise ValueError("Source IDs and split counts do not match")
    return {
        "schema_version": "pilot-source-splits-v1",
        "dataset_version": DATASET_VERSION,
        "split_seed": split_seed,
        "counts": {"train": train, "validation": validation, "test": test},
        "splits": {
            "train": ordered[:train],
            "validation": ordered[train:train + validation],
            "test": ordered[train + validation:],
        },
    }

def write_source_protocol(
    output_dir: Path, *, split_seed: int = DEFAULT_SPLIT_SEED
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("Source protocol output must be empty")
    sources = build_sources()
    splits = build_source_splits(
        sources, split_seed=split_seed, counts=DEFAULT_SPLIT_COUNTS
    )
    paths = {
        "sources": output_dir / "sources.jsonl",
        "splits": output_dir / "source_splits.json",
    }
    paths["sources"].write_text(
        "".join(canonical_json(row) + "\n" for row in sources),
        encoding="utf-8", newline="\n",
    )
    paths["splits"].write_text(
        canonical_json(splits) + "\n", encoding="utf-8", newline="\n"
    )
    return paths
```

Use these exact source rules:

- IDs are the four family prefixes above with two-digit indexes.
- Seeds are `410000..410029`.
- All scenarios validate through `ScenarioConfig.model_validate()`.
- All windows use zero loss and rates 8192/16384 bit/s.
- Decision sources rotate energies `0.6, 1.2, 10.0`, task counts `1..4`, payloads `1024..4096`, deadlines within 30 s, and one to three non-overlapping windows.
- Low-energy sources use `0.49` and `0.5309017777778` Wh.
- Partial-delivery sources include a send step followed by an idle step long enough to process ACK and timeout events before capture.
- `content_sha256` excludes `source_id`, `scenario_id`, and channel seed so renamed copies collide.

- [ ] **Step 4: Add the immutable pilot configuration**

Create `configs/policy_pilot.json` with exact keys:

```json
{
  "schema_version": "policy-pilot-config-v1",
  "dataset_version": "a-n4-pilot-v1",
  "output_path": "data/teacher/a_n4_pilot_v1",
  "source_count": 30,
  "split_seed": 20261104,
  "split_counts": {"train": 18, "validation": 6, "test": 6},
  "states_per_source_min": 2,
  "states_per_source_max": 4,
  "valid_state_min": 60,
  "valid_state_max": 120,
  "teacher_config_path": "configs/teacher.json",
  "teacher_version": "bounded-forecast-r4-v1",
  "teacher_budget_ms": 1000,
  "cpu_budget_s": 7200.0,
  "limited_result_stop_count": 3,
  "training_enabled": false
}
```

Extend the test to load this file and assert the dictionary exactly, including `training_enabled is False`.

- [ ] **Step 5: Run GREEN and commit**

Run:

```powershell
python -m pytest tests/test_pilot_scenarios.py -q
```

Expected: all tests pass.

Commit:

```powershell
git add training/pilot_scenarios.py configs/policy_pilot.json tests/test_pilot_scenarios.py
git commit -m "feat(A): define A-N4b pilot sources"
```

---

### Task 2: Real simulator evolution and protocol-clean admission

**Files:**
- Create: `training/generate_policy_pilot.py`
- Create: `tests/test_generate_policy_pilot.py`

**Interfaces:**
- Consumes: rows from `build_sources()`, `ScenarioConfig`, `create_state()`, `observe()`, `step()`.
- Produces: `admit_state(state) -> Observation`, `sample_source(source) -> list[dict[str, object]]`.

- [ ] **Step 1: Write failing admission and evolution tests**

```python
import copy
import pytest
from backend.contracts import Action
from backend.simulator.engine import create_state, step
from training.generate_policy_pilot import PilotDataError, admit_state, sample_source
from training.pilot_scenarios import build_sources

IDLE = Action(
    task_id=None, mode="idle", scheduled_bytes=0,
    reason_codes=[], fallback=False,
)

def test_sampling_uses_real_steps_and_preserves_source_identity():
    source = build_sources()[0]
    rows = sample_source(source)
    assert 2 <= len(rows) <= 4
    assert {row["source_id"] for row in rows} == {source["source_id"]}
    assert len({row["observation"]["sim_time_s"] for row in rows}) >= 2

@pytest.mark.parametrize("mutation", ["inflight", "retry", "pending"])
def test_admission_rejects_unresolved_private_protocol_state(mutation):
    source = next(row for row in build_sources() if row["family"] == "decision")
    state = create_state(source["scenario"], run_id=source["source_id"], policy_id="pilot")
    if mutation == "inflight":
        state = step(state, source["evolution_steps"][0]["action"], 2.0).next_state
    elif mutation == "retry":
        state.protocol_state.retry_required_key = ("T00", 0)
    else:
        state.protocol_state.pending.append(copy.deepcopy(
            step(state, source["evolution_steps"][0]["action"], 2.0)
            .next_state.protocol_state.pending[0]
        ))
    with pytest.raises(PilotDataError, match="SOURCE_PROTOCOL_STATE"):
        admit_state(state)
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_generate_policy_pilot.py -q
```

Expected: collection fails because `training.generate_policy_pilot` does not exist.

- [ ] **Step 3: Implement admission and sampling**

Implement:

```python
class PilotDataError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")

def admit_state(state: SimulatorState) -> Observation:
    protocol = state.protocol_state
    if (
        state.inflight is not None
        or protocol.retry_required_key is not None
        or protocol.pending
    ):
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

def sample_source(source: dict[str, object]) -> list[dict[str, object]]:
    state = create_state(
        source["scenario"], run_id=str(source["source_id"]), policy_id="pilot-source"
    )
    captured = []
    capture_steps = set(source["capture_after_steps"])
    if 0 in capture_steps:
        captured.append(_source_record(source, 0, admit_state(state)))
    for index, command in enumerate(source["evolution_steps"], start=1):
        result = step(
            state,
            Action.model_validate(command["action"]),
            float(command["dt_s"]),
        )
        state = result.next_state
        if index in capture_steps:
            captured.append(_source_record(source, index, admit_state(state)))
    if not 2 <= len(captured) <= 4:
        raise PilotDataError("CAPTURE_COUNT", "Each source needs 2..4 states")
    return captured
```

`_source_record` must store only `source_id`, `family`, `seed`, `capture_index`,
`state_id`, canonical Observation JSON, Observation SHA256, and split later supplied by the
source manifest. It must not serialize `SimulatorState`, protocol pending objects, true energy,
future arrivals, or evaluation truth.

- [ ] **Step 4: Add leakage and block-state tests**

Add tests asserting:

- every serialized record round-trips through `Observation.model_validate`;
- no serialized key equals `protocol_state`, `true_windows`, `future_arrivals`,
  `energy_true_Wh`, or `evaluation_truth`;
- every visible task has `remaining_bytes > 0`;
- `(payload_bytes - remaining_bytes) % 1024 == 0`;
- at least one sampled record has `sim_time_s > 0`;
- at least one sampled record has partial delivery.

- [ ] **Step 5: Run GREEN and commit**

Run:

```powershell
python -m pytest tests/test_generate_policy_pilot.py -q
```

Expected: all tests pass.

Commit:

```powershell
git add training/generate_policy_pilot.py tests/test_generate_policy_pilot.py
git commit -m "feat(A): sample protocol-clean pilot states"
```

---

### Task 3: Teacher labelling, result routing, and atomic package publication

**Files:**
- Modify: `training/generate_policy_pilot.py`
- Modify: `tests/test_generate_policy_pilot.py`

**Interfaces:**
- Consumes: `sample_source()`, source split manifest, `solve_teacher()`, `validate_teacher_result()`.
- Produces: `label_state(record, *, teacher_config, teacher_config_sha256, budget_ms) -> dict[str, object]`, `generate_pilot(config_path, output_dir) -> dict[str, object]`.

- [ ] **Step 1: Write failing routing and publication tests**

```python
from training.generate_policy_pilot import partition_attempts

def test_only_optimal_zero_gap_records_enter_samples():
    attempts = [
        {"state_id": "a", "solver_status": "OPTIMAL", "gap": 0.0,
         "label_eligible": True},
        {"state_id": "b", "solver_status": "TIME_LIMIT_FEASIBLE", "gap": 0.5,
         "label_eligible": False},
        {"state_id": "c", "solver_status": "UNSUPPORTED_LOSS", "gap": None,
         "label_eligible": False},
    ]
    samples, diagnostics = partition_attempts(attempts)
    assert [row["state_id"] for row in samples] == ["a"]
    assert [row["state_id"] for row in diagnostics] == ["b", "c"]

def test_publication_refuses_nonempty_destination(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    (output / "keep.txt").write_text("user data", encoding="utf-8")
    with pytest.raises(PilotDataError, match="OUTPUT_NOT_EMPTY"):
        generate_pilot(Path("missing-config.json"), output)
    assert (output / "keep.txt").read_text(encoding="utf-8") == "user data"
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_generate_policy_pilot.py -q
```

Expected: fails because `label_state` and `generate_pilot` are absent.

- [ ] **Step 3: Implement teacher labelling**

```python
def label_state(
    record: dict[str, object], *,
    teacher_config: dict[str, object],
    teacher_config_sha256: str,
    budget_ms: int,
) -> dict[str, object]:
    observation = Observation.model_validate(record["observation"])
    diagnostics: dict[str, object] = {}
    result = validate_teacher_result(
        observation,
        solve_teacher(
            observation,
            budget_ms=budget_ms,
            config=teacher_config,
            diagnostics=diagnostics,
        ),
    )
    eligible = result.solver_status == "OPTIMAL" and result.gap == 0.0
    labelled = {
        **record,
        "schema_version": "pilot-teacher-record-v1",
        "dataset_version": "a-n4-pilot-v1",
        "teacher_version": diagnostics["teacher_version"],
        "teacher_config_sha256": teacher_config_sha256,
        "candidate_scores": [
            row.model_dump(mode="json") for row in result.candidate_scores
        ],
        "solver_status": result.solver_status,
        "gap": result.gap,
        "elapsed_ms": result.elapsed_ms,
        "diagnostics": diagnostics,
        "label_eligible": eligible,
        "exclusion_reasons": [] if eligible else [result.solver_status],
    }
    stable = {key: value for key, value in labelled.items() if key != "elapsed_ms"}
    labelled["label_content_sha256"] = sha256_json(stable)
    return labelled

def partition_attempts(
    attempts: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    samples = []
    diagnostics = []
    for row in attempts:
        eligible = (
            row.get("label_eligible") is True
            and row.get("solver_status") == "OPTIMAL"
            and row.get("gap") == 0.0
        )
        if eligible:
            samples.append(row)
        else:
            diagnostics.append(row)
    return samples, diagnostics
```

Before hashing, remove per-candidate `elapsed_ms` from diagnostics, matching the frozen A-N3
stable-label rule.

- [ ] **Step 4: Implement package generation and budget stops**

`generate_pilot` must:

1. load and validate `configs/policy_pilot.json`;
2. call `write_source_protocol` in staging before sampling;
3. map each source ID to exactly one split;
4. sample and label in stable source/capture order;
5. track `process_time()` and stop at `cpu_budget_s`;
6. stop after `limited_result_stop_count` TIME/NODE results;
7. write attempts, eligible samples, diagnostics, summary, and manifest with LF;
8. re-read every file and verify advertised SHA256 before renaming staging to output;
9. remove only its verified, name-prefixed staging directory on failure.

Summary status is `ready_for_audit` only when:

- all 30 sources were attempted;
- 60–120 records are eligible;
- no integrity or leakage failure occurred;
- the run did not stop on CPU or solver limits.

Otherwise status is `blocked`, but all completed evidence remains published.

- [ ] **Step 5: Test deterministic stable labels and stop behavior**

Add tests that:

- two runs have equal source, split, status, candidate scores, gaps, and label content hashes;
- actual `elapsed_ms` may differ and is not part of the label content hash;
- a fake process clock crossing 7200 s produces `stop_reason="CPU_BUDGET"`;
- three limited results produce `stop_reason="REPEATED_SOLVER_LIMIT"`;
- a changed teacher config hash during generation blocks publication.

- [ ] **Step 6: Run GREEN and commit**

Run:

```powershell
python -m pytest tests/test_generate_policy_pilot.py -q
```

Expected: all tests pass.

Commit:

```powershell
git add training/generate_policy_pilot.py tests/test_generate_policy_pilot.py
git commit -m "feat(A): publish auditable pilot labels"
```

---

### Task 4: Independent audit and acceptance rendering

**Files:**
- Create: `training/audit_policy_pilot.py`
- Create: `tests/test_audit_policy_pilot.py`

**Interfaces:**
- Consumes: published pilot directory and `training.audit_policy_dataset.audit_rows()`.
- Produces: `verify_split_inheritance(rows, split_manifest) -> None`,
  `audit_pilot(package_dir) -> dict[str, object]`,
  `render_pilot_audit(audit) -> str`, CLI exit 0 only for an internally
  consistent package.

- [ ] **Step 1: Write failing package-audit tests**

```python
import json
from pathlib import Path

import pytest

import training.generate_policy_pilot as generator
from backend.contracts import TeacherCandidateScore, TeacherResult
from training.audit_policy_pilot import (
    audit_pilot,
    render_pilot_audit,
    verify_split_inheritance,
)

def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]

@pytest.fixture
def pilot_package(tmp_path, monkeypatch):
    def fake_teacher(observation, budget_ms, *, config=None, diagnostics=None):
        diagnostics.update({
            "teacher_version": "bounded-forecast-r4-v1",
            "candidates": [],
        })
        candidates = [
            TeacherCandidateScore(
                task_id=task.task_id, mode=mode, score=0.0, feasible=False
            )
            for task in observation.tasks
            for mode in ("robust", "fast")
        ]
        candidates.append(TeacherCandidateScore(
            task_id=None, mode="idle", score=0.0, feasible=True
        ))
        return TeacherResult(
            candidate_scores=candidates,
            solver_status="OPTIMAL",
            gap=0.0,
            elapsed_ms=1.0,
        )
    monkeypatch.setattr(generator, "solve_teacher", fake_teacher)
    output = tmp_path / "package"
    generator.generate_pilot(
        Path("configs/policy_pilot.json"), output
    )
    return output

def test_audit_verifies_sources_splits_hashes_and_label_semantics(pilot_package):
    audit = audit_pilot(pilot_package)
    assert audit["source_count"] == 30
    assert audit["split_counts"] == {"train": 18, "validation": 6, "test": 6}
    assert audit["cross_split_source_count"] == 0
    assert audit["duplicate_source_content_count"] == 0
    assert audit["duplicate_observation_content_count"] == 0
    assert audit["eligible_count"] == len(_read_jsonl(pilot_package / "samples.jsonl"))
    assert audit["label_quality"]["idle_in_optimal_set"] != audit["label_quality"]["tied_optimal_set"]

def test_split_verification_rejects_state_moved_to_another_split():
    manifest = {
        "splits": {
            "train": ["source-a"],
            "validation": ["source-b"],
            "test": ["source-c"],
        }
    }
    rows = [{"source_id": "source-a", "split": "validation"}]
    with pytest.raises(ValueError, match="SOURCE_SPLIT_MISMATCH"):
        verify_split_inheritance(rows, manifest)
```

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_audit_policy_pilot.py -q
```

Expected: collection fails because `training.audit_policy_pilot` does not exist.

- [ ] **Step 3: Implement independent verification**

`audit_pilot` must independently:

- verify the manifest contains exactly the required filenames and SHA256 values;
- parse all JSON/JSONL with finite values and no duplicate IDs;
- recompute source content hashes and Observation hashes;
- prove source split completeness/disjointness and row split inheritance;
- prove samples and diagnostics partition all attempts by `label_eligible`;
- reject any sample that is not `OPTIMAL + gap=0`;
- count family sources and sampled states;
- call `audit_rows(samples, reserve_wh=0.5)`;
- add per-mode plan rejection summaries from teacher diagnostics;
- keep idle-in-optimal and tied-optimal as separate named fields.

Implement split verification before reading label quality:

```python
def verify_split_inheritance(
    rows: list[dict[str, object]],
    split_manifest: dict[str, object],
) -> None:
    expected = {
        source_id: split_name
        for split_name, source_ids in split_manifest["splits"].items()
        for source_id in source_ids
    }
    for row in rows:
        if expected.get(row.get("source_id")) != row.get("split"):
            raise ValueError(
                f"SOURCE_SPLIT_MISMATCH: {row.get('source_id')}"
            )
```

Return:

```python
{
    "schema_version": "policy-pilot-audit-v1",
    "status": "accepted_for_receiver_review",
    "source_count": 30,
    "split_counts": {"train": 18, "validation": 6, "test": 6},
    "eligible_count": len(samples),
    "diagnostic_count": len(diagnostics),
    "cross_split_source_count": 0,
    "duplicate_source_content_count": 0,
    "duplicate_observation_content_count": 0,
    "family_counts": family_counts,
    "label_quality": row_audit["label_quality"],
    "coverage": row_audit["coverage"],
    "teacher": row_audit["teacher"],
    "inputs": verified_hashes,
}
```

- [ ] **Step 4: Implement explicit audit Markdown**

`render_pilot_audit` must state:

- this is synthetic pilot evidence, not a formal experiment result;
- idle-in-optimal and tied-optimal counts separately;
- actual boundary-source and eligible-state counts;
- unsupported/limited/error counts without hiding them;
- model training remains disabled pending B acceptance.

- [ ] **Step 5: Run GREEN and commit**

Run:

```powershell
python -m pytest tests/test_audit_policy_pilot.py -q
```

Expected: all tests pass.

Commit:

```powershell
git add training/audit_policy_pilot.py tests/test_audit_policy_pilot.py
git commit -m "feat(A): audit A-N4b pilot package"
```

---

### Task 5: Materialize the pilot, verify regressions, and prepare B handoff

**Files:**
- Create: `data/teacher/a_n4_pilot_v1/sources.jsonl`
- Create: `data/teacher/a_n4_pilot_v1/source_splits.json`
- Create: `data/teacher/a_n4_pilot_v1/attempts.jsonl`
- Create: `data/teacher/a_n4_pilot_v1/samples.jsonl`
- Create: `data/teacher/a_n4_pilot_v1/diagnostics.jsonl`
- Create: `data/teacher/a_n4_pilot_v1/summary.json`
- Create: `data/teacher/a_n4_pilot_v1/manifest.json`
- Create: `docs/evidence/A/A_N4b_pilot_2026-11-04/audit.json`
- Create: `docs/evidence/A/A_N4b_pilot_2026-11-04/README.md`
- Create: `docs/handoffs/A_N4b_pilot_B_2026-11-04.md`

**Interfaces:**
- Consumes: completed generator, auditor, and frozen config.
- Produces: receiver-verifiable data/evidence package and handoff; no model files.

- [ ] **Step 1: Run all new targeted tests**

Run:

```powershell
python -m pytest tests/test_pilot_scenarios.py tests/test_generate_policy_pilot.py tests/test_audit_policy_pilot.py -q
```

Expected: all new tests pass.

- [ ] **Step 2: Generate the real pilot package**

Run:

```powershell
python -m training.generate_policy_pilot --config configs/policy_pilot.json --output data/teacher/a_n4_pilot_v1
```

Expected: JSON stdout with `status` equal to `ready_for_audit` or a truthful `blocked`
status and explicit stop reason. Do not edit labels or delete diagnostics after this run.

- [ ] **Step 3: Audit twice and prove deterministic evidence**

Run:

```powershell
python -m training.audit_policy_pilot --package data/teacher/a_n4_pilot_v1 --output docs/evidence/A/A_N4b_pilot_2026-11-04
python -m training.audit_policy_pilot --package data/teacher/a_n4_pilot_v1 --verify docs/evidence/A/A_N4b_pilot_2026-11-04/audit.json
```

Expected: first command writes the evidence; second exits 0 and prints the same audit SHA256.

- [ ] **Step 4: Run the full regression suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass; the existing platform-specific skipped test and known AnyIO warning may remain, but no new failures or warnings are accepted.

- [ ] **Step 5: Write the B handoff with actual values**

`docs/handoffs/A_N4b_pilot_B_2026-11-04.md` must record values copied from the generated manifest and audit:

- branch and exact commit SHA;
- base, teacher version, teacher-config SHA and pilot-config SHA;
- source count and 18/6/6 source split;
- attempt, eligible, diagnostic and solver-status counts;
- family and boundary coverage counts;
- idle-in-optimal, tied-optimal and unique-non-idle counts as separate fields;
- all file SHA256 values;
- exact targeted/full test commands and results;
- limitations and either `ready_for_B_review` or `blocked`.

The document must not contain planned numbers in place of actual output.

- [ ] **Step 6: Commit the generated package and handoff**

Run:

```powershell
git add data/teacher/a_n4_pilot_v1 docs/evidence/A/A_N4b_pilot_2026-11-04 docs/handoffs/A_N4b_pilot_B_2026-11-04.md
git commit -m "data(A): deliver A-N4b teacher pilot"
```

- [ ] **Step 7: Final verification before any push**

Run:

```powershell
git status --short
git log --oneline --decorate -6
python -m pytest tests/test_pilot_scenarios.py tests/test_generate_policy_pilot.py tests/test_audit_policy_pilot.py -q
```

Expected: clean worktree, the expected sequence of A-N4b commits, and all targeted tests passing.
Do not push or create a pull request until the user explicitly requests it.
