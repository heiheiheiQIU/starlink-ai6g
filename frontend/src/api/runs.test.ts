import { afterEach, describe, expect, it, vi, type Mock } from 'vitest'

import { ApiError, createRunApi, ResponseFormatError, TransportError } from './runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type {
  ErrorBody,
  Event,
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

function event(eventId: number): Event {
  return {
    event_id: eventId,
    run_id: 'run-1',
    policy_id: 'edf',
    sim_time_s: eventId,
    event_type: 'snapshot',
    task_id: null,
    block_id: null,
    payload_bytes: 0,
    overhead_bytes: 0,
    energy_Wh: 0,
    reason_code: null,
    data: null,
  }
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

  it('reports malformed successful JSON as an explicit response format error', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValue(new Response('{not-json', { status: 200 }))
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.getRunStatus('run-1').catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ResponseFormatError)
    expect((error as Error).message).toMatch(/JSON/)
  })

  it('collects all event pages in backend order', async () => {
    const pages: EventsPage[] = [
      { run_id: 'run-1', events: [event(1), event(2)], next_after: 2, has_more: true },
      { run_id: 'run-1', events: [event(3)], next_after: 3, has_more: false },
    ]
    const fetchFn = mockFetch()
    fetchFn.mockImplementation(() => Promise.resolve(jsonResponse(pages.shift())))
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    await expect(api.getAllEvents('run-1', 2)).resolves.toEqual([event(1), event(2), event(3)])
    expect(fetchFn).toHaveBeenNthCalledWith(1, 'http://x/runs/run-1/events?after=0&limit=2', undefined)
    expect(fetchFn).toHaveBeenNthCalledWith(2, 'http://x/runs/run-1/events?after=2&limit=2', undefined)
  })

  it('rejects an event page whose cursor does not advance', async () => {
    const fetchFn = mockFetch()
    fetchFn
      .mockResolvedValueOnce(
        jsonResponse({ run_id: 'run-1', events: [event(1)], next_after: 0, has_more: true } satisfies EventsPage),
      )
      .mockRejectedValueOnce(new Error('unexpected second page request'))
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })

    const error = await api.getAllEvents('run-1', 2).catch((value: unknown) => value)
    expect(error).toBeInstanceOf(ResponseFormatError)
    expect((error as Error).message).toMatch(/游标/)
    expect(fetchFn).toHaveBeenCalledTimes(1)
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

  it('aborts promptly while waiting between status polls', async () => {
    const fetchFn = mockFetch()
    fetchFn.mockResolvedValue(
      jsonResponse({
        run_id: 'run-1',
        status: 'running',
        progress: 0.2,
        active_policies: ['edf'],
        error: null,
      } satisfies RunStatusResponse),
    )
    const api = createRunApi({ baseUrl: 'http://x/', fetchFn })
    const controller = new AbortController()
    const polling = api.pollUntilComplete('run-1', {
      intervalMs: 80,
      timeoutMs: 1000,
      signal: controller.signal,
    })

    await new Promise((resolve) => setTimeout(resolve, 5))
    controller.abort()
    let outcome: string
    try {
      outcome = await Promise.race([
        polling.then(() => 'completed', (error: unknown) =>
          error instanceof TransportError && error.message === '轮询已中止' ? 'aborted' : 'wrong-error',
        ),
        new Promise<string>((resolve) => setTimeout(() => resolve('still-waiting'), 25)),
      ])
      expect(outcome).toBe('aborted')
    } finally {
      await polling.catch(() => undefined)
    }
  })
})
