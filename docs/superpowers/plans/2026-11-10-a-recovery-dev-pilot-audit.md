# A Recovery Development Pilot Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently audit B's `b-recovery-dev-v1` 30-source/60-state pilot and issue an A-owned coverage, leakage, and training-gate ruling without retraining or modifying B/C interfaces.

**Architecture:** Audit the immutable remote snapshot `origin/codex/b-finalize-receipts-20261110@a2e0be4b579b5d4cb797bdc826c077e551d985f6` from a temporary export. A standalone A evidence script will validate hashes, identities, source-level splitting, label invariants, coverage counts, and declared leakage scope without importing B's audit implementation; its machine-readable output will feed a human-readable A ruling.

**Tech Stack:** Python 3 standard library, Git object export, JSON/JSONL, pytest for existing regression checks, Markdown acceptance records.

## Global Constraints

- Do not train a model, enable Hybrid, replace `a-n3-mlp-v1`, or modify formal result artifacts.
- Do not edit B/C-owned interfaces or source evidence.
- Treat `b-recovery-dev-v1` as development-only and keep `training_enabled=false`.
- Keep formal 540-run results and the recovery pilot as separate evidence domains.
- Preserve negative findings and incomplete coverage; do not convert them into algorithm-benefit claims.

---

### Task 1: Build an independent A audit tool

**Files:**
- Create: `docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.py`
- Test: temporary export of `origin/codex/b-finalize-receipts-20261110@a2e0be4b579b5d4cb797bdc826c077e551d985f6`

**Interfaces:**
- Consumes: `--pilot-dir PATH`, `--source-commit SHA`, and optional `--output PATH`.
- Produces: JSON containing `status`, snapshot SHA, file hashes, identity/split/leakage checks, decision and coverage counts, gaps, and `training_approved=false`.

- [ ] **Step 1: Export the immutable B snapshot**

Run from the repository root:

```powershell
$auditRoot = Join-Path $env:TEMP 'starlink-a-recovery-audit'
New-Item -ItemType Directory -Force -Path $auditRoot | Out-Null
git archive a2e0be4b579b5d4cb797bdc826c077e551d985f6 | tar -xf - -C $auditRoot
```

Expected: `$auditRoot/docs/evidence/B/recovery_dev_2026-11-10/pilot/manifest.json` exists and the current A worktree remains unchanged.

- [ ] **Step 2: Write the independent audit script**

Implement standard-library checks for:

```python
EXPECTED_SOURCE_COUNT = 30
EXPECTED_STATE_COUNT = 60
EXPECTED_SPLITS = {"train": 18, "validation": 6, "test": 6}
EXPECTED_SEEDS = set(range(710000, 710030))
REQUIRED_FAMILIES = {"wait_then_send", "last_chance", "task_conflict", "must_wait"}
```

The script must fail closed when any manifest hash, source/state identity, source-level split, unique seed, unique content hash, unique semantic observation, label content hash, solver status, teacher binding, or declared exclusion-evidence hash differs. It must count non-zero loss, in-flight, long-horizon, strict-wait-better, tied, send-better, and no-feasible-send states and must never set `training_approved=true`.

- [ ] **Step 3: Execute the audit twice**

Run:

```powershell
python docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.py --pilot-dir "$auditRoot/docs/evidence/B/recovery_dev_2026-11-10/pilot" --repo-root $auditRoot --source-commit a2e0be4b579b5d4cb797bdc826c077e551d985f6 --output "$auditRoot/audit-first.json"
python docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.py --pilot-dir "$auditRoot/docs/evidence/B/recovery_dev_2026-11-10/pilot" --repo-root $auditRoot --source-commit a2e0be4b579b5d4cb797bdc826c077e551d985f6 --output "$auditRoot/audit-second.json"
```

Expected: both commands exit 0; after excluding an optional execution timestamp, outputs are byte-identical and report 30 sources, 60 states, 18/6/6 source splits, and `training_approved=false`.

- [ ] **Step 4: Copy the verified output into A evidence**

Copy the deterministic JSON result to:

```text
docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.json
```

Record the source commit and every consumed evidence SHA in the JSON.

### Task 2: Issue the A coverage and training-gate ruling

**Files:**
- Create: `docs/acceptance/A_recovery_dev_label_coverage_review_2026-11-10.md`

**Interfaces:**
- Consumes: `docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.json`.
- Produces: an A-owned ruling for B/C with explicit approved and unapproved scopes.

- [ ] **Step 1: Write the factual audit table**

Include source commit, file hashes, 30/60 counts, 18/6/6 source split, family distribution, teacher/solver status, label decision counts, and leakage scope. Distinguish independently recomputed facts from B's self-reported `1703` checks.

- [ ] **Step 2: Record the coverage gaps**

Explicitly state whether the pilot contains:

```text
strictly-wait-better states
non-zero packet/ACK loss
in-flight or retransmission state
long-horizon state beyond the two-capture short trajectory
```

If any count is zero, keep the training gate closed and do not infer generalization.

- [ ] **Step 3: Define the minimum supplementation contract**

Require a new version and directory, source-level train/validation/test isolation, new seed range, separately registered held-out evaluation, and targeted coverage for every missing state family. Preserve the existing pilot and formal result bytes.

- [ ] **Step 4: State the A ruling**

The allowed conclusion is limited to label/integrity acceptance if all checks pass. `training_enabled` remains `false`; no Hybrid integration, model replacement, or AI-benefit claim is authorized.

### Task 3: Verify and commit the A audit

**Files:**
- Verify: `docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.py`
- Verify: `docs/evidence/A/recovery_dev_2026-11-10/A_recovery_dev_audit.json`
- Verify: `docs/acceptance/A_recovery_dev_label_coverage_review_2026-11-10.md`
- Verify: `docs/superpowers/plans/2026-11-10-a-recovery-dev-pilot-audit.md`

**Interfaces:**
- Consumes: all Task 1 and Task 2 outputs.
- Produces: one reviewable A commit; no push unless separately requested.

- [ ] **Step 1: Run B's frozen pilot regression in the exported snapshot**

Run:

```powershell
python -m pytest -q tests/test_recovery_pilot.py
python training/audit_recovery_pilot.py --input docs/evidence/B/recovery_dev_2026-11-10/pilot
```

Expected: tests pass; B's audit reports `status=passed`, `checks=1703`, and `training_enabled=false`.

- [ ] **Step 2: Run the A audit gate from the current worktree**

Run the Task 1 command and assert the machine audit and A ruling separately:

```text
machine_audit.status=passed
A_ruling=accepted_with_notes
source_commit=a2e0be4b579b5d4cb797bdc826c077e551d985f6
training_approved=false
formal_results_modified=false
```

- [ ] **Step 3: Review the diff and repository status**

Run:

```powershell
git diff --check
git status --short
git diff -- docs/evidence/A/recovery_dev_2026-11-10 docs/acceptance/A_recovery_dev_label_coverage_review_2026-11-10.md docs/superpowers/plans/2026-11-10-a-recovery-dev-pilot-audit.md
```

Expected: only A-owned evidence, acceptance, and plan files appear.

- [ ] **Step 4: Commit the audit**

Run:

```powershell
git add docs/evidence/A/recovery_dev_2026-11-10 docs/acceptance/A_recovery_dev_label_coverage_review_2026-11-10.md docs/superpowers/plans/2026-11-10-a-recovery-dev-pilot-audit.md
git commit -m "docs(A): audit recovery development pilot"
```

Expected: a single commit on `codex/a-final-sprint-review-20261107`; the working tree is clean and no remote push has occurred.
