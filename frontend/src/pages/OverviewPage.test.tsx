import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { OverviewPage } from './OverviewPage'
import { RunProvider } from '../state/RunContext'
import type { RunController } from '../state/useRun'

function onlineController(): RunController {
  return {
    state: {
      kind: 'online',
      runId: 'run-overview-7',
      status: { run_id: 'run-overview-7', status: 'running', progress: 0.6, active_policies: ['learned'], error: null },
      results: null,
      events: [],
      offline: false,
      error: null,
    },
    create: async () => undefined,
    resume: async () => undefined,
    refresh: async () => undefined,
    abort: () => undefined,
    exportZip: async () => undefined,
  }
}

describe('overview page', () => {
  it('renders the six-node chain and product runtime status without internal project management', () => {
    const { container } = render(<OverviewPage onNavigate={() => undefined} />)

    expect(screen.getByText(/系统链路/)).toBeInTheDocument()
    expect(screen.getByText('任务到达')).toBeInTheDocument()
    expect(screen.getByText('结果与追溯')).toBeInTheDocument()
    expect(screen.getByText('当前链路态势')).toBeInTheDocument()
    expect(screen.getByText('可用服务')).toBeInTheDocument()
    expect(container).not.toHaveTextContent(/内部提交|A-N\d|B-R\d|I-\d|M-\d|合入 main/)
  })

  it('navigates from chain nodes and quick entries', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<OverviewPage onNavigate={onNavigate} />)

    await user.click(screen.getAllByRole('button', { name: /任务到达/ })[0])
    expect(onNavigate).toHaveBeenCalledWith('flow')

    await user.click(screen.getByRole('button', { name: /策略评估/ }))
    expect(onNavigate).toHaveBeenCalledWith('compare')
  })

  it('keeps demonstration-data honesty visible', () => {
    render(<OverviewPage onNavigate={() => undefined} />)
    expect(screen.getByText(/当前展示为标准场景演示，不作为实验结果/)).toBeInTheDocument()
  })

  it('shows the authoritative run identity when an online task is active', () => {
    render(
      <RunProvider controller={onlineController()}>
        <OverviewPage onNavigate={() => undefined} />
      </RunProvider>,
    )
    expect(screen.getByText(/run-overview-7 · 运行中/)).toBeInTheDocument()
    expect(screen.queryByText(/demo_fixture_001 · completed/)).not.toBeInTheDocument()
  })
})
