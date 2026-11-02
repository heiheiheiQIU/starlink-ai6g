export interface PolicyMetricRow {
  metric: string
  unit: string
  edf: string
  learned: string
  diff: string
  diffKind: 'pos' | 'zero' | 'na'
  note: string
}

export interface PolicySeriesPoint {
  t: number
  edf: number
  learned: number
}

export const COMPARE_AXIS = [0, 120, 240, 360, 480, 600] as const

export const FIXTURE_SERIES: readonly PolicySeriesPoint[] = [
  { t: 0, edf: 0, learned: 0 },
  { t: 120, edf: 0, learned: 1 },
  { t: 240, edf: 1, learned: 1 },
  { t: 300, edf: 1, learned: 2 },
  { t: 480, edf: 1, learned: 2 },
  { t: 600, edf: 2, learned: 3 },
]

export const FIXTURE_METRICS: readonly PolicyMetricRow[] = [
  {
    metric: '加权按时交付率',
    unit: '0—1',
    edf: '58.3%',
    learned: '66.7%',
    diff: '+8.4 pp（占位）',
    diffKind: 'pos',
    note: '分母含到期失败任务；未到期单列。契约样例占位，非实测。',
  },
  {
    metric: '关键任务成功率',
    unit: '0—1',
    edf: '1/1',
    learned: '1/1',
    diff: '持平',
    diffKind: 'zero',
    note: '异常摘要类任务完整按时交付。契约样例占位。',
  },
  {
    metric: '能量违例次数',
    unit: '次',
    edf: '0',
    learned: '0',
    diff: '持平',
    diffKind: 'zero',
    note: '真实违例在裁剪前记录；预测约束通过不能替代此值。',
  },
  {
    metric: 'J / 成功 bit',
    unit: 'mJ/bit',
    edf: '0.031',
    learned: '0.032',
    diff: '±0.001',
    diffKind: 'zero',
    note: '无成功交付时为 null + NO_DELIVERY，禁止以 0 伪装。',
  },
]

export const COMPARE_SCENARIO_LABELS = {
  load: ['负载：低', '负载：接近容量', '负载：过载'],
  energy: ['能量余量：充足', '能量余量：紧张', '能量余量：极低'],
  link: ['链路扰动：无', '链路扰动：有'],
} as const
