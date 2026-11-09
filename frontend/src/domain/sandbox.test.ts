import { describe, expect, it } from 'vitest'

import { DEFAULT_SANDBOX_AXES, makeSandboxRunRequest, validateSandboxInput } from './sandbox'

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
})
