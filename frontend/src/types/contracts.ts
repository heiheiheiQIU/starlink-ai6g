/**
 * H00 冻结合同的 TypeScript 镜像（origin/main@75f1c52，contracts.py 已三方 accepted）。
 *
 * 边界纪律：本文件只做结构镜像与防御性展示语义；跨字段/集合/时间语义的权威校验在
 * Python 后端（docs/contracts/README.md「Schema与Python校验的边界」）。前端收到
 * 违反合同的数据时显示"合同错误态"，不得自行选版本、二选一或推算合法值。
 */

export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue }

export type Mode = 'idle' | 'robust' | 'fast'
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ErrorCode =
  | 'INVALID_CONFIG'
  | 'RUN_NOT_FOUND'
  | 'RUN_NOT_COMPLETE'
  | 'CAPACITY_BUSY'
  | 'INTERNAL_RUN_ERROR'
export type TransportEventType =
  | 'arrived'
  | 'sent'
  | 'received'
  | 'acked'
  | 'dropped'
  | 'fallback'
export type EventType = TransportEventType | 'decision' | 'snapshot' | 'window_changed'

export interface Task {
  task_id: string
  arrival_s: number
  deadline_s: number
  payload_bytes: number
  remaining_bytes: number
  priority_weight: number
  business_class: string
  data_location: 'satellite_1'
}

export interface RatePoint {
  time_s: number
  robust_bps: number
  fast_bps: number
}

export interface LossPoint {
  time_s: number
  robust_loss_prob: number
  fast_loss_prob: number
}

export interface Window {
  window_id: string
  start_s: number
  end_s: number
  rate_profile: RatePoint[]
  loss_profile: LossPoint[]
  source: string
  forecast_version: string
}

export interface HealthEstimate {
  soc_est: number
  soc_lower: number
  capacity_Wh_est: number
  capacity_lower_Wh: number
  energy_lower_Wh: number
  rul_est: number | null
  rul_unit: string | null
  uncertainty_method: string
  model_version: string
  observed_at_s: number
  available_at_s: number
  reason_codes: string[]
}

export interface InFlight {
  task_id: string
  block_id: number
  payload_bytes: number
  mode: 'robust' | 'fast'
  sent_at_s: number
  timeout_at_s: number
  retries: number
}

export interface Observation {
  schema_version: '1.0'
  run_id: string
  policy_id: string
  sim_time_s: number
  tasks: Task[]
  forecast_windows: Window[]
  health: HealthEstimate
  inflight: InFlight | null
  cache_bytes: number
  forecast_version: string
}

export interface CandidateScore {
  task_id: string | null
  mode: Mode
  score: number
}

export interface Action {
  task_id: string | null
  mode: Mode
  scheduled_bytes: number
  reason_codes: string[]
  fallback: boolean
}

export interface ConstraintCheck {
  code: string
  passed: boolean
  details: Record<string, JsonValue>
}

export interface DecisionData {
  /** 线上事件字段名；不得同时使用内部 Decision 的 decision_latency_ms。 */
  action: Action
  candidate_scores: CandidateScore[]
  constraint_checks: ConstraintCheck[]
  latency_ms: number
  fallback: boolean
  model_version: string | null
  policy_version: string
}

export interface Decision {
  action: Action
  candidate_scores: CandidateScore[]
  constraint_checks: ConstraintCheck[]
  decision_latency_ms: number
  fallback: boolean
  model_version: string | null
  policy_version: string
}

export interface EnergyBandPoint {
  time_s: number
  energy_lower_Wh: number
  energy_upper_Wh: number
}

export interface EvaluationTruth {
  label: 'posthoc_simulation'
  soc_true: number
  energy_true_Wh: number
  capacity_true_Wh: number
}

export interface SnapshotData {
  soc_est: number
  energy_est_Wh: number
  energy_lower_Wh: number
  queue_count: number
  forecast_energy_band: EnergyBandPoint[] | null
  policy_version: string
  evaluation_truth: EvaluationTruth | null
  reason_codes: string[]
}

export interface WindowChangedData {
  window_id: string
  is_visible: boolean
}

export type EventData = DecisionData | SnapshotData | WindowChangedData | null

export interface Event {
  event_id: number
  run_id: string
  policy_id: string
  sim_time_s: number
  event_type: EventType
  task_id: string | null
  block_id: number | null
  payload_bytes: number
  overhead_bytes: number
  energy_Wh: number
  reason_code: string | null
  data: EventData
}

export interface EventsQuery {
  after: number
  limit: number
}

export interface EventsPage {
  run_id: string
  events: Event[]
  next_after: number
  has_more: boolean
}

export interface ErrorBody {
  code: ErrorCode
  message: string
  details: Record<string, JsonValue>
}

export interface RunRequest {
  schema_version: '1.0'
  config: Record<string, JsonValue>
  policy_ids: string[]
  seed: number
}

export interface RunCreated {
  run_id: string
  status: 'queued'
  schema_version: '1.0'
}

export interface RunStatusResponse {
  run_id: string
  status: RunStatus
  progress: number | null
  active_policies: string[]
  error: ErrorBody | null
}

export type NullableMetricName =
  | 'weighted_on_time_rate'
  | 'critical_task_success_rate'
  | 'goodput_bps'
  | 'minimum_soc_true'
  | 'energy_violation_count'
  | 'energy_violation_duration_s'
  | 'joule_per_success_bit'
  | 'wait_p50_s'
  | 'wait_p95_s'
  | 'decision_p50_ms'
  | 'decision_p95_ms'
  | 'timeout_rate'
  | 'parameter_count'
  | 'memory_bytes'

export interface PolicyResult {
  policy_id: string
  model_hash: string | null
  sample_count: number
  evaluation_end_s: number
  pending_task_count: number
  weighted_on_time_rate: number | null
  critical_task_success_rate: number | null
  goodput_bps: number | null
  minimum_soc_true: number | null
  energy_violation_count: number | null
  energy_violation_duration_s: number | null
  success_payload_bytes: number
  joule_per_success_bit: number | null
  wait_p50_s: number | null
  wait_p95_s: number | null
  decision_p50_ms: number | null
  decision_p95_ms: number | null
  timeout_rate: number | null
  parameter_count: number | null
  memory_bytes: number | null
  metric_reasons: Record<string, string>
}

export interface RunResult {
  schema_version: '1.0'
  run_id: string
  status: 'completed'
  config_hash: string
  input_hash: string
  model_hash: string | null
  code_revision: string
  seed: number
  by_policy: PolicyResult[]
  metric_definitions: Record<string, string>
  artifact_paths: Record<string, string>
}

export interface TeacherCandidateScore extends CandidateScore {
  feasible: boolean
}

export interface TeacherResult {
  candidate_scores: TeacherCandidateScore[]
  solver_status: string
  gap: number | null
  elapsed_ms: number
}
