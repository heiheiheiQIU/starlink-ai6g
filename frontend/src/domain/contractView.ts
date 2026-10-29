/**
 * 合同 → 展示层的防御性语义（不替代后端校验）。
 *
 * 规则来源：docs/contracts/README.md「结果指标字段」与「Schema与Python校验的边界」。
 * 前端只做展示判定：null+reason=缺测；0=实测零；非null却携带原因=合同错误态；
 * 预测批次冲突=合同错误态。遇到合同错误态只显示与上报，不自行选一个值。
 */

import type {
  NullableMetricName,
  Observation,
  PolicyResult,
  TeacherCandidateScore,
  TeacherResult,
} from '../types/contracts'

export type MetricDisplay =
  | { kind: 'measured'; value: number }
  | { kind: 'missing'; reason: string }
  | { kind: 'conflict'; value: number | null; reason: string }

export function metricDisplay(policy: PolicyResult, name: NullableMetricName): MetricDisplay {
  const value = policy[name]
  const reason = policy.metric_reasons[name]

  if (value === null) {
    if (reason === undefined) {
      return { kind: 'conflict', value: null, reason: '缺失指标未提供原因（合同错误态）' }
    }
    return { kind: 'missing', reason }
  }
  if (reason !== undefined) {
    return { kind: 'conflict', value, reason: '已测数值同时携带缺测原因（合同错误态）' }
  }
  return { kind: 'measured', value }
}

/** 实测 0 必须显示为 0；N/A 只能由 missing 分支产生（value=null）。 */
export function formatMetricValue(display: MetricDisplay): string {
  switch (display.kind) {
    case 'measured':
      return String(display.value)
    case 'missing':
      return `N/A（${display.reason}）`
    case 'conflict':
      return display.value === null ? `合同错误（${display.reason}）` : `${display.value} ⚠合同错误（${display.reason}）`
  }
}

/**
 * H00：每个 Window.forecast_version 必须等于 Observation.forecast_version；
 * 空窗口保留顶层批次标识。前端收到混批数据时显示合同错误态，不自行选版本。
 */
export function forecastBatchConflict(obs: Observation): string | null {
  const mismatch = obs.forecast_windows.find(
    (window) => window.forecast_version !== obs.forecast_version,
  )
  return mismatch
    ? `窗口 ${mismatch.window_id} 预测版本 ${mismatch.forecast_version} 与顶层 ${obs.forecast_version} 不一致（合同错误态）`
    : null
}

/**
 * TeacherResult 候选集合的展示性检查（防御提示，非权威校验）：
 * 非空、键唯一、恰一个 idle 且 feasible=true。
 */
export function teacherCandidateSetIssues(result: TeacherResult): string[] {
  const issues: string[] = []
  const scores: TeacherCandidateScore[] = result.candidate_scores

  if (scores.length === 0) {
    return ['候选集合为空']
  }
  const keys = scores.map((score) => `${score.task_id ?? 'idle'}:${score.mode}`)
  if (new Set(keys).size !== keys.length) {
    issues.push('候选键重复')
  }
  const idle = scores.filter((score) => score.mode === 'idle')
  if (idle.length === 0) {
    issues.push('缺少 idle 候选')
  } else if (idle.length > 1) {
    issues.push('存在多个 idle 候选')
  } else if (!idle[0].feasible) {
    issues.push('唯一 idle 候选不可行')
  }
  return issues
}
