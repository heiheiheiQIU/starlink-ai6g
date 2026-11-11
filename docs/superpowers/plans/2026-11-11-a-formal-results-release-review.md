# A Formal Results Release Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently verify A-owned model, decision, fallback, and applicability facts for the completed 540-run formal experiment and issue the real-member A release review without rerunning the experiment.

**Architecture:** Export the immutable B formal-result evidence from `a4890579f1d4a2cfb5be9246db6ca46a306fcd39`, bind it to the known result-package and summary hashes, and audit the ZIP directly with a standalone A script. Separate machine verification (`passed`) from the human A release ruling (`accepted_with_notes`), and keep B's original `result_signoff=pending` and `formal_verdict=未完成` unchanged until B creates the unified release object after A/C review.

**Tech Stack:** Python 3 standard library, ZIP/JSON/JSONL/CSV, Git immutable objects, Markdown acceptance records.

## Global Constraints

- Do not rerun the 540 formal policy executions.
- Do not modify B/C evidence, the original `summary.json`, the frozen model, or formal input bytes.
- Do not train a new model, enable Hybrid, or mix recovery-pilot results into this formal batch.
- Preserve the negative result: Learned does not outperform EDF or Value in this registered synthetic out-of-domain batch.
- Distinguish statistical conclusion `negative` from release status `pending` until B produces the gated unified release object.
- Limit applicability to the registered synthetic out-of-domain environment; make no real-orbit, real-6G, hardware, or generalization claim.

---

### Task 1: Build the independent A formal-result audit

**Files:**
- Create: `docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.py`
- Create: `docs/evidence/A/formal_results_2026-11-11/test_A_formal_results_audit.py`
- Create: `docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.json`

**Interfaces:**
- Consumes: `--result-zip PATH`, `--source-commit SHA`, and optional `--output PATH`.
- Produces: deterministic JSON containing source/package bindings, run and trajectory counts, policy metrics, model identity, Learned decision/fallback facts, score-margin facts, statistical comparisons, applicability fields, checks, and `release_approved=false`.

- [ ] **Step 1: Export the immutable B result package**

Run:

```powershell
$reviewRoot = Join-Path $env:TEMP 'starlink-a-formal-results-review'
New-Item -ItemType Directory -Force -Path $reviewRoot | Out-Null
git archive a4890579f1d4a2cfb5be9246db6ca46a306fcd39 --output="$env:TEMP/starlink-a-formal-results-review.tar" docs/evidence/B/delegated_execution_2026-11-10
& 'C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -c "import tarfile,sys;tarfile.open(sys.argv[1]).extractall(sys.argv[2],filter='data')" "$env:TEMP/starlink-a-formal-results-review.tar" $reviewRoot
```

Expected: the result ZIP exists at `docs/evidence/B/delegated_execution_2026-11-10/formal_v2_delegated_results_20261110.zip`; no tracked A/B/C file changes.

- [ ] **Step 2: Write mutation tests before the audit script**

The tests must require rejection of:

```text
wrong source commit
result ZIP SHA mismatch or corrupt ZIP member
wrong frozen code/model/summary/run-index binding
missing, duplicate, retried, or non-completed policy run
Learned action other than idle
Learned fallback=true or malformed fallback field
missing or duplicate Learned decision event
chosen action not matching the highest finite candidate score
summary metric, comparison, decision-count, or applicability mismatch
```

The positive test must run the real CLI twice and require byte-identical JSON.

- [ ] **Step 3: Implement the standard-library audit**

Bind these exact immutable facts:

```python
SOURCE_COMMIT = "a4890579f1d4a2cfb5be9246db6ca46a306fcd39"
RESULT_ZIP_SHA256 = "efa801d9dde6a9eb340ca0a27b873027248edbcadd7b85c82cdd3847ab5f9e86"
SUMMARY_SHA256 = "872a71029783ca4100ed8d4e6cfec79261f9c7eaaca65b10362ce53a9ffdbae9"
FROZEN_CODE_REVISION = "48157a8f4a1cdd7770685b79deb3fe4524b1bf7d"
MODEL_VERSION = "a-n3-mlp-v1"
MODEL_WEIGHTS_SHA256 = "a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a"
FROZEN_MANIFEST_SHA256 = "3ad4bfeaf5398012bae17cab4bf684fb5a80ce0b5e341bf5e9eda4d179104d30"
RUN_INDEX_SHA256 = "5d9c58585cd6782c3d898f2fc690829ae3a04956f9844e9ad6c389ea7d408ade"
```

Audit all 540 completed run identities and all Learned `decision` events. Require 180 trajectories, 18 cells × 10 trajectories, 180 runs per policy, attempt `1`, zero failures/missing/retries, 2160 Learned decisions, 2160 idle actions, and zero fallbacks. For every Learned decision, independently verify finite candidate scores, exactly one idle candidate, chosen idle is a maximum-score candidate, and record the idle-versus-best-send margin distribution.

- [ ] **Step 4: Recompute the published metrics and comparisons**

From the package's 540-row metrics table and 360-row paired table, independently derive:

```text
EDF weighted on-time rate = 0.4653873291265777
Value weighted on-time rate = 0.5114726389809670
Learned weighted on-time rate = 0.0
Learned−EDF mean = -0.4653873291265777, CI [-0.49422782912931634, -0.43592598002654237]
Learned−Value mean = -0.5114726389809671, CI [-0.5385503136194323, -0.4831265616824757]
```

Require the original summary to retain `result_signoff=pending`, comparison `formal_verdict=未完成`, and statistical verdict `负`.

- [ ] **Step 5: Generate deterministic A evidence**

Run the audit twice with the bundled Python interpreter, compare bytes, and copy the canonical output to `A_formal_results_audit.json`. The JSON must state `machine_audit.status=passed`, `A_ruling=pending`, and `release_approved=false`.

### Task 2: Issue the real-member A formal-result review

**Files:**
- Create: `docs/acceptance/A_formal_results_release_review_2026-11-11.md`

**Interfaces:**
- Consumes: `docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.json` and the frozen model card/training summary bound by the result ZIP.
- Produces: A's signed-scope review for B's gated release process, plus a material/defense boundary.

- [ ] **Step 1: Record the review objects and hashes**

List the B evidence commit, result ZIP, summary, frozen manifest, run index, frozen code revision, model version, weights, normalization, and training-summary hashes. Bind the A review to the same objects as C's `d9673126b41a678b6f83142b258fb4e8475d0bb5` review without copying C's conclusion.

- [ ] **Step 2: State the A ruling and verified facts**

Open with:

```text
A_ruling=accepted_with_notes
machine_audit.status=passed
```

Confirm the 540/540 technical execution, frozen model identity, 2160/2160 idle actions, zero fallback, policy metrics, negative paired comparisons, and zero energy violations. Keep original release status pending and authorize only B's generation of a separate gated unified release summary after combining A/C reviews.

- [ ] **Step 3: Explain all-idle without overstating causality**

Separate verified observations from interpretation:

```text
Verified: 12/4/4 small-sample split; weak validation/test feasibility and utility metrics; formal domain registered as out of zero-loss training domain; idle is top-scored at every recorded decision; no runtime fallback.
Interpretation: small-sample overfit and domain shift are evidence-supported contributors to conservative idle saturation, not a controlled causal proof.
```

Do not describe the result as a loading failure, Guard fallback, missing model, or proof that all learned approaches fail.

- [ ] **Step 4: Define material and defense boundaries**

Allow: real negative formal result, failure detection, release governance, deterministic constraints, traceability, protocol/sandbox engineering value. Prohibit: AI beats baselines, real-orbit/real-6G benefit, Hybrid as a formal policy, retrained-model substitution, or manual edits to the original summary.

- [ ] **Step 5: Provide the B handoff**

Require B to consume the A and C review records, generate one tested release object, preserve original evidence bytes, and avoid rerunning 540 executions. State that A's review does not itself flip the original `result_signoff` field.

### Task 3: Verify and commit the A release review

**Files:**
- Verify: `docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.py`
- Verify: `docs/evidence/A/formal_results_2026-11-11/test_A_formal_results_audit.py`
- Verify: `docs/evidence/A/formal_results_2026-11-11/A_formal_results_audit.json`
- Verify: `docs/acceptance/A_formal_results_release_review_2026-11-11.md`
- Verify: `docs/superpowers/plans/2026-11-11-a-formal-results-release-review.md`

**Interfaces:**
- Consumes: all Task 1 and Task 2 outputs.
- Produces: one reviewable A commit series; no push unless separately requested.

- [ ] **Step 1: Run all A formal-result audit tests**

Run:

```powershell
& 'C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest discover -s docs/evidence/A/formal_results_2026-11-11 -p 'test_*.py' -v
```

Expected: all positive, mutation, and deterministic-output tests pass.

- [ ] **Step 2: Run the audit against a fresh immutable export**

Re-export `a4890579...`, run the CLI, and require byte identity with the committed JSON. Verify the acceptance document includes the committed JSON SHA, exact release markers, negative metrics, scope limits, and B handoff.

- [ ] **Step 3: Check scope and whitespace**

Run:

```powershell
git diff --check
git status --short
git diff --name-only f288d14374cd7d08e8e83ecc5cefd132c848b473..HEAD
```

Expected: only the A evidence directory, A acceptance record, and this plan are changed. No B/C, formal package, model, training, frontend, report, or PPT file changes.

- [ ] **Step 4: Commit the A review**

Run:

```powershell
git add docs/evidence/A/formal_results_2026-11-11 docs/acceptance/A_formal_results_release_review_2026-11-11.md docs/superpowers/plans/2026-11-11-a-formal-results-release-review.md
git commit -m "docs(A): review formal results for gated release"
```

Expected: working tree clean; branch remains local until the user chooses a push/PR option.
