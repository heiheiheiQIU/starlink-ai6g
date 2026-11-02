# C Live Run Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing high-fidelity frontend reproducible on a fresh machine and able to inspect a real backend run without weakening the approved fixture/evidence boundaries.

**Architecture:** Keep pnpm as the single package manager because the repository already freezes `pnpm-lock.yaml`. Extend the typed run client with explicit response-format and abort behavior, then add a self-contained live-run inspector to the evidence page; the rest of the application remains visibly fixture-backed until B exposes a frozen scenario-preset creation contract.

**Tech Stack:** React 18, TypeScript 5.9, Vite 6, Vitest, Testing Library, pnpm 9 lockfile.

**Spec:** `docs/ui_structure.md` (v5, especially sections 4, 7, 8, and 9.2)

## Global Constraints

- Preserve the user-approved six-step experience, visual hierarchy, animations, and all six navigation entries.
- Never display final metrics for queued, running, failed, cancelled, offline, or malformed responses.
- Fixture content keeps the global `FIXTURE / 非实验结果` banner; live-run content receives its own source label.
- Do not fabricate a run-list endpoint, scenario-preset endpoint, learned policy, or experiment result.
- Do not add a second lockfile; pnpm is the repository package manager.
- Do not merge or push as part of this plan.

## Review Focus

- A successful HTTP response containing malformed JSON must become an explicit response-format failure, not an uncaught `SyntaxError`.
- Aborting while poll delay is active must stop promptly instead of waiting for the entire interval.
- Refresh recovery must restore only a run ID, then re-fetch authoritative backend state.
- A running or failed run must never trigger result retrieval or show final metrics/export controls.
- Event pagination must stop on `has_more=false` and preserve backend ordering without cross-policy recomputation.

---

### Task 1: Freeze the frontend toolchain

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/README.md`

**Interfaces:**
- Consumes: existing `frontend/pnpm-lock.yaml`
- Produces: one documented fresh-machine command path based on `pnpm install --frozen-lockfile`

- [ ] Add the exact pnpm package-manager declaration and deterministic `test:run` / `check` scripts.
- [ ] Document install, test, build, offline-demo, and backend-base-URL commands without introducing npm lockfiles.
- [ ] Run `pnpm install --frozen-lockfile`, `pnpm test:run`, and `pnpm build`.

### Task 2: Harden the typed run client

**Files:**
- Modify: `frontend/src/api/runs.test.ts`
- Modify: `frontend/src/api/runs.ts`

**Interfaces:**
- Produces: `ResponseFormatError`, abort-aware polling, and `getAllEvents(runId, pageLimit)`.

- [ ] Write failing tests for malformed successful JSON, abort during delay, and multi-page event collection.
- [ ] Run the focused tests and verify the expected failures.
- [ ] Implement the smallest client changes that satisfy those behaviors without runtime scientific validation.
- [ ] Run the focused and complete frontend test suites.

### Task 3: Add the real-run inspector

**Files:**
- Create: `frontend/src/components/LiveRunInspector.test.tsx`
- Create: `frontend/src/components/LiveRunInspector.tsx`
- Modify: `frontend/src/pages/EvidencePage.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: `RunApi`, `RunStatusResponse`, `RunResult`, and `EventsPage`.
- Produces: a run-ID-driven inspector with live/offline/error/loading/queued/running/completed/failed states and completed-only export.

- [ ] Write failing component tests for completed retrieval, running-result suppression, offline recovery messaging, failed-state preservation, pagination, export, and local-storage run-ID restoration.
- [ ] Run the focused tests and verify they fail because the component is absent.
- [ ] Implement the component and embed it in the evidence page without replacing fixture examples.
- [ ] Add responsive styles that preserve 1920×1080 and 1366×768 layouts and reduced-motion behavior.
- [ ] Run focused and complete tests plus the production build.

### Task 4: Record reproducibility and visual QA evidence

**Files:**
- Create: `docs/evidence/C/frontend_readiness_2026-10-30/README.md`
- Create: `docs/evidence/C/frontend_readiness_2026-10-30/verification.json`
- Modify: `docs/task_board.csv`

**Interfaces:**
- Consumes: final command outputs and browser observations.
- Produces: auditable C-N2/C-N3 evidence without claiming end-to-end backend integration.

- [ ] Run a frozen-lock install, full tests, type/build verification, and record exact tool versions/counts.
- [ ] Start the local preview and inspect the representative evidence/run flow at 1920×1080 and 1366×768, including reduced motion.
- [ ] Record what is verified and the remaining B-dependent limits; update only C-owned task-board fields without overwriting A/B status.
- [ ] Run `git diff --check`, the full frontend suite, and the production build.
