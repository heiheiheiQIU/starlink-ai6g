import { describe, expect, it } from 'vitest'

import {
  DEFAULT_SANDBOX_AXES,
  SANDBOX_DEMO_ROUTES,
  diffSandboxAxes,
  explainSandboxResults,
  makeSandboxRunRequest,
  validateSandboxInput,
} from './sandbox'

describe('sandbox request builder', () => {
  it('submits only the versioned axis contract and never compiles a scenario in the browser', () => {
    const request = makeSandboxRunRequest(DEFAULT_SANDBOX_AXES, 'edf/learned', 600001)

    expect(request).toEqual({
      schema_version: '1.0',
      config: {
        kind: 'sandbox_axes',
        compiler_version: 'sandbox-axis-v1',
        axes: DEFAULT_SANDBOX_AXES,
      },
      policy_ids: ['edf', 'learned'],
      seed: 600001,
    })
    expect(request.config).not.toHaveProperty('scenario')
    expect(request.config).not.toHaveProperty('tasks')
  })

  it('rejects non-integer seeds and reserve values outside the backend boundary', () => {
    expect(validateSandboxInput(DEFAULT_SANDBOX_AXES, -1)).toContain('随机种子必须为非负整数')
    expect(validateSandboxInput(DEFAULT_SANDBOX_AXES, 1.5)).toContain('随机种子必须为非负整数')
    expect(validateSandboxInput({ ...DEFAULT_SANDBOX_AXES, reserve_Wh: 20.1 }, 1)).toContain('安全储能下限必须在 0–20 Wh')
  })

  it('pins the three demo routes to the backend golden requests', () => {
    expect(SANDBOX_DEMO_ROUTES.map(({ id, axes, seed }) => ({ id, axes, seed }))).toEqual([
      { id: 'S1', seed: 7, axes: { task_count: 2, deadline_s: 24, weights: 'equal', initial_energy_Wh: 10, health: 'healthy', reserve_Wh: 0.5, disturbance: 'none', rate: 'fast' } },
      { id: 'S2', seed: 7, axes: { task_count: 6, deadline_s: 8, weights: 'tiered', initial_energy_Wh: 0.8, health: 'critical', reserve_Wh: 0.5, disturbance: 'none', rate: 'robust' } },
      { id: 'S3', seed: 7, axes: { task_count: 2, deadline_s: 24, weights: 'tiered', initial_energy_Wh: 10, health: 'healthy', reserve_Wh: 0.5, disturbance: 'strong', rate: 'robust' } },
    ])
  })

  it('reports only changed engineering axes between the executed and edited config', () => {
    expect(diffSandboxAxes(DEFAULT_SANDBOX_AXES, { ...DEFAULT_SANDBOX_AXES, health: 'critical', reserve_Wh: 1.2 })).toEqual([
      { key: 'health', label: '健康状态', before: 'healthy', after: 'critical' },
      { key: 'reserve_Wh', label: '安全储能下限', before: '0.5', after: '1.2' },
    ])
  })

  it.each([
    [[{ policy_id: 'edf', weighted_on_time_rate: 1 }, { policy_id: 'learned', weighted_on_time_rate: 0 }], 'negative'],
    [[{ policy_id: 'edf', weighted_on_time_rate: 1 }, { policy_id: 'learned', weighted_on_time_rate: 1 }], 'equivalent'],
    [[{ policy_id: 'edf', weighted_on_time_rate: 0 }, { policy_id: 'learned', weighted_on_time_rate: 1 }], 'higher'],
    [[{ policy_id: 'edf', weighted_on_time_rate: null }], 'insufficient'],
  ] as const)('classifies measured results without inventing an AI gain: %s', (results, expected) => {
    expect(explainSandboxResults([...results]).classification).toBe(expected)
  })
})
