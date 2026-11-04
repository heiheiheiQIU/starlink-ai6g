# SDD ledger — plan: docs/superpowers/plans/2026-11-04-wp5-experiment-readiness.md
Scope: Task 1, model-independent input delivery. Tasks 2–4 require later model/statistical review gates.
Base: f3c6938
Pre-flight: Task 1 supplies manifest and hashes to Task 2/3; pending model rejects formal execution. Task 4 consumes unique trajectory-policy records.
Ruling: reuse current checkout on own new branch per desktop preference; no extra worktree needed.
Ruling: define load by 4/12/20 KiB-blocks offered versus optimistic 12-block capacity in 24s at decision_dt=2s. 2/6/10 tasks each 2048B, all arrive at zero. Deadlines sampled before outcomes, 8/12/18/24s. Costs: labels describe offered aggregate load, not guarantee deadline feasibility.
Ruling: Task 1 delivered as candidate with model pending and A-N4b leakage audit pending. New package cannot be frozen until A sources arrive.
Ruling: discrete priorities produced duplicate seed-stripped scenarios in first green run; use uniform [1,3] priorities with same independent task RNG before evaluating outcomes. Cost: priority distribution changes from original draft.
Review: fresh gpt-6-astra high, 5 Important accepted. 8 reproducing tests RED (8 failed/9 passed) -> GREEN17. Fixed manifest/protocol semantics, raw protocol SHA, junction and extra inventory, loaded code/source matching, preregistered generation rules.
Final: minor (deferred): collision errors reject safely but lack conflicting row/value details.
Task1 implementation ready_for_review; A-N4b cross-provenance review pending external delivery.
Source-constant regression RED1 failed/1 passed -> import snapshot pin. Task1 candidate and receiver handoff implemented.

Task1: ready_for_review. Final full suite570 passed1skip1warning. A-N4b lineage gate remains pending.
