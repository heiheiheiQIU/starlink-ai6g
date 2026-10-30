import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TransportError, type RunApi } from '../api/runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type { RunRequest, RunStatusResponse } from '../types/contracts'
import { useRun } from './useRun'

const REQUEST: RunRequest = {
  schema_version: '1.0',
  config: {},
  policy_ids: ['edf', 'value'],
  seed: 42,
}

function runningStatus(runId: string): RunStatusResponse {
  return { run_id: runId, status: 'running', progress: 0.4, active_policies: ['edf', 'value'], error: null }
}

function completedStatus(runId: string): RunStatusResponse {
  return { run_id: runId, status: 'completed', progress: 1, active_policies: ['edf', 'value'], error: null }
}

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

describe('useRun', () => {
  it('resumes a stored run without creating a new one', async () => {
    const api = spyApi()
    api.getRunStatus.mockResolvedValue(runningStatus('run-9'))

    const { result } = renderHook(() => useRun({ api }))
    await act(() => result.current.resume('run-9'))

    expect(api.createRun).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(result.current.state).toMatchObject({ kind: 'online', runId: 'run-9', status: { status: 'running' } })
    })
  })

  it('marks transport failure as offline and keeps the last known status', async () => {
    const api = spyApi()
    api.getRunStatus.mockResolvedValueOnce(runningStatus('run-9'))
    api.getRunStatus.mockRejectedValueOnce(new TransportError('请求未到达服务'))

    const { result } = renderHook(() => useRun({ api }))
    await act(() => result.current.resume('run-9'))

    await waitFor(() => {
      expect(result.current.state).toMatchObject({ kind: 'online', offline: true })
    })
    expect(result.current.state).toMatchObject({ kind: 'online', status: runningStatus('run-9') })
  })

  it('fetches formal results only after completed status', async () => {
    const api = spyApi()
    api.getRunStatus.mockResolvedValueOnce(runningStatus('run-9'))
    api.getRunStatus.mockResolvedValueOnce(completedStatus('run-9'))
    api.getResults.mockResolvedValue(FIXTURE_RUN_RESULT)

    const { result } = renderHook(() => useRun({ api }))
    await act(() => result.current.resume('run-9'))
    expect(api.getResults).not.toHaveBeenCalled()

    await act(() => result.current.refresh())
    await waitFor(() => {
      expect(result.current.state).toMatchObject({ kind: 'online', results: FIXTURE_RUN_RESULT })
    })
    expect(api.getResults).toHaveBeenCalledWith('run-9')
  })

  it('creates a run and stores its id for refresh recovery', async () => {
    const api = spyApi()
    const storage = { setItem: vi.fn(), getItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn(), key: vi.fn(), length: 0 }
    api.createRun.mockResolvedValue({ run_id: 'run-new', status: 'queued', schema_version: '1.0' })
    api.pollUntilComplete.mockImplementation(async (_id: string, _opts: { signal?: AbortSignal }) => {
      await new Promise((resolve) => setTimeout(resolve, 10))
      return FIXTURE_RUN_RESULT
    })

    const { result } = renderHook(() => useRun({ api, storage }))
    await act(() => result.current.create(REQUEST))

    expect(api.createRun).toHaveBeenCalledWith(REQUEST)
    expect(storage.setItem).toHaveBeenCalledWith('xingdi.runId', 'run-new')
    await waitFor(() => {
      expect(result.current.state).toMatchObject({ kind: 'online', results: FIXTURE_RUN_RESULT })
    })
  })
})
