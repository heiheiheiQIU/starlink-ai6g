/**
 * H00 HTTP 合同的类型化客户端（C-N3 骨架）。
 *
 * 边界：本层只做传输与错误体解析，不重算指标、不猜测后端语义；
 * 网络失败与后端业务失败分开（TransportError vs ApiError），
 * 错误码按 H00 合同 ErrorCode 呈现，未知码标 UNKNOWN 不冒充已知。
 */

import type {
  ErrorBody,
  ErrorCode,
  Event,
  EventsPage,
  RunCreated,
  RunRequest,
  RunResult,
  RunStatusResponse,
} from '../types/contracts'

export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorCode | 'UNKNOWN'
  readonly details: Record<string, unknown>

  constructor(status: number, code: ErrorCode | 'UNKNOWN', message: string, details: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export class TransportError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'TransportError'
  }
}

export class ResponseFormatError extends Error {
  readonly path: string

  constructor(path: string, message: string) {
    super(message)
    this.name = 'ResponseFormatError'
    this.path = path
  }
}

export interface RunApiOptions {
  /** 例如 http://127.0.0.1:8000；末尾斜杠会被忽略。 */
  baseUrl: string
  /** 测试注入点；默认使用全局 fetch。 */
  fetchFn?: typeof fetch
}

export interface PollOptions {
  intervalMs?: number
  timeoutMs?: number
  signal?: AbortSignal
}

const JSON_HEADERS = { 'Content-Type': 'application/json' }

function waitForPoll(intervalMs: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(new TransportError('轮询已中止'))
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort)
      resolve()
    }, intervalMs)
    function abort() {
      clearTimeout(timer)
      signal?.removeEventListener('abort', abort)
      reject(new TransportError('轮询已中止'))
    }
    signal?.addEventListener('abort', abort, { once: true })
  })
}

export function createRunApi({ baseUrl, fetchFn }: RunApiOptions) {
  const base = baseUrl.replace(/\/+$/, '')
  const fetcher = fetchFn ?? ((...args: Parameters<typeof fetch>) => fetch(...args))

  async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response
    try {
      response = await fetcher(`${base}${path}`, init)
    } catch (cause) {
      throw new TransportError(`请求未到达服务：${cause instanceof Error ? cause.message : String(cause)}`)
    }

    if (response.ok) {
      try {
        return (await response.json()) as T
      } catch {
        throw new ResponseFormatError(path, `服务成功响应不是有效 JSON：${path}`)
      }
    }

    let body: ErrorBody | null = null
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      body = null
    }
    throw new ApiError(
      response.status,
      body?.code ?? 'UNKNOWN',
      body?.message ?? `HTTP ${response.status}`,
      body?.details ?? {},
    )
  }

  async function requestBlob(path: string): Promise<Blob> {
    let response: Response
    try {
      response = await fetcher(`${base}${path}`)
    } catch (cause) {
      throw new TransportError(`请求未到达服务：${cause instanceof Error ? cause.message : String(cause)}`)
    }
    if (response.ok) {
      return response.blob()
    }
    let body: ErrorBody | null = null
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      body = null
    }
    throw new ApiError(
      response.status,
      body?.code ?? 'UNKNOWN',
      body?.message ?? `HTTP ${response.status}`,
      body?.details ?? {},
    )
  }

  function getEvents(runId: string, query: { after?: number; limit?: number } = {}): Promise<EventsPage> {
    const params = new URLSearchParams()
    if (query.after !== undefined) params.set('after', String(query.after))
    if (query.limit !== undefined) params.set('limit', String(query.limit))
    const suffix = params.size > 0 ? `?${params.toString()}` : ''
    return requestJson<EventsPage>(`/runs/${encodeURIComponent(runId)}/events${suffix}`)
  }

  return {
    /** POST /runs → 202 RunCreated；422 非法配置/重复策略、429 容量不足由 ApiError 呈现。 */
    createRun(request: RunRequest): Promise<RunCreated> {
      return requestJson<RunCreated>('/runs', {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify(request),
      })
    },

    /** GET /runs/{id} → RunStatusResponse；404 见 ApiError。 */
    getRunStatus(runId: string): Promise<RunStatusResponse> {
      return requestJson<RunStatusResponse>(`/runs/${encodeURIComponent(runId)}`)
    },

    /** GET /runs/{id}/events?after=&limit= → EventsPage；游标非法 422。 */
    getEvents,

    /** 顺序读取全部事件页；只拼接后端事件，不跨策略重排或推导。 */
    async getAllEvents(runId: string, pageLimit = 200): Promise<Event[]> {
      const events: Event[] = []
      let after = 0
      for (;;) {
        const page = await getEvents(runId, { after, limit: pageLimit })
        events.push(...page.events)
        if (!page.has_more) return events
        if (page.next_after <= after) {
          throw new ResponseFormatError(
            `/runs/${encodeURIComponent(runId)}/events`,
            '事件分页游标没有向前推进',
          )
        }
        after = page.next_after
      }
    },

    /** GET /runs/{id}/results → RunResult；未完成 409（RUN_NOT_COMPLETE）。 */
    getResults(runId: string): Promise<RunResult> {
      return requestJson<RunResult>(`/runs/${encodeURIComponent(runId)}/results`)
    },

    /** GET /runs/{id}/export → ZIP Blob；未完成 409；页面只消费下载，不解析内容。 */
    exportRun(runId: string): Promise<Blob> {
      return requestBlob(`/runs/${encodeURIComponent(runId)}/export`)
    },

    /**
     * 轮询直到 run 完成并返回正式结果。failed/cancelled 直接抛出（不返回 partial 冒充成功）；
     * 超时抛出 TransportError；中断由 AbortSignal 控制。
     */
    async pollUntilComplete(runId: string, options: PollOptions = {}): Promise<RunResult> {
      const { intervalMs = 1000, timeoutMs = 60_000, signal } = options
      const startedAt = Date.now()

      for (;;) {
        if (signal?.aborted) throw new TransportError('轮询已中止')

        const status = await this.getRunStatus(runId)
        if (status.status === 'completed') {
          return this.getResults(runId)
        }
        if (status.status === 'failed' || status.status === 'cancelled') {
          throw new ApiError(
            409,
            status.status === 'failed' ? 'INTERNAL_RUN_ERROR' : 'UNKNOWN',
            status.error?.message ?? `run ${status.status}`,
            status.error?.details ?? {},
          )
        }
        if (Date.now() - startedAt >= timeoutMs) {
          throw new TransportError(`等待 run 完成超时（${timeoutMs}ms）`)
        }
        await waitForPoll(intervalMs, signal)
      }
    },
  }
}

export type RunApi = ReturnType<typeof createRunApi>
