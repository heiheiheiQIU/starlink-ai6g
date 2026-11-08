import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TransportError, type RunApi } from '../api/runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type { Event, RunRequest, RunStatusResponse } from '../types/contracts'
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
    const resumedEvent: Event = {
      event_id: 3,
      run_id: 'run-9',
      policy_id: 'learned',
      sim_time_s: 24,
      event_type: 'decision',
      task_id: 'T-009',
      block_id: null,
      payload_bytes: 512,
      overhead_bytes: 24,
      energy_Wh: 0.004,
      reason_code: null,
      data: null,
    }
    api.getRunStatus.mockResolvedValue(runningStatus('run-9'))
    api.getAllEvents.mockResolvedValue([resumedEvent])

    const { result } = renderHook(() => useRun({ api }))
    await act(() => result.current.resume('run-9'))

    expect(api.createRun).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(result.current.state).toMatchObject({
        kind: 'online',
        runId: 'run-9',
        status: { status: 'running' },
        events: [resumedEvent],
      })
    })
    expect(api.getAllEvents).toHaveBeenCalledWith('run-9', 500)
  })

  it('marks transport failure as offline and keeps the last known status', async () => {
    const api = spyApi()
    api.getRunStatus.mockResolvedValueOnce(runningStatus('run-9'))
    api.getRunStatus.mockRejectedValueOnce(new TransportError('请求未到达服务'))

    const { result } = renderHook(() => useRun({ api }))
    await act(() => result.current.resume('run-9'))
    await waitFor(() => {
      expect(result.current.state).toMatchObject({ kind: 'online', status: { status: 'running' } })
    })

    await act(() => result.current.refresh())
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

  it('publishes running status and events before final results complete', async () => {
    const api = spyApi()
    const liveEvent: Event = {
      event_id: 5,
      run_id: 'run-live',
      policy_id: 'learned',
      sim_time_s: 120,
      event_type: 'sent',
      task_id: 'T-101',
      block_id: 1,
      payload_bytes: 1024,
      overhead_bytes: 32,
      energy_Wh: 0.01,
      reason_code: null,
      data: null,
    }
    let releaseCompletion!: () => void
    const completionGate = new Promise<void>((resolve) => { releaseCompletion = resolve })
    api.createRun.mockResolvedValue({ run_id: 'run-live', status: 'queued', schema_version: '1.0' })
    api.getAllEvents.mockResolvedValue([liveEvent])
    api.pollUntilComplete.mockImplementation(async (_id: string, options: { onStatus?: (status: RunStatusResponse) => void | Promise<void> }) => {
      await options.onStatus?.(runningStatus('run-live'))
      await completionGate
      return FIXTURE_RUN_RESULT
    })

    const { result } = renderHook(() => useRun({ api }))
    let createPromise!: Promise<void>
    act(() => { createPromise = result.current.create(REQUEST) })

    await waitFor(() => {
      expect(result.current.state).toMatchObject({
        kind: 'online',
        runId: 'run-live',
        status: { status: 'running', progress: 0.4 },
        events: [liveEvent],
        results: null,
      })
    })

    releaseCompletion()
    await act(() => createPromise)
  })
})
