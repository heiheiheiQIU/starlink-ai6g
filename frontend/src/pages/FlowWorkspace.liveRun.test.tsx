import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { RunProvider } from '../state/RunContext'
import type { RunController } from '../state/useRun'
import { FlowWorkspace } from './FlowWorkspace'

describe('live flow workspace', () => {
  it('shows the shared backend run and advances from its events', () => {
    const controller: RunController = {
      state: {
        kind: 'online',
        runId: 'run_shared_live_42',
        status: { run_id: 'run_shared_live_42', status: 'running', progress: 0.7, active_policies: ['edf', 'learned'], error: null },
        results: null,
        events: [{
          event_id: 8,
          run_id: 'run_shared_live_42',
          policy_id: 'learned',
          sim_time_s: 240,
          event_type: 'sent',
          task_id: 'T-101',
          block_id: 1,
          payload_bytes: 1024,
          overhead_bytes: 32,
          energy_Wh: 0.01,
          reason_code: null,
          data: null,
        }],
        offline: false,
        error: null,
      },
      create: vi.fn(), resume: vi.fn(), refresh: vi.fn(), abort: vi.fn(), exportZip: vi.fn(),
    }

    render(<RunProvider controller={controller}><FlowWorkspace /></RunProvider>)

    const status = screen.getByRole('region', { name: '工程运行状态' })
    expect(status).toHaveTextContent('在线任务执行')
    expect(status).toHaveTextContent('任务服务在线')
    expect(status).toHaveTextContent('run_shared_live_42')
    expect(status).toHaveTextContent('05 / 06')
    expect(screen.getByRole('heading', { name: '发送/确认', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('发送 1')).toBeInTheDocument()
    expect(screen.getByText('T-101 · block 1 · 1024 B')).toBeInTheDocument()
    expect(screen.queryByText('链路已暂停 · 等待操作')).not.toBeInTheDocument()
    const summary = screen.getByLabelText('当前步骤在线摘要')
    expect(summary).toHaveTextContent('发送1')
    expect(summary).toHaveTextContent('确认0')
    expect(summary).toHaveTextContent('丢失0')
  })
})
