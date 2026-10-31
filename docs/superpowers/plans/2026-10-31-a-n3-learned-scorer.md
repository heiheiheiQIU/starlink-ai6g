# A-N3 Learned Scorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver A's audited `score_actions()` learned scorer, deterministic three-seed training package, model card, hashes and handoff using only the accepted H02 v2 synthetic data.

**Architecture:** Verify and encode the frozen 12/4/4 dataset into variable-length candidate rows, fit normalization on train only, train a shared 23→32→16 two-head MLP in PyTorch, and export fixed non-pickle NumPy arrays. Runtime inference validates every artifact and uses NumPy; B's existing gateway and Guard retain timeout, fallback and physical-feasibility authority.

**Tech Stack:** Python 3.12.9, NumPy 2.1.3, PyTorch 2.5.1, Pydantic 2.12.3, pytest 8.3.5, Git worktree `D:/pro2/.worktrees/a-n3-learned`.

## Global Constraints

- Work only on `codex/a-n3-learned`, based on `codex/a-next@2cfe89c`; do not modify PR #7.
- Frozen data candidate is `8f206b4f6d029ddaf3cfd6163777e0c9a57b03ee`; source revision is `38a1a7463bfe0c8eaecf1bb729b98aa74ae0040b`.
- Do not modify `data/teacher/a_n3_20_v2/*`, legacy assets, H00 contracts, `configs/schema.json`, or other members' interfaces.
- Train/validation/test remain exactly 12/4/4; test is never used for normalization, stopping, seed selection or hyperparameters.
- Feature schema remains `policy-features-v1`: 14 global + 9 candidate features in the frozen order.
- Candidate order is sorted task ID, robust then fast, with one idle last; labels join by `(task_id, mode)`, never by JSON position.
- Runtime weights are numeric `.npz` arrays loaded with `allow_pickle=False`; no `.pt` runtime artifact.
- Training seeds are exactly 20261031, 20261032 and 20261033; selected seed minimizes validation total loss with lower seed as tie-break.
- Initial gateway budget remains 100 ms; model load and warm forward timing are reported separately.
- Every production behavior follows RED→GREEN→REFACTOR. Commit after each task.
- Claims remain synthetic small-sample pipeline/overfit validation, never generalization, AI superiority, mature optimization or in-orbit performance.

---

### Task 1: Frozen dataset gate and train-only normalization

**Files:**
- Create: `training/policy_dataset.py`
- Create: `tests/test_policy_dataset.py`

**Interfaces:**
- Consumes: `training.policy_features.encode_observation(Observation) -> EncodedObservation`, `configs/policy_train.json`, v2 samples/summary/manifest/splits.
- Produces: `load_frozen_dataset(config_path=Path(...), *, root: Path | None = None) -> FrozenPolicyDataset`, `fit_normalization(examples) -> Normalization`, `normalise_example(example, normalization) -> tuple[tuple[float, ...], ...]`.

- [ ] **Step 1: Write failing real-data loading and alignment tests**

```python
def test_loads_exact_frozen_split_and_aligns_labels_by_key():
    data = load_frozen_dataset()
    assert {name: len(rows) for name, rows in data.splits.items()} == {
        "train": 12, "validation": 4, "test": 4,
    }
    first = data.by_sample_id["h02_v2_00"]
    assert first.candidate_keys == (("T1", "robust"), ("T1", "fast"), (None, "idle"))
    assert first.target_scores == (0.0, 1.0, 1.0)
    assert first.target_feasible == (False, True, True)


def test_normalization_is_fitted_from_train_only():
    data = load_frozen_dataset()
    expected = fit_normalization(data.splits["train"])
    assert data.normalization == expected
    assert data.normalization.source_split == "train"
    assert all(scale > 0.0 for scale in (*expected.global_scale, *expected.candidate_scale))
```

- [ ] **Step 2: Run tests and verify RED**

Run: `py -3 -m pytest tests/test_policy_dataset.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_dataset_red`

Expected: collection fails with `ModuleNotFoundError: No module named 'training.policy_dataset'`.

- [ ] **Step 3: Implement immutable dataset types, hash gates and key join**

```python
@dataclass(frozen=True)
class PolicyExample:
    sample_id: str
    observation: Observation
    candidate_keys: tuple[tuple[str | None, str], ...]
    global_features: tuple[float, ...]
    candidate_features: tuple[tuple[float, ...], ...]
    candidate_mask: tuple[bool, ...]
    target_scores: tuple[float, ...]
    target_feasible: tuple[bool, ...]


@dataclass(frozen=True)
class Normalization:
    schema_version: str
    feature_schema_version: str
    source_split: str
    global_feature_names: tuple[str, ...]
    candidate_feature_names: tuple[str, ...]
    global_mean: tuple[float, ...]
    global_scale: tuple[float, ...]
    candidate_mean: tuple[float, ...]
    candidate_scale: tuple[float, ...]


@dataclass(frozen=True)
class FrozenPolicyDataset:
    splits: dict[str, tuple[PolicyExample, ...]]
    by_sample_id: dict[str, PolicyExample]
    normalization: Normalization
    samples_sha256: str
    split_sha256: str
```

`load_frozen_dataset()` must verify config feature names/version, samples and summary hashes against `manifest.json`, samples hash against `splits.json`, all empty intersections, exact split IDs/counts, all OPTIMAL/gap-zero/eligible labels, unique identifiers and candidate keys, finite scores, observation content hashes, and exact split coverage. It must join labels by key and then reorder them to encoder order.

- [ ] **Step 4: Add failure tests for tampering, duplicate/missing candidates and leakage**

Use a helper that copies the four frozen files plus a rewritten `policy_train.json` into `tmp_path`; mutate one field at a time. Assert `PolicyDataError.code` equals `SOURCE_HASH`, `CANDIDATE_KEYS`, `INELIGIBLE_LABEL` or `SPLIT_LEAKAGE` as appropriate.

- [ ] **Step 5: Run Task 1 tests and existing feature/split tests**

Run: `py -3 -m pytest tests/test_policy_dataset.py tests/test_policy_features.py tests/test_splits.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_dataset_green`

Expected: all pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add training/policy_dataset.py tests/test_policy_dataset.py
git diff --cached --check
git commit -m "feat(A): verify frozen policy training data"
```

---

### Task 2: Validated NumPy learned-policy runtime

**Files:**
- Create: `backend/policies/learned.py`
- Create: `tests/test_learned_policy.py`
- Create: `configs/learned_policy.json`

**Interfaces:**
- Consumes: `encode_observation()`, normalization JSON and named numeric arrays.
- Produces: `score_actions(observation, *, config=None) -> list[CandidateScore]`, `LearnedPolicyError(code, message)`.

- [ ] **Step 1: Write RED tests for complete variable candidate output and structural mask**

Create a real temporary package with finite zero weights, utility bias `0.0`, feasibility bias `0.0`, and correct hashes. With the standard observation fixture assert keys are robust/fast/idle and scores are `0.25`. With an inflight observation assert both send scores are `-1.0` and idle remains finite.

```python
scores = score_actions(observation(), config=package_config)
assert [(row.task_id, row.mode) for row in scores] == [
    ("T1", "robust"), ("T1", "fast"), (None, "idle"),
]
assert [row.score for row in scores] == pytest.approx([0.25, 0.25, 0.25])
```

- [ ] **Step 2: Run and verify RED**

Run: `py -3 -m pytest tests/test_learned_policy.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_runtime_red`

Expected: import fails because `backend.policies.learned` does not exist.

- [ ] **Step 3: Implement strict package loading and NumPy forward pass**

The required array schema is exact:

```python
ARRAY_SHAPES = {
    "layer1_weight": (32, 23), "layer1_bias": (32,),
    "layer2_weight": (16, 32), "layer2_bias": (16,),
    "utility_weight": (1, 16), "utility_bias": (1,),
    "feasibility_weight": (1, 16), "feasibility_bias": (1,),
}
```

Forward computation:

```python
hidden1 = np.maximum(inputs @ w1.T + b1, 0.0)
hidden2 = np.maximum(hidden1 @ w2.T + b2, 0.0)
utility = sigmoid(hidden2 @ wu.T + bu)
feasible = sigmoid(hidden2 @ wf.T + bf)
scores = utility[:, 0] * feasible[:, 0]
scores[~candidate_mask] = -1.0
```

Verify SHA256 before parsing, use `np.load(..., allow_pickle=False)`, require exact array names/shapes/float32 dtype/finite values, require exact normalization feature order/version and finite mean/positive scale, and cache only a completely validated immutable bundle.

- [ ] **Step 4: Add RED tests for controlled failures**

Parameterize missing weights, wrong SHA, extra/missing array, wrong shape, float64 dtype, NaN, normalization feature mismatch and invalid Observation. Assert the exact error codes `MODEL_MISSING`, `MODEL_HASH`, `MODEL_FORMAT`, `MODEL_NONFINITE`, `NORMALIZATION_FORMAT` and `INVALID_OBSERVATION`. Add a missing-RUL success case proving no RUL imputation.

- [ ] **Step 5: Run runtime, gateway and guard tests**

Run: `py -3 -m pytest tests/test_learned_policy.py tests/test_policy_features.py tests/test_policies.py tests/test_policy_runner.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_runtime_green`

Expected: all pass; existing EDF/value behavior unchanged.

- [ ] **Step 6: Commit Task 2**

```powershell
git add backend/policies/learned.py tests/test_learned_policy.py configs/learned_policy.json
git diff --cached --check
git commit -m "feat(A): add validated learned scorer runtime"
```

---

### Task 3: Deterministic trainer and stable non-pickle export

**Files:**
- Create: `training/train_policy.py`
- Create: `tests/test_policy_training.py`
- Modify: `configs/policy_train.json`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `FrozenPolicyDataset`, `Normalization`, three fixed seeds.
- Produces: `CandidateMLP`, `train_seed()`, `evaluate_model()`, `write_deterministic_npz()`, CLI `python -m training.train_policy --config ... --output ...`.

- [ ] **Step 1: Write RED tests for byte-stable export and deterministic training**

```python
def test_deterministic_npz_is_byte_identical(tmp_path):
    arrays = {"layer1_bias": np.zeros(32, dtype=np.float32)}
    left, right = tmp_path / "left.npz", tmp_path / "right.npz"
    write_deterministic_npz(left, arrays)
    write_deterministic_npz(right, arrays)
    assert left.read_bytes() == right.read_bytes()


def test_same_seed_repeats_exact_parameters():
    data = load_frozen_dataset()
    left = train_seed(data, seed=20261031, epochs=20)
    right = train_seed(data, seed=20261031, epochs=20)
    assert left.metrics == right.metrics
    assert all(torch.equal(left.state_dict[key], right.state_dict[key]) for key in left.state_dict)
```

- [ ] **Step 2: Run and verify RED**

Run: `py -3 -m pytest tests/test_policy_training.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_training_red`

Expected: import fails because `training.train_policy` does not exist.

- [ ] **Step 3: Implement deterministic model, weighted loss and metrics**

Use CPU float32, `torch.use_deterministic_algorithms(True)`, and set Python/NumPy/Torch seeds. Each observation contributes total weight 1/N regardless of candidate count. Optimize:

```python
loss = weighted_mse(utility, teacher_scores, row_weights)
loss += 0.25 * weighted_bce(feasibility_logits, feasible, row_weights)
```

Evaluate utility MSE, feasibility accuracy, total loss and teacher-optimal-set hit count per split. Add idle-only and linear least-squares diagnostic baselines without using test data for selection.

- [ ] **Step 4: Implement stable export and CLI preflight**

Write each `.npy` member into a ZIP with fixed member order, fixed timestamp `(1980, 1, 1, 0, 0, 0)`, no pickle and `ZIP_STORED`. Refuse a non-empty output directory. CLI runs seeds `[20261031, 20261032, 20261033]`, selects by `(validation_total_loss, seed)`, checks train MSE ≤ `1e-3` and 12/12 optimal-set hits, evaluates test once, and writes weights, normalization, summary, model card and manifest.

- [ ] **Step 5: Add config and tracked-weight exception**

Extend `configs/policy_train.json` with the exact frozen model/training parameters and keep `training_enabled: false` until Task 4 succeeds. Add narrow `.gitignore` exceptions only for:

```gitignore
!artifacts/
!artifacts/models/
!artifacts/models/a_n3_policy_v1/
!artifacts/models/a_n3_policy_v1/weights.npz
```

- [ ] **Step 6: Run trainer tests and dataset/runtime regression**

Run: `py -3 -m pytest tests/test_policy_training.py tests/test_policy_dataset.py tests/test_learned_policy.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_training_green`

Expected: all pass.

- [ ] **Step 7: Commit Task 3**

```powershell
git add training/train_policy.py tests/test_policy_training.py configs/policy_train.json .gitignore
git diff --cached --check
git commit -m "feat(A): add deterministic policy trainer"
```

---

### Task 4: Run three seeds and freeze the real model package

**Files:**
- Generate: `artifacts/models/a_n3_policy_v1/weights.npz`
- Generate: `artifacts/models/a_n3_policy_v1/normalization.json`
- Generate: `artifacts/models/a_n3_policy_v1/training_summary.json`
- Generate: `artifacts/models/a_n3_policy_v1/model_card.md`
- Generate: `artifacts/models/a_n3_policy_v1/manifest.json`
- Modify: `configs/learned_policy.json`
- Modify: `configs/policy_train.json`
- Create: `docs/evidence/A/A_N3_training_2026-10-31/verification.json`

**Interfaces:**
- Consumes: deterministic trainer and accepted v2 data.
- Produces: the exact frozen package consumed by `score_actions(config=None)`.

- [ ] **Step 1: Run the actual three-seed training command**

Run:

```powershell
py -3 -m training.train_policy `
  --config configs/policy_train.json `
  --output artifacts/models/a_n3_policy_v1
```

Expected: command exits 0, prints all three seed metrics and selected seed, and reports the overfit gate passed. If the fixed gate fails, stop; do not change split, test usage or claim success.

- [ ] **Step 2: Bind runtime config to exact hashes**

Update `configs/learned_policy.json` with generated `weights_sha256`, `normalization_sha256`, `model_version: a-n3-mlp-v1`, `feature_schema_version: policy-features-v1`, package path and masked score `-1.0`. Set `training_enabled: true` only now.

- [ ] **Step 3: Verify default runtime and latency**

Add/execute a verification command that loads each of the 20 observations through `score_actions(config=None)`, checks exact complete keys and finite values, records cold load separately, then measures 1,000 warm calls and records median, p95 and max. Assert no warm call exceeds the 100 ms evidence budget on this machine; do not fold cold load into warm timings.

- [ ] **Step 4: Write committed verification evidence**

`verification.json` records Python/dependency versions, branch/source/data/split/config/weights/normalization hashes, all three seed metrics, selected seed rule, baseline metrics, train gate, test-once statement, artifact inventory, cold/warm timings, targeted test command and the limitations string `synthetic small-sample validation; no generalization or policy-superiority claim`.

- [ ] **Step 5: Run artifact and default-runtime tests**

Run: `py -3 -m pytest tests/test_policy_training.py tests/test_learned_policy.py tests/test_policy_dataset.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_artifact_green`

Expected: all pass against the committed default package.

- [ ] **Step 6: Commit Task 4**

```powershell
git add -f artifacts/models/a_n3_policy_v1/weights.npz
git add artifacts/models/a_n3_policy_v1 configs/learned_policy.json configs/policy_train.json docs/evidence/A/A_N3_training_2026-10-31/verification.json
git diff --cached --check
git commit -m "feat(A): freeze A-N3 small-sample model"
```

---

### Task 5: Failure/fallback evidence, handoff and full verification

**Files:**
- Modify: `tests/test_learned_policy.py`
- Modify: `tests/test_policy_runner.py`
- Create: `docs/handoffs/A_N3_learned_A_2026-10-31.md`
- Modify: `docs/task_board.csv` only for A-owned A-N3 status/evidence fields.

**Interfaces:**
- Consumes: frozen default model and existing `ScorerGateway`/Guard.
- Produces: B-ready handoff with success, missing-RUL, invalid-input, corrupt-weight and gateway fallback evidence.

- [ ] **Step 1: Add RED gateway tests for scorer exception and timeout**

Use the real `ScorerGateway` with a scorer that raises `LearnedPolicyError` and one that blocks beyond a 1 ms budget. Assert EDF fallback is explicit, reason codes are `MODEL_UNAVAILABLE` and `MODEL_TIMEOUT`, late results are not reused, and the returned action still passes Guard.

- [ ] **Step 2: Run RED and confirm the intended gap**

Run: `py -3 -m pytest tests/test_policy_runner.py tests/test_learned_policy.py -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_fallback_red`

Expected: only newly added learned integration assertions fail; existing gateway behavior remains green.

- [ ] **Step 3: Make the minimum compatibility change if required**

Do not change public contracts. If no production change is required because the existing gateway already satisfies the tests, retain the tests as evidence. If a reason propagation defect exists, add the smallest internal runner/gateway fix behind a failing test and keep EDF/value behavior byte-compatible.

- [ ] **Step 4: Write the B handoff and update only A-owned task status**

The handoff lists exact function signature, feature/action order, structural mask, loss scale, model and normalization hashes, selected-seed rule, latency, fallback ownership, five sample classes, tests and explicit non-claims. Mark A-N3 learned scorer `ready_for_B_review`; do not mark B integration, C frontend or formal experiment complete.

- [ ] **Step 5: Run final targeted suite**

Run:

```powershell
py -3 -m pytest `
  tests/test_policy_dataset.py tests/test_policy_training.py `
  tests/test_learned_policy.py tests/test_policy_features.py `
  tests/test_policies.py tests/test_policy_runner.py -q `
  --noconftest -p no:cacheprovider --basetemp=runs/a_n3_final_targeted
```

Expected: all pass without warnings or errors.

- [ ] **Step 6: Run full repository suite with the verified temporary legacy junction**

Run: `py -3 -m pytest -q --noconftest -p no:cacheprovider --basetemp=runs/a_n3_final_full`

Expected: all tests pass. Afterward verify the exact junction target, remove only the junction, and confirm `D:/pro2/交付包` still exists.

- [ ] **Step 7: Verify hashes, tree and non-claims**

Run `git diff --check`, recompute all package SHA256 values, verify frozen v2 files are byte-identical to `2cfe89c`, verify `backend/contracts.py` and `configs/schema.json` are unchanged, and inspect `git status --short` for runtime pollution.

- [ ] **Step 8: Commit Task 5**

```powershell
git add tests/test_learned_policy.py tests/test_policy_runner.py docs/handoffs/A_N3_learned_A_2026-10-31.md docs/task_board.csv
git diff --cached --check
git commit -m "docs(A): hand off learned scorer for B review"
```

Do not push, open a PR or merge until the user explicitly authorizes that external action.
