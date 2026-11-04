import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { RealRunPanel } from './RealRunPanel'
import { ApiError } from '../api/runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type { RunController } from '../state/useRun'

function fakeController(overrides: Partial<RunController> = {}): RunController {
  return {
    state: { kind: 'idle' },
    create: vi.fn(),
    resume: vi.fn(),
    refresh: vi.fn(),
    abort: vi.fn(),
    exportZip: vi.fn(),
    ...overrides,
  }
}

describe('RealRunPanel', () => {
  it('submits the selected preset with empty actions', async () => {
    const user = userEvent.setup()
    const create = vi.fn()
    render(<RealRunPanel controller={fakeController({ create })} />)

    await user.click(screen.getByRole('button', { name: '发起真实运行' }))

    expect(create).toHaveBeenCalledTimes(1)
    const request = create.mock.calls[0][0] as { config: { actions: unknown[]; scenario: { scenario_id: string } }; policy_ids: string[]; seed: number }
    expect(request.policy_ids).toEqual(['edf', 'value'])
    expect(request.seed).toBe(10000)
    expect(request.config.actions).toEqual([])
    expect(request.config.scenario.scenario_id).toBeTruthy()
  })

  it('submits edf/learned pair when selected', async () => {
    const user = userEvent.setup()
    const create = vi.fn()
    render(<RealRunPanel controller={fakeController({ create })} />)

    await user.selectOptions(screen.getByLabelText(/策略对/), 'edf/learned')
    await user.click(screen.getByRole('button', { name: '发起真实运行' }))

    const request = create.mock.calls[0][0] as { policy_ids: string[] }
    expect(request.policy_ids).toEqual(['edf', 'learned'])
  })

  it('renders real metrics and ZIP download for a completed run', async () => {
    const user = userEvent.setup()
    const exportZip = vi.fn()
    render(
      <RealRunPanel
        controller={fakeController({
          exportZip,
          state: {
            kind: 'online',
            runId: 'run-real',
            status: { run_id: 'run-real', status: 'completed', progress: 1, active_policies: ['edf', 'learned'], error: null },
            results: FIXTURE_RUN_RESULT,
            events: [],
            offline: false,
            error: null,
          },
        })}
      />,
    )

    expect(screen.getByLabelText('真实运行指标')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /下载 ZIP 证据包/ }))
    expect(exportZip).toHaveBeenCalled()
  })

  it('shows backend errors and keeps the last state', () => {
    render(
      <RealRunPanel
        controller={fakeController({
          state: {
            kind: 'online',
            runId: 'run-real',
            status: { run_id: 'run-real', status: 'running', progress: 0.2, active_policies: ['edf'], error: null },
            results: null,
            events: null,
            offline: false,
            error: 'INVALID_CONFIG：bad config',
          },
        })}
      />,
    )

    expect(screen.getByText('INVALID_CONFIG：bad config')).toBeInTheDocument()
  })
})
