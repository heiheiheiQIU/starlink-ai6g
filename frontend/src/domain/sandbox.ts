import type { JsonValue, RunRequest } from '../types/contracts'

export type SandboxPolicyPair = 'edf/value' | 'edf/learned'
export type SandboxWeights = 'equal' | 'tiered' | 'urgent'
export type SandboxHealth = 'healthy' | 'degraded' | 'critical'
export type SandboxDisturbance = 'none' | 'mild' | 'strong'
export type SandboxRate = 'robust' | 'fast'

export interface SandboxAxes {
  task_count: 2 | 6 | 10
  deadline_s: 8 | 12 | 18 | 24
  weights: SandboxWeights
  initial_energy_Wh: 0.8 | 1.2 | 10
  health: SandboxHealth
  reserve_Wh: number
  disturbance: SandboxDisturbance
  rate: SandboxRate
}

export interface SandboxDemoRoute {
  id: 'S1' | 'S2' | 'S3'
  label: string
  purpose: string
  observation: string
  axes: SandboxAxes
  seed: 7
}

export const SANDBOX_DEMO_ROUTES: readonly SandboxDemoRoute[] = [
  {
    id: 'S1', label: '资源充足', purpose: '验证基础传输闭环',
    observation: '观察无扰动、能量充足时不同策略是否完成任务。', seed: 7,
    axes: { task_count: 2, deadline_s: 24, weights: 'equal', initial_energy_Wh: 10, health: 'healthy', reserve_Wh: 0.5, disturbance: 'none', rate: 'fast' },
  },
  {
    id: 'S2', label: '健康临界', purpose: '验证健康约束介入',
    observation: '观察低能量与临界健康状态下安全储能约束如何拒绝发送。', seed: 7,
    axes: { task_count: 6, deadline_s: 8, weights: 'tiered', initial_energy_Wh: 0.8, health: 'critical', reserve_Wh: 0.5, disturbance: 'none', rate: 'robust' },
  },
  {
    id: 'S3', label: '强链路扰动', purpose: '验证协议恢复链路',
    observation: '观察ACK丢失、超时、重传、重复块抑制与回退事件。', seed: 7,
    axes: { task_count: 2, deadline_s: 24, weights: 'tiered', initial_energy_Wh: 10, health: 'healthy', reserve_Wh: 0.5, disturbance: 'strong', rate: 'robust' },
  },
]

const AXIS_LABELS: Record<keyof SandboxAxes, string> = {
  task_count: '任务数量', deadline_s: '任务期限', weights: '业务权重',
  initial_energy_Wh: '初始可用能量', health: '健康状态', reserve_Wh: '安全储能下限',
  disturbance: '链路扰动', rate: '传输速率档',
}

export function diffSandboxAxes(before: SandboxAxes, after: SandboxAxes) {
  return (Object.keys(AXIS_LABELS) as (keyof SandboxAxes)[])
    .filter((key) => before[key] !== after[key])
    .map((key) => ({ key, label: AXIS_LABELS[key], before: String(before[key]), after: String(after[key]) }))
}

export interface SandboxMeasuredResult { policy_id: string; weighted_on_time_rate: number | null }

export function explainSandboxResults(results: readonly SandboxMeasuredResult[]) {
  const edf = results.find((item) => item.policy_id === 'edf')?.weighted_on_time_rate
  const learned = results.find((item) => item.policy_id === 'learned')?.weighted_on_time_rate
  if (edf === null || edf === undefined || learned === null || learned === undefined) {
    return { classification: 'insufficient' as const, title: '证据不足', detail: '策略对缺少可比较的加权按时交付率，不作增益判断。' }
  }
  const delta = learned - edf
  if (Math.abs(delta) < 1e-9) {
    return { classification: 'equivalent' as const, title: '本工况结果等效', detail: `Learned与EDF实测均为${(learned * 100).toFixed(1)}%。` }
  }
  if (delta > 0) {
    return { classification: 'higher' as const, title: '本工况Learned较高', detail: `实测差值${(delta * 100).toFixed(1)}个百分点；仅适用于本次合成工况。` }
  }
  return { classification: 'negative' as const, title: '本工况Learned较低', detail: `实测差值${(delta * 100).toFixed(1)}个百分点；负结果已原样保留。` }
}

export const DEFAULT_SANDBOX_AXES: SandboxAxes = {
  task_count: 2,
  deadline_s: 24,
  weights: 'equal',
  initial_energy_Wh: 10,
  health: 'healthy',
  reserve_Wh: 0.5,
  disturbance: 'none',
  rate: 'fast',
}

export function validateSandboxInput(axes: SandboxAxes, seed: number): string[] {
  const errors: string[] = []
  if (!Number.isSafeInteger(seed) || seed < 0) errors.push('随机种子必须为非负整数')
  if (!Number.isFinite(axes.reserve_Wh) || axes.reserve_Wh < 0 || axes.reserve_Wh > 20) {
    errors.push('安全储能下限必须在 0–20 Wh')
  }
  return errors
}

export function makeSandboxRunRequest(axes: SandboxAxes, pair: SandboxPolicyPair, seed: number): RunRequest {
  const errors = validateSandboxInput(axes, seed)
  if (errors.length > 0) throw new Error(errors.join('；'))
  return {
    schema_version: '1.0',
    config: {
      kind: 'sandbox_axes',
      compiler_version: 'sandbox-axis-v1',
      axes: { ...axes },
    } as Record<string, JsonValue>,
    policy_ids: pair.split('/'),
    seed,
  }
}
