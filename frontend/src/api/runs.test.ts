import { afterEach, describe, expect, it, vi, type Mock } from 'vitest'

import { ApiError, createRunApi, TransportError } from './runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type {
  ErrorBody,
  EventsPage,
  RunCreated,
  RunRequest,
  RunStatusResponse,
} from '../types/contracts'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function errorResponse(body: ErrorBody, status: number): Response {
  return jsonResponse(body, status)
}

const REQUEST: RunRequest = {
  schema_version: '1.0',
  config: {},
  policy_ids: ['edf', 'learned'],
  seed: 42,
}

const CREATED: RunCreated = { run_id: 'run-1', status: 'queued', schema_version: '1.0' }

function mockFetch(): Mock<typeof fetch> {
  return vi.fn()
}

describe('run api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('creates a run and parses 202', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValue(jsonResponse(CREATED, 202))
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    await expect(api.createRun(REQUEST)).resolves.toEqual(CREATED)
    expect(fetchFn).toHaveBeenCalledWith(
      'http://x/runs',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('maps contract error bodies to typed ApiError', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValueOnce(
      errorResponse({ code: 'INVALID_CONFIG', message: 'bad config', details: { field: 'seed' } }, 422),
    )
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.createRun(REQUEST).catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(422)
    expect((error as ApiError).code).toBe('INVALID_CONFIG')
    expect((error as ApiError).details).toEqual({ field: 'seed' })
  })

  it('flags RUN_NOT_COMPLETE when results are read before completion', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValue(
      errorResponse({ code: 'RUN_NOT_COMPLETE', message: 'running', details: {} }, 409),
    )
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.getResults('run-1').catch((value: unknown) => value)
    expect((error as ApiError).code).toBe('RUN_NOT_COMPLETE')
  })

  it('builds event pagination query only for provided fields', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockImplementation(() =>
      Promise.resolve(jsonResponse({ run_id: 'run-1', events: [], next_after: 0, has_more: false } satisfies EventsPage)),
    )
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    await api.getEvents('run-1', { after: 5, limit: 100 })
    expect(fetchFn).toHaveBeenCalledWith('http://x/runs/run-1/events?after=5&limit=100', undefined)

    await api.getEvents('run-1')
    expect(fetchFn).toHaveBeenCalledWith('http://x/runs/run-1/events', undefined)
  })

  it('surfaces transport failures separately from backend failures', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockRejectedValue(new TypeError('fetch failed'))
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.getRunStatus('run-1').catch((value: unknown) => value)
    expect(error).toBeInstanceOf(TransportError)
  })

  it('polls until completed and returns formal results only then', async () => {
    const statuses: RunStatusResponse[] = [
      { run_id: 'run-1', status: 'queued', progress: null, active_policies: [], error: null },
      { run_id: 'run-1', status: 'running', progress: 0.4, active_policies: ['edf', 'learned'], error: null },
      { run_id: 'run-1', status: 'completed', progress: 1, active_policies: ['edf', 'learned'], error: null },
    ]
    let calls = 0
    const fetchFn = mockFetch()
    fetchFn.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/results')) {
        return jsonResponse(FIXTURE_RUN_RESULT)
      }
      calls += 1
      return jsonResponse(statuses[Math.min(calls - 1, statuses.length - 1)])
    })
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    await expect(api.pollUntilComplete('run-1', { intervalMs: 5, timeoutMs: 2000 })).resolves.toEqual(
      FIXTURE_RUN_RESULT,
    )
  })

  it('never returns partial results for failed runs', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValue(
      jsonResponse({
        run_id: 'run-1',
        status: 'failed',
        progress: null,
        active_policies: [],
        error: { code: 'INTERNAL_RUN_ERROR', message: 'boom', details: {} },
      } satisfies RunStatusResponse),
    )
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.pollUntilComplete('run-1', { intervalMs: 5 }).catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('INTERNAL_RUN_ERROR')
  })
})
