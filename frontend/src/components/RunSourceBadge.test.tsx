import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TransportError, type RunApi } from '../api/runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import { RUN_ID_STORAGE_KEY } from '../state/useRun'
import { RunSourceBadge } from './RunSourceBadge'

function spyApi() {
  const api = {
    createRun: vi.fn(),
    getRunStatus: vi.fn(),
    getResults: vi.fn(),
    getEvents: vi.fn(),
    getAllEvents: vi.fn(),
    exportRun: vi.fn(),
    pollUntilComplete: vi.fn(),
  }
  return api as unknown as RunApi & typeof api
}

function fakeStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() { return map.size },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => Array.from(map.keys())[index] ?? null,
    removeItem: (key: string) => { map.delete(key) },
    setItem: (key: string, value: string) => { map.set(key, value) },
  }
}

describe('RunSourceBadge', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows explicit demo-data mode when no backend run is known', () => {
    const storage = fakeStorage()
    render(<RunSourceBadge api={spyApi()} storage={storage} />)

    expect(screen.getByRole('status')).toHaveTextContent('演示数据模式')
    expect(screen.getByText(/契约样例，非真实运行结果/)).toBeInTheDocument()
  })

  it('resumes a stored run without creating a new one', async () => {
    const storage = fakeStorage()
    storage.setItem(RUN_ID_STORAGE_KEY, 'run-9')
    const api = spyApi()
    api.getRunStatus.mockResolvedValue({
      run_id: 'run-9', status: 'running', progress: 0.4, active_policies: ['edf', 'value'], error: null,
    })

    render(<RunSourceBadge api={api} storage={storage} />)

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('已连接实验服务')
    })
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it('shows offline banner with retry and keeps the last known state', async () => {
    const user = userEvent.setup()
    const storage = fakeStorage()
    storage.setItem(RUN_ID_STORAGE_KEY, 'run-9')
    const api = spyApi()
    api.getRunStatus.mockResolvedValueOnce({
      run_id: 'run-9', status: 'running', progress: 0.2, active_policies: ['edf'], error: null,
    })
    api.getRunStatus.mockRejectedValue(new TransportError('请求未到达服务'))

    render(<RunSourceBadge api={api} storage={storage} />)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('服务连接失败')
    })

    api.getRunStatus.mockResolvedValue({
      run_id: 'run-9', status: 'running', progress: 0.5, active_policies: ['edf'], error: null,
    })
    await user.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('已连接实验服务')
    })
  })

  it('shows formal results only for completed runs', async () => {
    const storage = fakeStorage()
    storage.setItem(RUN_ID_STORAGE_KEY, 'run-9')
    const api = spyApi()
    api.getRunStatus.mockResolvedValue({
      run_id: 'run-9', status: 'completed', progress: 1, active_policies: ['edf', 'value'], error: null,
    })
    api.getResults.mockResolvedValue(FIXTURE_RUN_RESULT)

    render(<RunSourceBadge api={api} storage={storage} />)

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('正式结果可用')
    })
  })

  it('does not retry polling after a failed run', async () => {
    vi.useFakeTimers()
    try {
      const storage = fakeStorage()
      storage.setItem(RUN_ID_STORAGE_KEY, 'run-9')
      const api = spyApi()
      api.getRunStatus.mockResolvedValue({
        run_id: 'run-9', status: 'failed', progress: null, active_policies: [], error: {
          code: 'INTERNAL_RUN_ERROR', message: 'boom', details: {},
        },
      })

      render(<RunSourceBadge api={api} storage={storage} />)
      await act(async () => { await vi.runOnlyPendingTimersAsync() })
      expect(api.getRunStatus).toHaveBeenCalledTimes(1)
    } finally {
      vi.useRealTimers()
    }
  })
})
