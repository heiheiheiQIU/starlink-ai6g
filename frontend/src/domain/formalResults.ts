export const FORMAL_VERDICTS = ['胜', '负', '未检出稳定差异', '未完成'] as const
export type FormalVerdict = (typeof FORMAL_VERDICTS)[number]
export type FormalComparisonId = 'learned-edf' | 'learned-value'

export interface FormalCellResult {
  cell_id: string
  n: number
  missing: number
  mean_delta: number | null
  ci95: [number, number] | null
}

export interface FormalComparison {
  cells: FormalCellResult[]
  paired_count: number
  overall: {
    mean_delta: number | null
    ci95: [number, number] | null
    aggregation: string
  }
  statistical_verdict: FormalVerdict
  formal_verdict: FormalVerdict
}

export interface FormalAnalysis {
  schema_version: 'formal-analysis-summary-v1'
  expected_policy_runs: 540
  completed_policy_runs: number
  missing_policy_runs: number
  failed_policy_runs: number
  failed_attempts: number
  result_signoff: string
  data_scope: string
  domain: string
  multiplicity: string
  policy_ids: string[]
  comparisons: Record<FormalComparisonId, FormalComparison>
  provenance: {
    frozen_manifest_sha256: string
    run_index_sha256: string
    binding: Record<string, unknown>
  }
  inference: {
    requests: number
    fallback_count: number
    fallback_rate: number | null
    cold_load_ms: number[]
    decision_latency_count: number
    decision_latency_median_ms: number | null
    decision_latency_p95_ms: number | null
    scope: string
  }
}

export type FormalAnalysisParseResult =
  | { ok: true; value: FormalAnalysis }
  | { ok: false; error: string }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isNonNegativeInteger(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === 'number' && value >= 0
}

function nullableNumber(value: unknown): value is number | null {
  return value === null || isFiniteNumber(value)
}

function interval(value: unknown): value is [number, number] | null {
  return value === null || (
    Array.isArray(value)
    && value.length === 2
    && isFiniteNumber(value[0])
    && isFiniteNumber(value[1])
    && value[0] <= value[1]
  )
}

function verdict(value: unknown): value is FormalVerdict {
  return typeof value === 'string' && FORMAL_VERDICTS.includes(value as FormalVerdict)
}

function classify(mean: number | null, ci95: [number, number] | null): FormalVerdict {
  if (mean === null || ci95 === null) return '未完成'
  if (mean > 0 && ci95[0] > 0) return '胜'
  if (mean < 0 && ci95[1] < 0) return '负'
  return '未检出稳定差异'
}

function parseComparison(value: unknown, id: FormalComparisonId): FormalComparisonParseResult {
  if (!isRecord(value) || !Array.isArray(value.cells) || value.cells.length !== 18) {
    return { ok: false, error: `${id} 必须包含18个工况格` }
  }
  const cellIds = new Set<string>()
  const cells: FormalCellResult[] = []
  for (const rawCell of value.cells) {
    if (!isRecord(rawCell) || typeof rawCell.cell_id !== 'string' || rawCell.cell_id.length === 0
      || !isNonNegativeInteger(rawCell.n) || !isNonNegativeInteger(rawCell.missing)
      || rawCell.n + rawCell.missing !== 10 || !nullableNumber(rawCell.mean_delta)
      || !interval(rawCell.ci95) || cellIds.has(rawCell.cell_id)) {
      return { ok: false, error: `${id} 含无效、重复或非10轨迹工况格` }
    }
    if ((rawCell.n === 0) !== (rawCell.mean_delta === null)) {
      return { ok: false, error: `${id}/${rawCell.cell_id} 的样本数与均值状态冲突` }
    }
    if ((rawCell.n === 10) !== (rawCell.ci95 !== null)) {
      return { ok: false, error: `${id}/${rawCell.cell_id} 的完整配对数与置信区间状态冲突` }
    }
    cellIds.add(rawCell.cell_id)
    cells.push(rawCell as unknown as FormalCellResult)
  }
  if (!isNonNegativeInteger(value.paired_count)
    || value.paired_count !== cells.reduce((sum, cell) => sum + cell.n, 0)
    || !isRecord(value.overall) || !nullableNumber(value.overall.mean_delta)
    || !interval(value.overall.ci95) || typeof value.overall.aggregation !== 'string'
    || !verdict(value.statistical_verdict) || !verdict(value.formal_verdict)) {
    return { ok: false, error: `${id} 的配对计数、总体统计量或结论无效` }
  }
  if (value.statistical_verdict !== classify(value.overall.mean_delta as number | null, value.overall.ci95 as [number, number] | null)) {
    return { ok: false, error: `${id} 的统计结论与总体统计量不一致` }
  }
  return { ok: true, value: value as unknown as FormalComparison }
}

type FormalComparisonParseResult =
  | { ok: true; value: FormalComparison }
  | { ok: false; error: string }

export function parseFormalAnalysis(value: unknown): FormalAnalysisParseResult {
  if (!isRecord(value) || value.schema_version !== 'formal-analysis-summary-v1') {
    return { ok: false, error: '不支持的正式分析版本' }
  }
  if (value.expected_policy_runs !== 540
    || !isNonNegativeInteger(value.completed_policy_runs)
    || !isNonNegativeInteger(value.missing_policy_runs)
    || !isNonNegativeInteger(value.failed_policy_runs)
    || !isNonNegativeInteger(value.failed_attempts)
    || value.completed_policy_runs + value.missing_policy_runs + value.failed_policy_runs !== 540) {
    return { ok: false, error: '正式运行计数不一致' }
  }
  if (!['pending', 'accepted'].includes(value.result_signoff as string) || typeof value.data_scope !== 'string'
    || typeof value.domain !== 'string' || typeof value.multiplicity !== 'string'
    || !Array.isArray(value.policy_ids) || value.policy_ids.some((item) => typeof item !== 'string')
    || !isRecord(value.comparisons)) {
    return { ok: false, error: '正式分析元数据不完整' }
  }
  const learnedEdf = parseComparison(value.comparisons['learned-edf'], 'learned-edf')
  if (!learnedEdf.ok) return learnedEdf
  const learnedValue = parseComparison(value.comparisons['learned-value'], 'learned-value')
  if (!learnedValue.ok) return learnedValue
  if (value.result_signoff !== 'accepted'
    && (learnedEdf.value.formal_verdict !== '未完成' || learnedValue.value.formal_verdict !== '未完成')) {
    return { ok: false, error: '结果发布完成前正式结论必须保持未完成' }
  }
  if (value.result_signoff === 'accepted'
    && (learnedEdf.value.formal_verdict !== learnedEdf.value.statistical_verdict
      || learnedValue.value.formal_verdict !== learnedValue.value.statistical_verdict)) {
    return { ok: false, error: '已发布正式结论必须与版本锁定的统计结论一致' }
  }
  if (!isRecord(value.provenance) || typeof value.provenance.frozen_manifest_sha256 !== 'string'
    || typeof value.provenance.run_index_sha256 !== 'string' || !isRecord(value.provenance.binding)
    || !/^[a-f0-9]{64}$/i.test(value.provenance.frozen_manifest_sha256)
    || !/^[a-f0-9]{64}$/i.test(value.provenance.run_index_sha256)) {
    return { ok: false, error: '正式分析来源哈希无效' }
  }
  if (!isRecord(value.inference) || !isNonNegativeInteger(value.inference.requests)
    || !isNonNegativeInteger(value.inference.fallback_count)
    || value.inference.fallback_count > value.inference.requests
    || !nullableNumber(value.inference.fallback_rate) || !Array.isArray(value.inference.cold_load_ms)
    || value.inference.cold_load_ms.some((item) => !isFiniteNumber(item) || item < 0)
    || !isNonNegativeInteger(value.inference.decision_latency_count)
    || !nullableNumber(value.inference.decision_latency_median_ms)
    || !nullableNumber(value.inference.decision_latency_p95_ms)
    || typeof value.inference.scope !== 'string') {
    return { ok: false, error: '推理证据字段无效' }
  }
  return {
    ok: true,
    value: {
      ...(value as unknown as FormalAnalysis),
      comparisons: { 'learned-edf': learnedEdf.value, 'learned-value': learnedValue.value },
    },
  }
}

export function shortHash(hash: string): string {
  return `${hash.slice(0, 12)}…${hash.slice(-4)}`
}
