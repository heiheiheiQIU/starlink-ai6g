# A3 Golden Scenario AI Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver A's evidence-grounded AI expectation review for S1/S2/S3 while keeping the missing sandbox compiler and golden run packages visible as acceptance gaps.

**Architecture:** Separate mechanism evidence from scenario acceptance. Use B's implemented feature, Guard, runner, and protocol behavior to define what each scenario may show; require B's future compiled configs and run packages before accepting any actual scene outcome.

**Tech Stack:** Markdown, Git object inspection, Python/pytest, pnpm/Vitest/Vite.

## Global Constraints

- Do not treat old `r3_*` manual scenarios or development case packets as the new sandbox golden run packages.
- Do not promise Learned superiority or a different final action in any scenario.
- Attribute scoring to A's frozen scorer, feasibility to Guard, and ACK/retransmission/de-duplication to B's protocol and retry controller.
- Keep `rul_est=null` and post-hoc truth out of policy claims.
- Do not change B's scenario compiler or C's frontend mapping from the A branch.

---

### Task 1: Audit available mechanism and scenario evidence

**Files:**
- Read: `configs/scenarios/r3_*.json` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/policies/common.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/policies/runner.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `backend/simulator/protocol.py` and `backend/simulator/r3_engine.py` from `origin/codex/b-final-sprint-review-20261107`
- Read: `tests/test_policy_runner.py` and `tests/test_learned_integration.py` from `origin/codex/b-final-sprint-review-20261107`

**Interfaces:**
- Consumes: B commit `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d` and the v2.0 sprint plan's S1/S2/S3 definitions.
- Produces: Mechanism facts and acceptance gaps for Task 2.

- [x] **Step 1: Search for the sandbox axis compiler and golden packages**

Expected: the reviewed B commit does not contain `compile_sandbox_axes`, `kind="sandbox_axes"`, or S1/S2/S3 run packages.

- [x] **Step 2: Verify low-energy behavior**

Confirm that health lower-bound features enter the scorer and `energy_lower_Wh` enters Guard's `ENERGY_RESERVE` check. Treat the low-energy unit test as mechanism evidence only.

- [x] **Step 3: Verify ACK and retry ownership**

Confirm that ACK loss, timeout, retransmission, duplicate detection, and ACK completion are protocol/runner behavior, not model inference.

### Task 2: Author the A3 scenario review

**Files:**
- Create: `docs/handoffs/A_golden_scenario_ai_review_2026-11-09.md`

**Interfaces:**
- Consumes: Task 1 findings and the A2 semantics handoff.
- Produces: Scene-by-scene observable changes, forbidden promises, C copy guidance, and B evidence requirements.

- [x] **Step 1: Review S1 resource-abundant semantics**

Allow policy agreement and idle ties; prohibit claims of mandatory Learned improvement, zero fallback, or AI-driven visual differences.

- [x] **Step 2: Review S2 low-energy/deadline-conflict semantics**

Describe the health-feature and Guard paths separately, require internally consistent compiled health fields, and prohibit attributing Guard refusal to model capability.

- [x] **Step 3: Review S3 ACK-loss semantics**

Define the expected protocol event chain and explicitly state that retransmission is not AI inference.

- [x] **Step 4: Record the acceptance verdict and recheck packet**

Keep runtime acceptance at `changes_requested` until B supplies compiled configs, run IDs, hashes, events, metrics, and provenance for all three scenes.

### Task 3: Verify the handoff

**Files:**
- Verify: `docs/handoffs/A_golden_scenario_ai_review_2026-11-09.md`

**Interfaces:**
- Consumes: Task 2 handoff.
- Produces: A reviewable A3 commit candidate.

- [x] **Step 1: Check required scene sections and ownership language**

Search for S1/S2/S3, observable changes, prohibited claims, scorer/Guard/protocol ownership, and `changes_requested`.

- [x] **Step 2: Check for overclaims and evidence substitution**

Ensure old manual fixtures are labeled development/mechanism evidence and no scene is described as accepted without a new run package.

- [x] **Step 3: Run diff and repository verification**

Run `git diff --check`, the repository tests, frontend tests, and production build before committing.
