/**
 * 契约样例 fixtures（H00 冻结结构）。所有哈希为占位值 fixture-not-real-hash，
 * 任何正式数字必须来自真实 run 的 results.json。
 */

import type {
  Observation,
  PolicyResult,
  RunResult,
  TeacherResult,
  Window,
} from '../types/contracts'

export const FIXTURE_HASH = 'fixture-not-real-hash'

function policy(
  policyId: string,
  modelHash: string | null,
  overrides: Partial<PolicyResult> = {},
): PolicyResult {
  return {
    policy_id: policyId,
    model_hash: modelHash,
    sample_count: 3,
    evaluation_end_s: 600,
    pending_task_count: 0,
    weighted_on_time_rate: 0.667,
    critical_task_success_rate: 1,
    goodput_bps: 409.6,
    minimum_soc_true: 0.41,
    energy_violation_count: 0,
    energy_violation_duration_s: 0,
    success_payload_bytes: 1024,
    joule_per_success_bit: 0.032,
    wait_p50_s: 12,
    wait_p95_s: 120,
    decision_p50_ms: 14,
    decision_p95_ms: 38,
    timeout_rate: 0,
    parameter_count: 8040,
    memory_bytes: 32768,
    metric_reasons: {},
    ...overrides,
  }
}

/** 正常对照样例：edf 规则（model_hash=null）＋learned（model_hash 占位）。 */
export const FIXTURE_RUN_RESULT: RunResult = {
  schema_version: '1.0',
  run_id: 'demo_fixture_001',
  status: 'completed',
  config_hash: FIXTURE_HASH,
  input_hash: FIXTURE_HASH,
  model_hash: null,
  code_revision: 'fixture-revision',
  seed: 42,
  by_policy: [policy('edf', null, { weighted_on_time_rate: 0.583 }), policy('learned', FIXTURE_HASH)],
  metric_definitions: {
    weighted_on_time_rate: 'Σ wᵢ·I(任务i完整且接收≤deadline) / Σ wᵢ',
  },
  artifact_paths: { results: 'results.json' },
}

/** 零交付样例：J/bit=null + NO_DELIVERY；sample_count=0 时不得产出比率。 */
export const FIXTURE_NO_DELIVERY_POLICY: PolicyResult = policy('edf', null, {
  sample_count: 0,
  weighted_on_time_rate: null,
  critical_task_success_rate: null,
  success_payload_bytes: 0,
  joule_per_success_bit: null,
  metric_reasons: { joule_per_success_bit: 'NO_DELIVERY', weighted_on_time_rate: 'EMPTY_DENOMINATOR' },
})

/** 合同错误态样例：非 null 指标同时携带缺测原因（后端不应产生，前端只展示错误态）。 */
export const FIXTURE_CONFLICT_POLICY: PolicyResult = policy('learned', FIXTURE_HASH, {
  metric_reasons: { goodput_bps: 'NO_DATA' },
})

const FIXTURE_WINDOW = (windowId: string, version: string): Window => ({
  window_id: windowId,
  start_s: 0,
  end_s: 120,
  rate_profile: [{ time_s: 0, robust_bps: 8000, fast_bps: 16000 }],
  loss_profile: [{ time_s: 0, robust_loss_prob: 0.01, fast_loss_prob: 0.05 }],
  source: 'geometry',
  forecast_version: version,
})

export function fixtureObservation(windows: Window[], forecastVersion: string): Observation {
  return {
    schema_version: '1.0',
    run_id: 'demo_fixture_001',
    policy_id: 'learned',
    sim_time_s: 60,
    tasks: [
      {
        task_id: 'T-101',
        arrival_s: 0,
        deadline_s: 480,
        payload_bytes: 12288,
        remaining_bytes: 9216,
        priority_weight: 3,
        business_class: '异常摘要',
        data_location: 'satellite_1',
      },
    ],
    forecast_windows: windows,
    health: {
      soc_est: 0.5,
      soc_lower: 0.45,
      capacity_Wh_est: 20,
      capacity_lower_Wh: 18,
      energy_lower_Wh: 8.1,
      rul_est: null,
      rul_unit: null,
      uncertainty_method: 'synthetic_absolute_margin',
      model_version: 'synthetic-health-v1',
      observed_at_s: 10,
      available_at_s: 12,
      reason_codes: ['SYNTHETIC_HEALTH_OBSERVATION'],
    },
    inflight: null,
    cache_bytes: 4096,
    forecast_version: forecastVersion,
  }
}

export const FIXTURE_OBSERVATION_CONSISTENT: Observation = fixtureObservation(
  [FIXTURE_WINDOW('W-1', 'v1'), FIXTURE_WINDOW('W-2', 'v1')],
  'v1',
)

export const FIXTURE_OBSERVATION_MIXED: Observation = fixtureObservation(
  [FIXTURE_WINDOW('W-1', 'v1'), FIXTURE_WINDOW('W-2', 'v2')],
  'v1',
)

export function fixtureTeacherResult(
  scores: TeacherResult['candidate_scores'],
): TeacherResult {
  return { candidate_scores: scores, solver_status: 'optimal', gap: 0, elapsed_ms: 42 }
}
