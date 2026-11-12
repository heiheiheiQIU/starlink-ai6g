# A Formal V2 Candidate Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record A's independent post-generation provenance and split review for the 180 formal_v2 candidates without prematurely authorizing 540 formal runs.

**Architecture:** Keep B/C's candidate packet immutable and review it from the frozen `48157a8` source. Publish an A-owned human-readable receipt plus a compact machine-readable receipt, then correct only A-owned documents whose “missing C receipt / candidates not generated” statements are now stale.

**Tech Stack:** Git, PowerShell, Python 3.12, pytest, Markdown, JSON.

## Global Constraints

- Do not modify B/C interfaces or their pending `review/A.json`, `review/B.json`, `review/C.json` files.
- Do not authorize formal runs until A/B/C bind one final accepted leakage file SHA256.
- Do not add Hybrid, retrain A-N4b, replace the frozen model, or alter the statistical protocol.
- Keep all formal performance claims pending while executed formal runs remain `0/540`.

---

### Task 1: Freeze and verify the review subject

**Files:**
- Read: `docs/evidence/B/formal_v2_candidate_2026-11-09/`
- Read: frozen source at commit `48157a8f4a1cdd7770685b79deb3fe4524b1bf7d`

**Interfaces:**
- Consumes: B candidate manifest, A/B/C generation receipts, frozen generator and review scripts.
- Produces: independently verified hashes, inventory counts, and test evidence used by Task 2.

- [x] **Step 1: Verify the candidate with the frozen generator**

Run `python -m backend.formal_v2 --verify <packet>/candidate/manifest.json` from the exported frozen source.

- [x] **Step 2: Regenerate the candidate from the three original receipts**

Run `python -m backend.formal_v2 --receipts <packet>/generation --output <new-temp-directory>` and compare all 182 files byte-for-byte.

- [x] **Step 3: Rebuild the provenance review**

Run `python -m scripts.prepare_formal_v2_review --candidate <packet>/candidate/manifest.json --output <new-temp-directory>` and compare the resulting leakage JSON with the delivered draft.

- [x] **Step 4: Run the formal-chain regression tests**

Run the eight formal, split, policy-feature, and learned-policy test modules. Expected: zero failures.

### Task 2: Publish A's second-stage review

**Files:**
- Create: `docs/acceptance/A_formal_v2_candidate_provenance_review_2026-11-10.md`
- Create: `docs/acceptance/A_formal_v2_candidate_provenance_review_2026-11-10.json`

**Interfaces:**
- Consumes: Task 1 evidence and the A-N3/A-N4b split manifests.
- Produces: A-owned `accepted_with_notes` candidate provenance verdict; does not substitute for the final formal-freeze receipt.

- [x] **Step 1: Record the exact review subject and hashes**

Include B `b4faac9`, C `d98052d`, generation code `48157a8`, candidate manifest `2b0814db...`, binding `d2b596d8...`, and leakage draft `8bc1909e...`.

- [x] **Step 2: Record source and split findings**

Document A-N3 12/4/4 source-group separation, A-N4b 18/6/6 separation, excluded seed/content counts, observation-projection overlap zero, and the missing legacy scenario-seed limitation.

- [x] **Step 3: Keep the authorization gate closed**

Set `formal_runs_authorized=false` and state that the final accepted leakage bytes plus A/B/C formal receipts are still required.

### Task 3: Correct stale A-owned status statements

**Files:**
- Modify: `docs/acceptance/B_sandbox_delivery_A_2026-11-09.md`
- Modify: `docs/acceptance/ABC_learned_zero_recovery_A_2026-11-09.md`
- Modify: `docs/handoffs/A_golden_scenario_ai_review_2026-11-09.md`

**Interfaces:**
- Consumes: Task 2 verdict.
- Produces: consistent A documentation that distinguishes pre-generation receipt completion, candidate generation, second-stage review, and formal-run authorization.

- [x] **Step 1: Mark the original C receipt blocker resolved**

State that all three pre-generation receipts bind the same subject and the 180 candidates now exist.

- [x] **Step 2: Preserve the remaining gate**

State that final leakage-byte agreement and A/B/C formal receipts remain pending; `0/540` runs have executed.

- [x] **Step 3: Verify and commit**

Run `git diff --check`, assert the new receipts contain `formal_runs_authorized=false`, and inspect the final diff before committing.
