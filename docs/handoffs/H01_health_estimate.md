# H01 HealthEstimate handoff

Date: 2026-10-29. Status: `ready_for_review`; not accepted by B.

Source revision (Task 3): `744b4062c320b875fb860a4c60556a8add709f4f`.
The verified evidence commit is `5871a64abaf0a7b03d03aeca6579b7de59f63e45`.

## Frozen adapter

`backend.health.estimator.estimate_health(history: list[dict], now_s: float) -> backend.contracts.HealthEstimate`
returns the frozen `HealthEstimate` contract. It loads
`configs/health_observation.json` relative to the module. Observations must be
explicitly synthetic SOC/capacity observations; SOC is a 0–1 fraction, capacity
and energy are Wh, and timestamps are seconds. Records with `available_at_s >
now_s` are excluded. RUL unavailable remains `null` with `RUL_UNAVAILABLE`.
This synthetic adapter does not consume legacy checkpoint `raw_fraction`.

## Evidence

Verified evidence directory: `docs/evidence/A/H01_2026-10-29`; manifest:
`docs/evidence/A/H01_2026-10-29/manifest.json`.
The manifest binds source revision, input and config hashes, and the success,
missing-RUL and invalid-input artifacts.
Missing-RUL view: `docs/evidence/A/H01_2026-10-29/health_missing_rul.json`.

Task 4 CLI commands (from repository root, with the Task 4 environment):

```powershell
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m backend.health.estimator --history docs/evidence/A/H01_2026-10-29/inputs/health_history_success.json --now-s 10
.\runs\a_n1_formal_env\venv\Scripts\python.exe -m backend.health.estimator --history docs/evidence/A/H01_2026-10-29/inputs/health_history_invalid.json --now-s 10
```

## B acceptance steps

Run one success command, inspect the missing-RUL view, run one rejection command,
validate the returned `HealthEstimate` against the frozen contract, and recompute
the evidence hashes against the manifest. B acceptance has not yet occurred.

Reject the handoff for future leakage, `raw_fraction` substitution, zero-filled
RUL, non-Wh energy, or a non-H00 return type.

## Explicit exclusions

This handoff makes no claims about A-N2, A-N3, guard, simulator, API, real
measurements, or performance. The synthetic evidence is not real telemetry,
online calibration, or a performance result.
