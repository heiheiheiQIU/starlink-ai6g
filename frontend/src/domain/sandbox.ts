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
