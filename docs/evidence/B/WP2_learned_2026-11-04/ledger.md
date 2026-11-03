# WP2 ledger — plan: docs/superpowers/plans/2026-11-02-project-optimization.md (WP2)

- Baseline 0638428: latest B readiness branch after fetch; preserve original branches and shared main.
- Scope: learned Runner/Guard, bounded same-level inference supervisor, five APIs, identity and paired development comparison; no retraining or formal benchmark.
- RED: new inference lifecycle module missing; runner complete-set/model tests absent. Core GREEN: 16 passed.
- API RED: learned requests rejected (422) and server model configuration unsupported. GREEN after registration: old test assuming learned invalid now reaches capacity (429); use unknown policy for invalid-request test because capability intentionally changed.
- Lifecycle: timeout, worker crash, service close/run timeout, abrupt server death, persistent status-read lock tested; 41 selected tests passed.
- Ruling: crash detection test gets 1000ms, separate 30ms hung-score test retained; Windows teardown can outlast 30ms. Does not relax production 100ms budget.
- Provenance RED: three failures for missing inference/feature source hashes, retry score overwriting, and rereading mutated model config; all fixed and 26 selected tests passed.
- Runtime fields remain immutable once config is written; changing execution statistics live only in manifest diagnostics, not hashed config.
- Model package/A frozen code, contracts, schema and frontend unchanged. Two-policy limit retained; repeated EDF in paired requests is not an independent sample.

- Final review: 6 Important + 1 diagnostic issue; failure regressions 7 failed/19 passed/1 Linux skip; one fix pass to GREEN, then full 552 passed/1 skipped/1 existing warning.
- Fix: startup-gate parent death, persistent status monitor, export manifests/hash snapshots, trusted model manifest, all-structural-mask fallback; Linux zombie parser included with Linux-only test skipped on Windows.
- Ruling: diagnostic missing-model error treated as required behavior and fixed; old package and contract frozen.
- Production runtime commit 5411fefa5f91b10ecc40b1203347a6fa7159334b; final HTTP two paired requests verified, no AI performance claim.
