# A1 to B health input contract

## Current A1 output

`predict_npz_windows` returns an internal `LegacyPrediction` from delivered, already standardized NPZ windows. It includes raw normalized checkpoint predictions, run IDs, legacy window start indices, final observed `available_indices`, native `step_unit`, model ID, and checkpoint SHA256. Source steps are `cycle`; target steps are `orbit`. Neither is elapsed seconds, and no cross-unit conversion is defined.

The caller must provide `now_index` in the NPZ native step unit. A window is eligible only when `start_index + window_size - 1 <= now_index`. The start and available indices must both be retained for audit. A1 checks exact feature order, finite window values, unique sample indices, and strict CPU checkpoint loading. Only the delivered standardized NPZ windows are supported until a persisted scaler and a new raw-telemetry preprocessing chain are established.

## RUL and system state boundary

The checkpoint's raw normalized prediction is not a validated online native RUL estimate. Restoring native RUL with a future run maximum would leak future information. Therefore `rul_est` remains `null` with reason code `NATIVE_RUL_RESTORE_REQUIRES_FUTURE_RUN_MAX` until an online-safe restoration method is demonstrated. Preserve the native RUL unit (`cycles` or `orbits`) as metadata; do not turn a missing value into zero.

RUL must never be substituted for SOC, capacity, energy, or a battery control state. B may use explicitly labeled synthetic health in its own simulations. A1 evidence JSON files are examples of checkpoint behavior, not B's formal `HealthEstimate` schema. H00 now owns and has frozen the formal type and its API semantics; legacy A1 checkpoint evidence remains non-formal.

## Failure behavior

Missing assets, manifest mismatch, invalid features or windows, future windows, invalid checkpoint state, and non-finite outputs are explicit failures. In particular, `WINDOW_NOT_AVAILABLE` is a rejected input, not a successful inference with a degraded score. Model errors must not silently fall back to synthetic health.

## Formal synthetic HealthEstimate adapter

`backend.health.estimator.estimate_health(history, now_s)` returns the frozen
`backend.contracts.HealthEstimate`. It accepts only explicit synthetic SOC/capacity
observations in seconds, loads `configs/health_observation.json` relative to the
module, and preserves unavailable RUL as `null` plus `RUL_UNAVAILABLE`.

The adapter does not consume the legacy checkpoint `raw_fraction`. The legacy A1
evidence remains checkpoint-behavior evidence and is not a formal HealthEstimate.
