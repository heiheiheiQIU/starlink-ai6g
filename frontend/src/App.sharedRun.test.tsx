import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import App from './App'
import type { RunController } from './state/useRun'

function onlineController(): RunController {
  return {
    state: {
      kind: 'online',
      runId: 'run_shared_42',
      status: {
        run_id: 'run_shared_42',
        status: 'running',
        progress: 0.4,
        active_policies: ['edf', 'learned'],
        error: null,
      },
      results: null,
      events: null,
      offline: false,
      error: null,
    },
    create: vi.fn(),
    resume: vi.fn(),
    refresh: vi.fn(),
    abort: vi.fn(),
    exportZip: vi.fn(),
  }
}

describe('App shared run root', () => {
  it('restores once and exposes the same run to comparison and evidence pages', async () => {
    const controller = onlineController()
    const storage = {
      getItem: vi.fn(() => 'run_saved_99'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
      key: vi.fn(),
      length: 1,
    } satisfies Storage

    render(<App runController={controller} storage={storage} />)
    await waitFor(() => expect(controller.resume).toHaveBeenCalledTimes(1))
    expect(controller.resume).toHaveBeenCalledWith('run_saved_99')
    expect(screen.getByLabelText('数据状态说明')).toHaveTextContent('在线任务')
    expect(screen.getByLabelText('数据状态说明')).toHaveTextContent('run_shared_42')
    expect(screen.getByText('运行中 · run_shared_42')).toBeInTheDocument()
    expect(screen.getByLabelText('数据状态说明')).not.toHaveTextContent('标准场景演示')

    fireEvent.click(screen.getByRole('button', { name: '策略评估' }))
    expect(screen.getAllByText('run_shared_42').length).toBeGreaterThan(0)
    expect(screen.getByText('暂无上一任务')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '结果追溯' }))
    expect(screen.getByText('run_shared_42')).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button', { name: '智能研判' })[0])
    expect(screen.getByText('在线任务已连接')).toBeInTheDocument()
  })

  it('refreshes an active shared run globally without requiring a specific page', async () => {
    vi.useFakeTimers()
    try {
      const controller = onlineController()
      const storage = {
        getItem: vi.fn(() => null), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn(), key: vi.fn(), length: 0,
      } satisfies Storage
      render(<App runController={controller} storage={storage} />)

      await act(async () => { await vi.advanceTimersByTimeAsync(2100) })
      expect(controller.refresh).toHaveBeenCalledTimes(1)
    } finally {
      vi.useRealTimers()
    }
  })
})
