# A2 Interactive AI Event Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver A's evidence-grounded event semantics handoff for the interactive sandbox without claiming that the missing two-health-run machine gate has passed.

**Architecture:** Treat B's published integration commit as the implementation source of truth, then separate semantic acceptance from runtime machine acceptance. Reuse the three published development cases only with their original development-only labels and record a precise B-side recheck request for the unmet health-difference gate.

**Tech Stack:** Markdown, Git object inspection, Python/pytest, pnpm/Vitest/Vite.

## Global Constraints

- Do not train A-N4b, create new weights, or replace `a-n3-mlp-v1`.
- Do not modify B/C interfaces or copy B implementation into the A branch.
- Keep formal, sandbox, fixture, and development-only evidence scopes distinct.
- Preserve `rul_est=null` and its reason code when native RUL is unavailable.
- Never present injected scores, fault injection, or sandbox output as a formal result.

---

### Task 1: Verify the implementation and evidence sources

**Files:**
- Read: `backend/policies/learned.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/policies/guard.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/policies/runner.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/api/inference.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `training/policy_features.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `docs/evidence/B/independent_2026-11-07/` from `origin/codex/b-final-sprint-review-20261107`

**Interfaces:**
- Consumes: B commit `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d` and H00 contract semantics.
- Produces: Verified model identity, score/Guard/fallback semantics, and evidence-scope findings for Task 2.

- [x] **Step 1: Confirm the A branch starts clean**

Run: `git status --short --branch`

Expected: branch `codex/a-final-sprint-review-20261107` with no file changes.

- [x] **Step 2: Run the current baseline**

Run: `D:\pro2\.venv\Scripts\python.exe -m pytest -q`, `pnpm test:run`, and `pnpm build`.

Expected: 61 Python tests, 77 frontend tests, and the production build pass.

- [x] **Step 3: Verify actual model and policy identity**

Check that the trusted manifest, model configuration, inference supervisor, and runner agree on `a-n3-mlp-v1`, weights SHA `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a`, and policy version `learned-r4-v1`.

- [x] **Step 4: Verify the three examples and health-run inventory**

Check one trained-model decision, the injected Guard rejection, and the corrupt-NPZ fallback. Inventory all published HTTP requests and compare their first `HealthEstimate` values.

Expected: all published Learned HTTP evidence uses the same health values, so the two-health-run machine gate remains unmet.

### Task 2: Author the A2 handoff

**Files:**
- Create: `docs/handoffs/A_interactive_ai_event_semantics_2026-11-09.md`

**Interfaces:**
- Consumes: Task 1 findings and `docs/contracts/README.md`.
- Produces: A-facing field semantics, C display rules, three scoped examples, and an exact B recheck request.

- [x] **Step 1: Document frozen model loading and provenance**

Record where `model_version`, weights/model hash, normalization hash, policy version, and decision-event fields originate. State that a decision event does not itself carry the model hash.

- [x] **Step 2: Document candidate and Guard semantics**

Define `idle`, `robust`, `fast`, `task_id`, structural masking, Guard checks, tie behavior, and the boundary between AI scoring and executable action selection.

- [x] **Step 3: Document fallback and information boundaries**

Separate trusted API startup refusal from in-run fallback; describe current reason-code behavior. List public Observation fields and post-hoc-only truth, including the null-RUL rule.

- [x] **Step 4: Add the three evidence examples**

Include a trained-model normal decision, an explicitly injected high-score Guard rejection, and a corrupt-package EDF fallback. Preserve run IDs, event IDs, commit identity, and development-only labels.

- [x] **Step 5: Record the machine-gate verdict**

Set overall status to `changes_requested` until B supplies two real sandbox Learned runs with different health inputs and shows the difference in Observation plus candidate scores or Guard checks.

### Task 3: Verify and review the handoff

**Files:**
- Verify: `docs/handoffs/A_interactive_ai_event_semantics_2026-11-09.md`

**Interfaces:**
- Consumes: Task 2 handoff.
- Produces: A clean, reviewable A2 commit candidate.

- [x] **Step 1: Check required semantics and scope labels**

Run repository searches for the seven required semantic topics, three example labels, `development_only`, `rul_est`, and the machine-gate verdict.

- [x] **Step 2: Check forbidden overclaims**

Search the new handoff for claims that A-N4b trained successfully, Learned is superior, results are formal, or RUL was reconstructed. Any occurrence must be explanatory or prohibitive, not an affirmative claim.

- [x] **Step 3: Review the diff and working tree**

Run: `git diff --check`, `git diff -- docs/handoffs/A_interactive_ai_event_semantics_2026-11-09.md`, and `git status --short`.

Expected: no whitespace errors and only the plan plus A2 handoff are changed.
