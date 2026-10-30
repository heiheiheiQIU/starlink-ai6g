/**
 * 单个 run 的页面状态钩子（C-N3 联调准备）。
 *
 * 纪律：刷新恢复已存在的 run_id（绝不重复 POST）；transport 失败进入 offline 并
 * 保留最后一次已确认状态；只有 completed 才取正式结果；fixture 模式仅在明确未接
 * API 时使用，不伪装"请求成功"。
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError, TransportError, createRunApi, type RunApi } from '../api/runs'
import type { RunRequest, RunResult, RunStatusResponse } from '../types/contracts'

export type RunSource =
  | { kind: 'idle' }
  | { kind: 'fixture'; note: string }
  | {
      kind: 'online'
      runId: string
      status: RunStatusResponse | null
      results: RunResult | null
      offline: boolean
      error: string | null
    }

export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
export const RUN_ID_STORAGE_KEY = 'xingdi.runId'

export interface UseRunOptions {
  baseUrl?: string
  api?: RunApi
  storage?: Storage
}

export interface RunController {
  state: RunSource
  create: (request: RunRequest) => Promise<void>
  resume: (runId: string) => Promise<void>
  refresh: () => Promise<void>
  abort: () => void
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return `${error.code}：${error.message}`
  if (error instanceof TransportError) return error.message
  return error instanceof Error ? error.message : String(error)
}

export function useRun(options: UseRunOptions = {}): RunController {
  const apiRef = useRef<RunApi | null>(null)
  if (apiRef.current === null) {
    apiRef.current = options.api ?? createRunApi({ baseUrl: options.baseUrl ?? DEFAULT_BASE_URL })
  }
  const api = apiRef.current
  const storage = options.storage
  const [state, setState] = useState<RunSource>({ kind: 'idle' })
  const controllerRef = useRef<AbortController | null>(null)
  const lastStatusRef = useRef<RunStatusResponse | null>(null)

  function setOnline(runId: string, patch: Partial<Extract<RunSource, { kind: 'online' }>>) {
    setState((current) => {
      const base =
        current.kind === 'online' && current.runId === runId
          ? current
          : { kind: 'online', runId, status: lastStatusRef.current, results: null, offline: false, error: null }
      return { ...base, ...patch } as Extract<RunSource, { kind: 'online' }>
    })
  }

  function rememberRunId(runId: string) {
    storage?.setItem(RUN_ID_STORAGE_KEY, runId)
  }

  function clearSignal() {
    controllerRef.current?.abort()
    controllerRef.current = null
  }

  const abort = useCallback(() => {
    controllerRef.current?.abort()
  }, [])

  const create = useCallback(
    async (request: RunRequest) => {
      clearSignal()
      const controller = new AbortController()
      controllerRef.current = controller
      try {
        const created = await api.createRun(request)
        rememberRunId(created.run_id)
        lastStatusRef.current = { run_id: created.run_id, status: 'queued', progress: 0, active_policies: request.policy_ids, error: null }
        setState({
          kind: 'online',
          runId: created.run_id,
          status: lastStatusRef.current,
          results: null,
          offline: false,
          error: null,
        })
        const results = await api.pollUntilComplete(created.run_id, { signal: controller.signal })
        lastStatusRef.current = { run_id: created.run_id, status: 'completed', progress: 1, active_policies: request.policy_ids, error: null }
        setState({ kind: 'online', runId: created.run_id, status: lastStatusRef.current, results, offline: false, error: null })
      } catch (error) {
        if (controller.signal.aborted) return
        const offline = error instanceof TransportError
        setOnline(lastStatusRef.current?.run_id ?? '', {
          offline,
          error: errorMessage(error),
        })
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null
      }
    },
    [api, storage],
  )

  const refresh = useCallback(async () => {
    const runId = lastStatusRef.current?.run_id
    if (!runId) return
    try {
      const status = await api.getRunStatus(runId)
      lastStatusRef.current = status
      setOnline(runId, { status, offline: false, error: null })
      if (status.status === 'completed') {
        const results = await api.getResults(runId)
        setOnline(runId, { results })
      }
    } catch (error) {
      const offline = error instanceof TransportError
      setOnline(runId, { offline, error: errorMessage(error) })
    }
  }, [api])

  const resume = useCallback(
    async (runId: string) => {
      rememberRunId(runId)
      lastStatusRef.current = { run_id: runId, status: 'running', progress: null, active_policies: [], error: null }
      setState({ kind: 'online', runId, status: lastStatusRef.current, results: null, offline: false, error: null })
      await refresh()
    },
    [refresh, storage],
  )

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  return { state, create, resume, refresh, abort }
}
