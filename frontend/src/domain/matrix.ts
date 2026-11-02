/**
 * B R5 规则矩阵（180轨迹×2规则=360真实运行）的解析与聚合。
 * 数据源：docs/evidence/B/R5_2026-10-29/per_run.csv（提交 50f441a，哈希 b1203575…）。
 * 本数据是规则基线验证记录，不是 AI 实验结果——展示时须保持这一标注。
 */

import perRunCsv from '../fixtures/r5_per_run.csv?raw'

export const MATRIX_SOURCE_NOTE =
  '数据来源：B R5 提交的真实规则运行记录（docs/evidence/B/R5_2026-10-29/per_run.csv，360 行）。属规则基线验证，非 AI 实验结果；正式 18×10 实验另行运行。'

export interface CellDef {
  cellIndex: number
  loadLevel: 'low' | 'near_capacity' | 'overload'
  energyMargin: 'low' | 'medium' | 'ample'
  disturbance: 'mild' | 'strong'
}

export const LOAD_LABELS = { low: '低载', near_capacity: '中载', overload: '过载' } as const
export const ENERGY_LABELS = { low: '能量低', medium: '能量中', ample: '能量充足' } as const
export const DISTURBANCE_LABELS = { mild: '扰动轻微', strong: '扰动强烈' } as const
export const POLICY_LABELS = { edf: 'EDF 规则', value: 'value 规则' } as const

export interface MatrixCell {
  def: CellDef
  byPolicy: Record<'edf' | 'value', { wotMean: number; runs: number }>
}

export interface MatrixSummary {
  cells: MatrixCell[]
  runCount: number
  policyMeans: Record<'edf' | 'value', number>
}

function parseCsv(raw: string): Record<string, string>[] {
  const lines = raw.split(/\r?\n/).filter((line) => line.trim().length > 0)
  const headers = lines[0].split(',')
  return lines.slice(1).map((line) => {
    const values = line.split(',')
    const row: Record<string, string> = {}
    headers.forEach((header, index) => {
      row[header] = values[index] ?? ''
    })
    return row
  })
}

function cellDef(index: number): CellDef {
  const loadLevel = (['low', 'near_capacity', 'overload'] as const)[Math.floor(index / 6)]
  const energyMargin = (['low', 'medium', 'ample'] as const)[Math.floor((index % 6) / 2)]
  const disturbance = index % 2 === 0 ? 'mild' : 'strong'
  return { cellIndex: index, loadLevel, energyMargin, disturbance }
}

export function loadMatrixSummary(): MatrixSummary {
  const rows = parseCsv(perRunCsv)
  const cells: MatrixCell[] = Array.from({ length: 18 }, (_, index) => ({
    def: cellDef(index),
    byPolicy: { edf: { wotMean: 0, runs: 0 }, value: { wotMean: 0, runs: 0 } },
  }))

  const sums: Record<'edf' | 'value', { total: number; count: number }> = {
    edf: { total: 0, count: 0 },
    value: { total: 0, count: 0 },
  }

  for (const row of rows) {
    const index = Number(row.cell_id?.split('_')[1])
    const policy = row.policy_id === 'edf' || row.policy_id === 'value' ? row.policy_id : null
    if (policy === null || !Number.isInteger(index) || index < 0 || index > 17) continue
    const wot = Number(row.weighted_on_time_rate)
    if (!Number.isFinite(wot)) continue
    cells[index].byPolicy[policy].wotMean += wot
    cells[index].byPolicy[policy].runs += 1
    sums[policy].total += wot
    sums[policy].count += 1
  }

  for (const cell of cells) {
    for (const policy of ['edf', 'value'] as const) {
      const bucket = cell.byPolicy[policy]
      bucket.wotMean = bucket.runs > 0 ? bucket.wotMean / bucket.runs : 0
    }
  }

  return {
    cells,
    runCount: rows.length,
    policyMeans: {
      edf: sums.edf.count > 0 ? sums.edf.total / sums.edf.count : 0,
      value: sums.value.count > 0 ? sums.value.total / sums.value.count : 0,
    },
  }
}

/** 0..1 → 红→琥珀→绿 三段插值，用于热力着色。 */
export function heatColor(value: number): string {
  const t = Math.max(0, Math.min(1, value))
  const stops = [
    { at: 0, r: 156, g: 59, b: 59 },
    { at: 0.5, r: 184, g: 134, b: 11 },
    { at: 1, r: 47, g: 158, b: 107 },
  ]
  const upper = stops.find((stop) => stop.at >= t) ?? stops[stops.length - 1]
  const lower = [...stops].reverse().find((stop) => stop.at <= t) ?? stops[0]
  if (upper === lower) {
    return `rgb(${upper.r}, ${upper.g}, ${upper.b})`
  }
  const ratio = (t - lower.at) / (upper.at - lower.at)
  const channel = (a: number, b: number) => Math.round(a + (b - a) * ratio)
  return `rgb(${channel(lower.r, upper.r)}, ${channel(lower.g, upper.g)}, ${channel(lower.b, upper.b)})`
}
