/**
 * 数据源状态指示（接入 useRun）：
 * - 有已存 run_id → 自动恢复并轮询，不重复创建；
 * - 未连接 → 明确展示"演示数据"而非假装在线；
 * - transport 失败 → offline 横幅＋重试；
 * - 只有 completed 显示正式结果标识。
 */

import { useEffect, useState } from 'react'

import { ApiError, TransportError, type RunApi } from '../api/runs'
import { DEFAULT_BASE_URL, RUN_ID_STORAGE_KEY, useRun } from '../state/useRun'

interface RunSourceBadgeProps {
  api?: RunApi
  storage?: Storage
}

export function RunSourceBadge({ api, storage }: RunSourceBadgeProps) {
  const { state, resume, refresh } = useRun({ api, storage, baseUrl: DEFAULT_BASE_URL })
  const [polling, setPolling] = useState(false)

  useEffect(() => {
    const source = storage ?? window.localStorage
    const stored = source.getItem(RUN_ID_STORAGE_KEY)
    if (stored) {
      void resume(stored)
    }
  }, [storage, resume])

  const statusName = state.kind === 'online' ? state.status?.status : undefined
  const onlineRunId = state.kind === 'online' ? state.runId : null

  useEffect(() => {
    if (state.kind !== 'online') {
      setPolling(false)
      return
    }
    const active = statusName === 'queued' || statusName === 'running'
    setPolling(active)
    if (!active) return
    const timer = window.setInterval(() => void refresh(), 2000)
    return () => window.clearInterval(timer)
  }, [state.kind, statusName, onlineRunId, refresh])

  if (state.kind === 'idle') {
    return (
      <div className="source-badge source-badge--fixture" role="status">
        <strong>演示数据模式</strong>
        <span>未连接实验服务；页面内容为契约样例，非真实运行结果。</span>
      </div>
    )
  }

  if (state.kind === 'fixture') {
    return (
      <div className="source-badge source-badge--fixture" role="status">
        <strong>演示数据模式</strong>
        <span>{state.note}</span>
      </div>
    )
  }

  const { runId, status, results, offline, error } = state
  if (offline) {
    return (
      <div className="source-badge source-badge--offline" role="alert">
        <strong>服务连接失败</strong>
        <span>{error ?? '请求未到达服务'}；已保留最后一次已确认状态。</span>
        <button type="button" onClick={() => void refresh()}>重试</button>
      </div>
    )
  }

  if (error) {
    return (
      <div className="source-badge source-badge--error" role="alert">
        <strong>运行异常</strong>
        <span>{error}</span>
        <button type="button" onClick={() => void refresh()}>刷新</button>
      </div>
    )
  }

  const statusLabel = status?.status ?? 'unknown'
  return (
    <div className="source-badge source-badge--online" role="status">
      <strong>已连接实验服务</strong>
      <span className="mono">{runId}</span>
      <span>
        {statusLabel === 'completed'
          ? `已完成${results ? ' · 正式结果可用' : ' · 读取结果中'}`
          : statusLabel === 'running'
            ? `运行中${polling ? ' · 自动轮询' : ''}${status?.progress !== null && status?.progress !== undefined ? ` ${Math.round(status.progress * 100)}%` : ''}`
            : statusLabel === 'failed'
              ? '失败 · 保留现场，不显示正式指标'
              : statusLabel === 'queued'
                ? '排队中'
                : '未知状态'}
      </span>
    </div>
  )
}
