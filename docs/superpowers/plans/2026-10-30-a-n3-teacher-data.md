# A-N3 Teacher Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompute and freeze 20 auditable H02 teacher labels, then provide an Observation-only policy feature/mask encoder and a deterministic, scenario-disjoint 12/4/4 split without starting policy training.

**Architecture:** A CLI reads only the H02 source identifiers and `Observation` objects, calls the real `solve_teacher` once per sample, validates every `TeacherResult`, and writes canonical JSONL plus provenance manifests. A separate pure encoder maps public `Observation` fields to fixed-shape global/candidate tensors and structural masks. A third pure module assigns whole scenarios to train/validation/test by a seeded SHA-256 ordering and refuses incomplete or ineligible datasets.

**Tech Stack:** Python 3.12, Pydantic v2 contracts, pytest, existing `backend.policies.teacher`, canonical JSON and SHA-256.

## Global Constraints

- Treat `backend/contracts.py` and the H00/H02 frozen contracts as read-only. Do not change another member's interface.
- Do not copy teacher scores from the B evidence bundle. Read only `sample_id` and `observation`, derive the new scenario key from `observation.run_id`, then recompute with `solve_teacher`.
- Do not turn old frozen predictions, simulation output, or planned metrics into new experiment results.
- Keep all generated evidence traceable to the exact source revision and config hashes.
- Never use teacher feasibility, teacher score, solver status, future outcome, or label fields as policy inputs or mask inputs.
- Do not add a model, optimizer, training loop, or claimed learning result in this phase.
- Follow test-driven development for every task: first produce the specified failing test, then add only enough implementation to pass it.
- Use the worktree `D:\pro2\.worktrees\a-n3-teacher-data` on branch `codex/a-n3-teacher-data`. Do not work directly in `D:\pro2`.
- Use `D:\pro2\.worktrees\a-n3-teacher-data\.venv\Scripts\python.exe` for every Python/pytest command.

---

## Task 1: Canonical one-sample teacher-label generation

**Files:**

- Create: `training/__init__.py`
- Create: `training/generate_teacher_data.py`
- Create: `tests/test_teacher_data.py`

- [ ] Add a failing test that loads the first record from `docs/evidence/B/H02_2026-10-29/samples.jsonl`, preserves a canonical copy of its observation, and calls a new `generate_record` function with the real solver.

The test must assert:

```python
assert record["sample_id"] == source["sample_id"]
assert record["scenario_id"] == source["observation"]["run_id"]
assert record["state_id"] == source["sample_id"]
assert record["solver_status"] == "OPTIMAL"
assert record["gap"] == 0.0
assert record["label_eligible"] is True
assert record["exclusion_reasons"] == []
assert record["observation"] == source["observation"]
score_by_key = {
    (item["task_id"], item["mode"]): item
    for item in record["candidate_scores"]
}
assert score_by_key[("T1", "fast")]["score"] == 1.0
assert score_by_key[("T1", "fast")]["feasible"] is True
assert score_by_key[("T1", "robust")]["feasible"] is False
assert canonical_json(source["observation"]) == before
assert record["label_content_sha256"] == label_content_sha256(record)
```

Also assert that the candidate key pairs are unique and that every numeric score and gap is finite.

- [ ] Run the test and confirm the intended RED failure:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py::test_generate_record_recomputes_first_h02_label -q
```

Expected: collection fails because `training.generate_teacher_data` does not exist.

- [ ] Implement the canonical primitives and one-record path in `training/generate_teacher_data.py`.

Use these public interfaces:

```python
class TeacherDataError(ValueError):
    def __init__(self, code: str, message: str) -> None: ...

def canonical_json(value: object) -> str: ...
def sha256_text(value: str) -> str: ...
def label_content_sha256(record: dict[str, object]) -> str: ...

def generate_record(
    source: dict[str, object],
    *,
    source_revision: str,
    budget_ms: int,
    teacher_config_path: Path,
) -> dict[str, object]: ...
```

Canonical JSON must use UTF-8 semantics, `ensure_ascii=False`, `sort_keys=True`, and separators `(',', ':')`. The label-content hash must include exactly these stable fields:

```python
LABEL_CONTENT_FIELDS = (
    "sample_id", "scenario_id", "state_id", "source_revision",
    "source_observation_sha256", "observation", "teacher_version",
    "teacher_config_sha256", "candidate_scores", "solver_status",
    "gap", "diagnostics", "label_eligible", "exclusion_reasons",
)
```

Do not include `elapsed_ms`, generation timestamps, output paths, or the hash itself. Preserve `elapsed_ms` in the record as runtime evidence, but keep it outside the deterministic label hash.

Before solving, recursively reject these case-insensitive hidden-truth keys inside the submitted observation payload:

```python
LEAK_FIELDS = {
    "true_capacity", "capacity_true_wh", "future_arrivals",
    "actual_future_loss", "evaluation_truth", "energy_true_wh", "soc_true",
}
```

Read only `sample_id` and `observation` from each source envelope. Ignore its existing `candidate_scores`, status, gap, timing, version, and `scenario_id`; derive the new `scenario_id` from `observation.run_id` and set `state_id=sample_id`. Apply the leak scan only inside the submitted observation payload. Parse the payload with `Observation.model_validate`, call:

```python
diagnostics: dict[str, object] = {}
result = solve_teacher(
    observation,
    budget_ms=budget_ms,
    config=load_json(teacher_config_path),
    diagnostics=diagnostics,
)
validate_teacher_result(observation, result)
```

After solving, verify that canonical observation bytes are unchanged, candidate `(task_id, mode)` pairs are unique, all candidate scores and every non-null gap are finite, and the teacher version/config hash are recorded. Eligibility is strictly:

```python
eligible = result.solver_status == "OPTIMAL" and result.gap == 0.0
```

- [ ] Run the focused test and confirm it passes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py::test_generate_record_recomputes_first_h02_label -q
```

Expected: `1 passed`.

- [ ] Add boundary tests for leak-field rejection, duplicate candidate keys, non-finite values, and observation mutation detection. Use monkeypatching only to inject malformed solver returns; the happy-path test must continue using the real H02 solver.

- [ ] Run the complete file:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py -q
```

- [ ] Commit Task 1:

```powershell
git add training/__init__.py training/generate_teacher_data.py tests/test_teacher_data.py
git commit -m "feat(ai): add canonical teacher label generation"
```

---

## Task 2: Twenty-sample batch, failure evidence, and provenance manifests

**Files:**

- Modify: `training/generate_teacher_data.py`
- Modify: `tests/test_teacher_data.py`

- [ ] Add failing tests for a `generate_dataset` batch API and CLI.

Required interface:

```python
def generate_teacher_dataset(
    *,
    source_path: Path,
    output_dir: Path,
    source_revision: str,
    teacher_config_path: Path,
    budget_ms: int,
    expected_count: int = 20,
) -> dict[str, object]: ...
```

The tests must verify all of the following:

1. Exactly 20 source rows, sample IDs, scenario IDs, and observations are consumed.
2. A spy wrapping the real `solve_teacher` records exactly 20 calls.
3. Output ordering is deterministic by `(scenario_id, sample_id)`, where `scenario_id` comes from `observation.run_id`.
4. `samples.jsonl` has 20 rows; all are `OPTIMAL`, gap zero, and label-eligible for the current H02 evidence.
5. `summary.json` reports exact counts by status and eligibility.
6. `manifest.json` includes source/output/config SHA-256 values, source revision, teacher version, budget, schema versions, command, and file row counts.
7. Duplicate sample IDs, duplicate derived scenario IDs, an unexpected count, a dirty/nonempty output directory, a non-40-hex source revision, or any source observation leak causes a controlled nonzero failure before publication.
8. A mocked `TIME_LIMIT_FEASIBLE` result is retained with `label_eligible=false` and an exclusion reason; the batch status is `blocked` and the CLI exits nonzero after writing evidence.
9. A thrown per-sample exception is retained as a failure record with a stable error code and message; it is never silently dropped.

- [ ] Run the new tests and confirm RED failures because the batch API/CLI are absent:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py -q
```

- [ ] Implement newline-delimited canonical JSON writing with an atomic staging directory beside `output_dir`. Publish the final directory only after all three files are closed and re-read successfully. Never overwrite a nonempty destination.

Use this summary status rule:

```python
ready = (
    total == expected_count
    and eligible == expected_count
    and failures == 0
    and solver_status_counts == {"OPTIMAL": expected_count}
)
    summary["status"] = "ready_for_split" if ready else "blocked"
```

Use this CLI:

```powershell
.\.venv\Scripts\python.exe -m training.generate_teacher_data `
  --source docs/evidence/B/H02_2026-10-29/samples.jsonl `
  --output data/teacher/a_n3_20 `
  --source-revision cccca9892086522624a5979216d7a2ab73209803 `
  --teacher-config configs/teacher.json `
  --budget-ms 1000 `
  --expected-count 20
```

The `command` field in the manifest must be the normalized argument vector, not a shell-expanded or machine-specific absolute path. Timestamps may appear in the manifest as provenance but must not enter per-label content hashes.

- [ ] Run the batch tests and confirm they pass:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py -q
```

- [ ] Commit Task 2:

```powershell
git add training/generate_teacher_data.py tests/test_teacher_data.py
git commit -m "feat(ai): generate auditable H02 teacher dataset"
```

---

## Task 3: Observation-only policy features and structural action masks

**Files:**

- Create: `training/policy_features.py`
- Create: `tests/test_policy_features.py`

- [ ] Add failing tests for the exact public output type:

```python
@dataclass(frozen=True)
class EncodedObservation:
    schema_version: str
    global_feature_names: tuple[str, ...]
    candidate_feature_names: tuple[str, ...]
    candidate_keys: tuple[tuple[str | None, str], ...]
    global_features: tuple[float, ...]
    candidate_features: tuple[tuple[float, ...], ...]
    candidate_mask: tuple[bool, ...]

def encode_observation(observation: Observation) -> EncodedObservation: ...
```

Assert the global feature order is exactly:

```python
GLOBAL_FEATURE_NAMES = (
    "sim_time_s", "cache_bytes", "energy_lower_Wh", "soc_lower",
    "capacity_lower_Wh", "visible_task_count", "inflight_present",
    "next_window_start_delta_s", "next_window_duration_s",
    "next_robust_bps", "next_fast_bps", "next_robust_loss_prob",
    "next_fast_loss_prob", "has_forecast_window",
)
```

Assert each task contributes `robust` then `fast`, task IDs are sorted lexically, and the final candidate is `(None, 'idle')`. Candidate features must be exactly:

```python
CANDIDATE_FEATURE_NAMES = (
    "is_idle", "is_robust", "is_fast", "time_since_arrival_s",
    "time_to_deadline_s", "payload_bytes", "remaining_bytes",
    "remaining_fraction", "priority_weight",
)
```

The structural mask must be derived only from public observation state:

```python
task_allowed = (
    observation.inflight is None
    and task.deadline_s >= observation.sim_time_s
    and task.remaining_bytes > 0
)
```

Both modes share the same structural availability; idle is always available. Do not incorporate energy sufficiency, forecast success, teacher feasibility, or teacher score into this mask.

- [ ] Add edge-case tests covering no forecast windows, an active window, a future window, expired/completed tasks, inflight work, unsorted tasks, and NaN/Inf rejection. The next window is the earliest window whose `end_s > sim_time_s`; evaluate its robust/fast rate and loss profiles at `max(sim_time_s, start_s)` using the latest profile point at or before that time, falling back to the first point. Use the full window duration `end_s - start_s`, matching the approved design.

- [ ] Add a leakage-invariance test: keep the same Observation while replacing every teacher candidate score/feasible value in an unrelated label object; encoded arrays and mask must remain byte-identical. The encoder signature must make passing a teacher result impossible.

- [ ] Run and confirm RED:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policy_features.py -q
```

- [ ] Implement the pure encoder. Return immutable tuples of Python floats and booleans. Raise `PolicyFeatureError` for non-finite output or schema violations. Do not perform normalization in this module.

- [ ] Run and confirm GREEN:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policy_features.py -q
```

- [ ] Commit Task 3:

```powershell
git add training/policy_features.py tests/test_policy_features.py
git commit -m "feat(ai): add observation-only policy features and masks"
```

---

## Task 4: Deterministic scenario-disjoint split and frozen training input config

**Files:**

- Create: `training/splits.py`
- Create: `tests/test_splits.py`
- Create: `configs/policy_train.json`

- [ ] Add failing tests for:

```python
def build_split_manifest(
    samples_path: Path,
    output_path: Path,
    *,
    split_seed: int,
    split_counts: tuple[int, int, int] = (12, 4, 4),
) -> dict[str, object]: ...
```

The function must read the adjacent `summary.json` and `manifest.json` from `samples_path.parent` and verify them before assigning rows.

Sort unique scenario IDs by:

```python
key = sha256(f"{seed}:{scenario_id}".encode("utf-8")).hexdigest()
```

Assign the first 12 to train, next 4 to validation, final 4 to test. Preserve all rows belonging to one scenario in the same split. The split manifest must include scenario lists, sample lists, counts, pairwise intersections, source JSONL SHA-256, split seed, and split algorithm version.

Tests must prove:

- same input/seed produces byte-identical output;
- another seed changes at least one assignment;
- train/validation/test scenario and sample intersections are empty;
- union equals the source set;
- duplicate sample IDs, fewer/more than 20 scenarios, a non-`ready_for_split` summary, a source hash mismatch, or any ineligible record blocks splitting;
- tampering one source byte is detected through the manifest hash;
- config feature names match the constants exported by `training.policy_features`.

- [ ] Run and confirm RED:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_splits.py -q
```

- [ ] Implement `training/splits.py` with a CLI that writes `data/teacher/a_n3_20/splits.json` atomically and refuses overwrite unless the existing bytes are identical.

- [ ] Create `configs/policy_train.json` with these frozen values:

```json
{
  "schema_version": "policy-train-config-v1",
  "dataset_path": "data/teacher/a_n3_20/samples.jsonl",
  "dataset_summary_path": "data/teacher/a_n3_20/summary.json",
  "dataset_manifest_path": "data/teacher/a_n3_20/manifest.json",
  "split_manifest_path": "data/teacher/a_n3_20/splits.json",
  "teacher_version": "bounded-forecast-r4-v1",
  "teacher_budget_ms": 1000,
  "feature_schema_version": "policy-features-v1",
  "global_feature_names": [
    "sim_time_s", "cache_bytes", "energy_lower_Wh", "soc_lower",
    "capacity_lower_Wh", "visible_task_count", "inflight_present",
    "next_window_start_delta_s", "next_window_duration_s",
    "next_robust_bps", "next_fast_bps", "next_robust_loss_prob",
    "next_fast_loss_prob", "has_forecast_window"
  ],
  "candidate_feature_names": [
    "is_idle", "is_robust", "is_fast", "time_since_arrival_s",
    "time_to_deadline_s", "payload_bytes", "remaining_bytes",
    "remaining_fraction", "priority_weight"
  ],
  "split_algorithm_version": "scenario-sha256-v1",
  "split_seed": 20261030,
  "split_counts": {"train": 12, "validation": 4, "test": 4},
  "eligible_solver_status": "OPTIMAL",
  "required_gap": 0.0,
  "normalization": "deferred-until-training",
  "training_enabled": false
}
```

- [ ] Run and confirm GREEN:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_splits.py tests/test_policy_features.py -q
```

- [ ] Commit Task 4:

```powershell
git add training/splits.py tests/test_splits.py configs/policy_train.json
git commit -m "feat(ai): add deterministic scenario data splits"
```

---

## Task 5: Produce the 20-label evidence bundle and H02 A acceptance receipt

**Files:**

- Create: `data/teacher/a_n3_20/samples.jsonl`
- Create: `data/teacher/a_n3_20/summary.json`
- Create: `data/teacher/a_n3_20/manifest.json`
- Create: `data/teacher/a_n3_20/splits.json`
- Create: `docs/acceptance/H02_A_2026-10-30.md`
- Modify: `docs/task_board.csv`

- [ ] Resolve and record the exact clean source revision before generation:

```powershell
git status --short
git rev-parse cccca9892086522624a5979216d7a2ab73209803^{commit}
git diff --exit-code cccca9892086522624a5979216d7a2ab73209803 -- backend/contracts.py backend/policies/teacher.py configs/teacher.json
Get-FileHash docs/evidence/B/H02_2026-10-29/samples.jsonl -Algorithm SHA256
```

Expected: clean status before generated files, the exact 40-character teacher source revision, zero teacher/contract/config drift, and source evidence SHA-256 `3eec464b6cef0389458a8927b32b6e60d521cb295498722321a4ab533c43c062`.

- [ ] Generate all 20 labels with the exact Task 2 CLI. Stop and retain the failure evidence if the command exits nonzero; do not continue to splitting or claim acceptance.

- [ ] Validate the artifacts independently:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py tests/test_policy_features.py tests/test_splits.py -q
.\.venv\Scripts\python.exe -m training.splits `
  --samples data/teacher/a_n3_20/samples.jsonl `
  --output data/teacher/a_n3_20/splits.json `
  --seed 20261030 `
  --train-count 12 --validation-count 4 --test-count 4
Get-FileHash data/teacher/a_n3_20/samples.jsonl -Algorithm SHA256
Get-FileHash data/teacher/a_n3_20/summary.json -Algorithm SHA256
Get-FileHash data/teacher/a_n3_20/manifest.json -Algorithm SHA256
Get-FileHash data/teacher/a_n3_20/splits.json -Algorithm SHA256
```

- [ ] Inspect all four artifacts. Confirm 20/20 labels are eligible, 20 real solver invocations are evidenced, all source observation hashes match, every label content hash recomputes, status is `ready_for_split`, and split intersections are empty.

- [ ] Write `docs/acceptance/H02_A_2026-10-30.md` using only observed command results. Include:

1. decision (`accepted` only if every gate above passed);
2. exact source and implementation revisions;
3. source/config/output SHA-256 values;
4. exact solver-status, eligibility, failure, and split counts;
5. exact commands and pytest counts;
6. statement that labels were recomputed, not copied;
7. statement that features/masks use only Observation fields;
8. statement that no model was trained and no performance claim is made;
9. links to the four generated artifacts.

- [ ] Update only the relevant rows in `docs/task_board.csv`: mark H02 A acceptance with its receipt path, mark A-N3 teacher-data/feature/split work ready for B review, and leave unrelated member statuses untouched. If the current row layout differs, preserve its columns and wording conventions rather than rewriting the board.

- [ ] Commit the evidence bundle:

```powershell
git add data/teacher/a_n3_20 configs/policy_train.json docs/acceptance/H02_A_2026-10-30.md docs/task_board.csv
git commit -m "data(ai): freeze A-N3 teacher labels and splits"
```

---

## Task 6: Independent regression and handoff verification

**Files:**

- Modify only if verification reveals a defect: files introduced in Tasks 1–5
- Do not modify: `backend/contracts.py`, legacy assets, B/C-owned interfaces

- [ ] Run the H02 contract/teacher regression tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policies.py tests/test_policy_runner.py tests/test_teacher.py -q
```

Expected baseline: `26 passed`.

- [ ] Run all new A-N3 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_data.py tests/test_policy_features.py tests/test_splits.py -q
```

- [ ] Run the full suite. The repository config expects a sibling Chinese-named delivery directory, so create a temporary directory junction only if it is absent, verify its exact target, then remove only that junction after the run:

```powershell
if (-not (Test-Path 'D:\pro2\.worktrees\交付包')) {
  New-Item -ItemType Junction `
    -Path 'D:\pro2\.worktrees\交付包' `
    -Target 'D:\pro2\交付包' | Out-Null
}
Get-Item 'D:\pro2\.worktrees\交付包' | Select-Object FullName,LinkType,Target
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item -LiteralPath 'D:\pro2\.worktrees\交付包'
```

Expected baseline before new tests: `293 passed, 1 warning`; the final pass count must equal 293 plus every newly collected A-N3 test, with no failure. Record the actual count in the receipt rather than predicting it.

- [ ] Confirm no protected interface drift and no ignored runtime evidence is staged:

```powershell
git diff --exit-code 930476667933ca5d307a11e2003a7a263541baa9 -- backend/contracts.py
git status --short
git diff --check
git ls-files .venv runs
```

Expected: zero contract diff, clean whitespace check, and no tracked `.venv` or `runs` paths.

- [ ] Review the complete branch diff:

```powershell
git log --oneline --decorate 930476667933ca5d307a11e2003a7a263541baa9..HEAD
git diff --stat 930476667933ca5d307a11e2003a7a263541baa9..HEAD
git diff 930476667933ca5d307a11e2003a7a263541baa9..HEAD -- backend training tests configs data/teacher docs
```

- [ ] If review finds a defect, add a failing regression test, fix only that defect, rerun the focused and full suites, and commit with a narrowly scoped message. Do not amend evidence to hide a failed run.

- [ ] Prepare the handoff to member B with the branch name, commit list, H02 receipt path, four artifact paths/hashes, exact pytest counts, and the explicit statement: `training_enabled=false; no model or experiment result is included`.

