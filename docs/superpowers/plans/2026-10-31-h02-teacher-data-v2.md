# H02 Teacher Data v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rejected H02 teacher-data split with a new 20-row synthetic v2 delivery whose decision inputs are content-unique and whose 12/4/4 split is source-group disjoint.

**Architecture:** Add a canonical Observation-content identity at the teacher-data publication boundary, propagate source-group and content identities into stable records, and split by source group instead of display IDs. Preserve the rejected v1 artifacts, generate a parallel v2 source/output set, then freeze hashes and issue a new A-to-B handoff.

**Tech Stack:** Python 3.12, Pydantic v2 contracts, pytest, canonical JSON, SHA-256, Git.

## Global Constraints

- Work only on `codex/a-next`, based on `origin/feature/ai@866df43d124e62a77081a7acd2e095c98b34c172`.
- Keep `docs/evidence/B/H02_2026-10-29/` and `data/teacher/a_n3_20/` byte-for-byte unchanged.
- Do not change public Observation, TeacherResult, CandidateScore, solve_teacher, or Guard contracts.
- All v2 inputs and results are synthetic pipeline-validation data, not model-training evidence or real satellite results.
- Run tests with `py -3`; use repository-local `runs/` for pytest temporary output.
- Every production behavior change must follow red-green-refactor.

---

### Task 1: Reject duplicate decision inputs before solving

**Files:**
- Modify: `tests/test_teacher_data.py`
- Modify: `training/generate_teacher_data.py`

**Interfaces:**
- Produces: `observation_content_sha256(payload: dict[str, object]) -> str`
- Produces: records containing `source_group_id` and `observation_content_sha256`
- Consumes: source rows with explicit `source_group_id`, or historical `scenario_id` as a single-record compatibility fallback

- [ ] **Step 1: Add the content-identity unit test**

Add a test that proves execution identifiers do not affect decision-input identity:

```python
def test_observation_content_identity_ignores_only_execution_ids():
    left = first_source()["observation"]
    right = copy.deepcopy(left)
    right["run_id"] = "another-run"
    right["policy_id"] = "another-policy"
    assert observation_content_sha256(left) == observation_content_sha256(right)
    right["cache_bytes"] += 1
    assert observation_content_sha256(left) != observation_content_sha256(right)
```

- [ ] **Step 2: Add the failing batch regression**

Construct two rows with different `sample_id`, `source_group_id`, `run_id`, and
`policy_id`, but otherwise identical Observations. Assert
`generate_teacher_dataset` raises `TeacherDataError` with code
`DUPLICATE_OBSERVATION_CONTENT`, calls the teacher zero times, and publishes no
output.

Update the positive batch-test helper to create a temporary 20-row source with
explicit source groups and content-unique public inputs. Do not keep using the
rejected historical v1 source as a positive fixture; retain it only for the new
duplicate-content regression. This prevents the correct new validation from
turning unrelated publication tests into false failures.

- [ ] **Step 3: Run the two tests and observe RED**

Run:

```powershell
py -3 -m pytest tests/test_teacher_data.py -q -p no:cacheprovider --basetemp runs/h02_v2_red_identity
```

Expected: failures because `observation_content_sha256` and duplicate-content
preflight do not exist.

- [ ] **Step 4: Implement canonical identity and provenance propagation**

In `training/generate_teacher_data.py`, add:

```python
EXECUTION_ID_FIELDS = frozenset({"run_id", "policy_id"})

def observation_content_sha256(payload: dict[str, object]) -> str:
    content = copy.deepcopy(payload)
    for field in EXECUTION_ID_FIELDS:
        content.pop(field, None)
    return sha256_text(canonical_json(content))

def source_group_id(source: dict[str, object]) -> str:
    value = source.get("source_group_id", source.get("scenario_id"))
    if not isinstance(value, str) or not value.strip():
        raise TeacherDataError("INVALID_SOURCE_GROUP", "source_group_id must be nonempty")
    return value
```

Validate unique content hashes in the existing all-input preflight loop before
the first `solve_teacher` call. Add both provenance fields to success and
failure records and to `LABEL_CONTENT_FIELDS`. Keep the original full
Observation hash as `source_observation_sha256`.

- [ ] **Step 5: Run the teacher-data module tests and observe GREEN**

Run the Step 3 command with basetemp `runs/h02_v2_green_identity`.
Expected: all tests in `tests/test_teacher_data.py` pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add training/generate_teacher_data.py tests/test_teacher_data.py
git commit -m "fix(ai): reject duplicate teacher observations"
```

---

### Task 2: Partition by source group and verify embedded identities

**Files:**
- Modify: `tests/test_splits.py`
- Modify: `training/splits.py`

**Interfaces:**
- Consumes: eligible teacher records with `source_group_id`, `scenario_id`,
  `sample_id`, `observation`, and `observation_content_sha256`
- Produces: split algorithm `source-group-sha256-v2`
- Produces: per-split `source_group_ids`, `scenario_ids`, `sample_ids`, and
  `observation_content_sha256` lists plus pairwise intersections

- [ ] **Step 1: Extend the split fixture with real identity fields**

Give every fixture record a minimal valid embedded Observation, its recomputed
content hash, a source group, and a scenario. Retain two records in selected
groups so grouping behavior is exercised.

- [ ] **Step 2: Add failing split tests**

Add separate tests that assert:

```python
assert sample_to_split["state-a"] == sample_to_split["state-b"]
```

when both states share a source group, and that a forged stored content hash or
duplicate content in different source groups raises `ValueError`.

- [ ] **Step 3: Run split tests and observe RED**

```powershell
py -3 -m pytest tests/test_splits.py -q -p no:cacheprovider --basetemp runs/h02_v2_red_splits
```

Expected: failures because splitting still uses `scenario_id` and does not
verify Observation content.

- [ ] **Step 4: Implement group-first splitting**

Import `observation_content_sha256`. Recompute every record's identity and
reject a mismatch. Reject duplicate content hashes. Build the partition unit
from `source_group_id`, place all samples from one group together, and emit:

```python
result = {
    "split_algorithm_version": "source-group-sha256-v2",
    "split_seed": split_seed,
    "source_jsonl_sha256": digest,
    "splits": splits,
    "intersections": intersections,
}
```

Interpret `split_counts` as source-group counts. Compute intersections for all
four identity fields and retain deterministic ordering and immutable-output
behavior.

- [ ] **Step 5: Run split tests and observe GREEN**

Run the Step 3 command with basetemp `runs/h02_v2_green_splits`.
Expected: all split tests pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add training/splits.py tests/test_splits.py
git commit -m "fix(ai): split teacher data by source group"
```

---

### Task 3: Build and freeze 20 independent H02 v2 scenarios

**Files:**
- Create: `training/build_h02_v2_source.py`
- Create: `tests/test_h02_v2_source.py`
- Create: `data/teacher/sources/a_n3_20_v2.jsonl`
- Create: `data/teacher/a_n3_20_v2/manifest.json`
- Create: `data/teacher/a_n3_20_v2/samples.jsonl`
- Create: `data/teacher/a_n3_20_v2/summary.json`
- Create: `data/teacher/a_n3_20_v2/splits.json`
- Modify: `configs/policy_train.json`
- Modify: `tests/test_splits.py`

**Interfaces:**
- Produces: `build_source_rows() -> list[dict[str, object]]`
- Consumes: existing public Observation schema and teacher support limits

- [ ] **Step 1: Write failing source-matrix tests**

Assert the builder returns exactly 20 rows, every row validates as Observation,
all sample IDs/source groups/run IDs/content hashes are unique, all source names
are `synthetic`, every loss probability is zero, no inflight block exists, and
every row solves to `OPTIMAL` with gap `0.0` under the frozen teacher config.

- [ ] **Step 2: Run the source test and observe RED**

```powershell
py -3 -m pytest tests/test_h02_v2_source.py -q -p no:cacheprovider --basetemp runs/h02_v2_red_source
```

Expected: import failure because `training.build_h02_v2_source` does not exist.

- [ ] **Step 3: Implement the deterministic 20-row matrix**

Build Observations from the frozen public H02 shape while varying multiple
public dimensions within support limits: one/two/three visible tasks, deadlines
2-12 seconds, payloads 1024-4096 bytes, priorities 1-5, immediate/delayed
windows, robust rates 4096-12288 bps, fast rates 8192-24576 bps, and public
`soc_lower` values 0.05-0.80 with matching `energy_lower_Wh`. Use stable IDs:

```python
row = {
    "sample_id": f"h02_v2_{index:02d}",
    "source_group_id": f"h02-v2-source-{index:02d}",
    "observation": observation,
}
```

The module CLI writes canonical JSONL with LF line endings and refuses to
overwrite a differing existing file.

- [ ] **Step 4: Run source tests and observe GREEN**

Run the Step 2 command with basetemp `runs/h02_v2_green_source`.
Expected: all source tests pass and all 20 teacher results are eligible.

- [ ] **Step 5: Materialize and commit the independent source first**

```powershell
py -3 -m training.build_h02_v2_source --output data/teacher/sources/a_n3_20_v2.jsonl
git add training/build_h02_v2_source.py tests/test_h02_v2_source.py data/teacher/sources/a_n3_20_v2.jsonl
git commit -m "feat(ai): add independent H02 v2 source matrix"
```

Expected: the committed source has 20 rows and 20 distinct content identities.
This separate commit provides a real, non-circular source revision for the
label manifest.

- [ ] **Step 6: Generate labels and split into fresh paths**

```powershell
$sourceRevision = git rev-parse HEAD
py -3 -m training.generate_teacher_data --source data/teacher/sources/a_n3_20_v2.jsonl --output data/teacher/a_n3_20_v2 --source-revision $sourceRevision --teacher-config configs/teacher.json --budget-ms 1000 --expected-count 20
py -3 -m training.splits --samples data/teacher/a_n3_20_v2/samples.jsonl --output data/teacher/a_n3_20_v2/splits.json --seed 20261031 --train-count 12 --validation-count 4 --test-count 4
```

Expected: generation reports `ready_for_split`; split command exits zero.

- [ ] **Step 7: Point the disabled training config at v2**

Update the four dataset paths, set
`split_algorithm_version` to `source-group-sha256-v2`, set seed to `20261031`,
and keep `training_enabled` exactly `false`. Update the exact-config assertion.

- [ ] **Step 8: Verify deterministic regeneration**

Generate into a fresh directory under `runs/h02_v2_regeneration/`, compare
source, samples, summary, manifest, and splits hashes or canonical stable fields,
and assert 20 unique content hashes and empty split intersections. Runtime-only
`elapsed_ms` is excluded from stable label hashes but may change byte hashes;
the committed manifest must describe the actual committed generation.

- [ ] **Step 9: Commit the frozen outputs and config**

```powershell
git add tests/test_splits.py configs/policy_train.json data/teacher/a_n3_20_v2
git commit -m "data(ai): freeze leakage-safe H02 teacher data v2"
```

---

### Task 4: Issue the corrected A-to-B handoff and verify the branch

**Files:**
- Create: `docs/handoffs/A_N3_data_v2_A_2026-10-31.md`
- Modify: `docs/task_board.csv`

**Interfaces:**
- Produces: auditable resubmission instructions for B
- Consumes: final candidate commit and committed file SHA-256 values

- [ ] **Step 1: Run targeted tests**

```powershell
py -3 -m pytest tests/test_teacher_data.py tests/test_policy_features.py tests/test_splits.py tests/test_h02_v2_source.py -q -p no:cacheprovider --basetemp runs/h02_v2_targeted
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run the full repository suite**

Ensure the historical `交付包` path expected by repository tests is available
without modifying its contents, then run:

```powershell
py -3 -m pytest -q -p no:cacheprovider --basetemp runs/h02_v2_full
```

Expected: full suite passes with no new warnings or failures.

- [ ] **Step 3: Write the handoff**

Record candidate SHA, base SHA, exact commands, test counts, all new artifact
SHA-256 values, 20/20 content uniqueness, 12/4/4 group counts, empty
intersections, synthetic-only limitation, and the explicit request that B
recompute all labels and independently repeat the duplicate audit. State that
the old v1 candidate remains historical `changes_requested` evidence.

- [ ] **Step 4: Update only the A-N3 task-board row**

Keep A-N3 at `ready_for_review` for the teacher-data stage, point its artifact
to the v2 handoff/data directory, and state that learned-policy implementation
is still not complete. Do not alter B/C-owned interfaces or claim A-N3 overall
acceptance.

- [ ] **Step 5: Run repository integrity checks**

```powershell
git diff --check
git status --short
git diff --stat 866df43d124e62a77081a7acd2e095c98b34c172..HEAD
```

Also verify historical paths have no diff:

```powershell
git diff --exit-code 866df43d124e62a77081a7acd2e095c98b34c172 -- docs/evidence/B/H02_2026-10-29 data/teacher/a_n3_20
```

- [ ] **Step 6: Commit Task 4**

```powershell
git add docs/handoffs/A_N3_data_v2_A_2026-10-31.md docs/task_board.csv
git commit -m "docs(ai): resubmit H02 teacher data for B review"
```

- [ ] **Step 7: Request review before any push or merge**

Use the requesting-code-review workflow against the complete branch. Do not
push, merge, or delete `codex/a-next` without the user's explicit confirmation.
