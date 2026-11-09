import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SandboxControlPanel } from './SandboxControlPanel'
import type { RunController } from '../state/useRun'

function controller(create = vi.fn().mockResolvedValue(undefined)): RunController {
  return {
    state: { kind: 'idle' },
    create,
    resume: vi.fn(),
    refresh: vi.fn(),
    abort: vi.fn(),
    exportZip: vi.fn(),
  }
}

describe('SandboxControlPanel', () => {
  it('exposes all eight backend axes and submits the versioned axis-only request', async () => {
    const user = userEvent.setup()
    const create = vi.fn().mockResolvedValue(undefined)
    render(<SandboxControlPanel controller={controller(create)} />)

    expect(screen.getByLabelText('任务数量')).toBeInTheDocument()
    expect(screen.getByLabelText('任务期限')).toBeInTheDocument()
    expect(screen.getByLabelText('业务权重')).toBeInTheDocument()
    expect(screen.getByLabelText('初始可用能量')).toBeInTheDocument()
    expect(screen.getByLabelText('健康状态')).toBeInTheDocument()
    expect(screen.getByLabelText('安全储能下限')).toBeInTheDocument()
    expect(screen.getByLabelText('链路扰动')).toBeInTheDocument()
    expect(screen.getByLabelText('传输速率档')).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('健康状态'), 'critical')
    await user.click(screen.getByRole('button', { name: '运行沙盒对照' }))

    expect(create).toHaveBeenCalledWith(expect.objectContaining({
      config: expect.objectContaining({
        kind: 'sandbox_axes',
        compiler_version: 'sandbox-axis-v1',
        axes: expect.objectContaining({ health: 'critical' }),
      }),
    }))
    expect(create.mock.calls[0][0].config).not.toHaveProperty('scenario')
  })

  it('blocks an invalid reserve before POST and explains the boundary', async () => {
    const user = userEvent.setup()
    const create = vi.fn().mockResolvedValue(undefined)
    render(<SandboxControlPanel controller={controller(create)} />)

    const reserve = screen.getByLabelText('安全储能下限')
    await user.clear(reserve)
    await user.type(reserve, '20.1')

    expect(screen.getByText('安全储能下限必须在 0–20 Wh')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '运行沙盒对照' })).toBeDisabled()
    expect(create).not.toHaveBeenCalled()
  })

  it('labels a zero learned result as a measured negative result, not a success claim', () => {
    const online = controller()
    online.state = {
      kind: 'online',
      runId: 'run-sandbox-1',
      status: { run_id: 'run-sandbox-1', status: 'completed', progress: 1, active_policies: [], error: null },
      results: {
        schema_version: '1.0', run_id: 'run-sandbox-1', status: 'completed', config_hash: 'a', input_hash: 'b',
        model_hash: null, code_revision: 'c', seed: 1, metric_definitions: {}, artifact_paths: {},
        by_policy: [{
          policy_id: 'learned', model_hash: 'm', sample_count: 2, evaluation_end_s: 32, pending_task_count: 2,
          weighted_on_time_rate: 0, critical_task_success_rate: 0, goodput_bps: 0, minimum_soc_true: 0.4,
          energy_violation_count: 0, energy_violation_duration_s: 0, success_payload_bytes: 0,
          joule_per_success_bit: null, wait_p50_s: null, wait_p95_s: null, decision_p50_ms: 1,
          decision_p95_ms: 1, timeout_rate: 0, parameter_count: 1, memory_bytes: 1, metric_reasons: {},
        }],
      },
      events: [], offline: false, error: null,
    }
    render(<SandboxControlPanel controller={online} />)
    expect(screen.getByText('0.0%')).toBeInTheDocument()
    expect(screen.getByText(/实测结果，不代表增益/)).toBeInTheDocument()
  })
})
