/**
 * 真实事件流卡：事件瀑布（按策略分泳道）+ 能量曲线（snapshot 事件的公开估计/下界）。
 * 只读展示；数据来自 GET /runs/{id}/events 全量分页，页面不重算科学指标。
 */

import { useEffect, useMemo, useState } from 'react'

import { buildReplayFrames } from '../domain/eventReplay'
import { energySeries, eventWaterfall, WATERFALL_COLORS, WATERFALL_LABELS } from '../domain/eventView'
import type { Event } from '../types/contracts'

interface EventStreamCardProps {
  runId: string
  events: Event[]
}

function toSvgPoints(points: { time: number; value: number }[], minTime: number, maxTime: number, minValue: number, maxValue: number, width: number, height: number): string {
  const span = maxTime - minTime || 1
  const valueSpan = maxValue - minValue || 1
  return points
    .map((point) => {
      const x = 20 + ((point.time - minTime) / span) * (width - 40)
      const y = height - 20 - ((point.value - minValue) / valueSpan) * (height - 40)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

export function EventStreamCard({ runId, events }: EventStreamCardProps) {
  const replay = useMemo(() => {
    try {
      return { frames: buildReplayFrames(events), error: null }
    } catch (error) {
      return { frames: [], error: error instanceof Error ? error.message : String(error) }
    }
  }, [events])
  const [visibleFrames, setVisibleFrames] = useState(replay.frames.length)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<0.5 | 1 | 2 | 4>(1)
  const replayIdentity = `${runId}:${replay.frames.length}:${replay.frames.at(-1)?.events.at(-1)?.event_id ?? 0}`

  useEffect(() => {
    setVisibleFrames(replay.frames.length)
    setPlaying(false)
  }, [replayIdentity, replay.frames.length])

  useEffect(() => {
    if (!playing) return
    if (visibleFrames >= replay.frames.length) {
      setPlaying(false)
      return
    }
    const timer = window.setTimeout(
      () => setVisibleFrames((current) => Math.min(current + 1, replay.frames.length)),
      800 / speed,
    )
    return () => window.clearTimeout(timer)
  }, [playing, replay.frames.length, speed, visibleFrames])

  const visibleEvents = replay.frames
    .slice(0, visibleFrames)
    .flatMap((frame) => frame.events)
  const waterfall = eventWaterfall(visibleEvents)
  const energy = energySeries(visibleEvents)

  return (
    <div className="console-card">
      <h2>在线事件记录</h2>
      <p className="panel-note" style={{ marginBottom: 12 }}>
        来源：GET /runs/{'{id}'}/events（分页全量，run_id={runId}）；只读展示，页面不重算指标。
      </p>

      {replay.error ? (
        <div className="stale-banner" role="alert">
          事件合同错误：{replay.error}。已停止回放，未合并冲突事件。
        </div>
      ) : (
        <div className="event-replay-controls" aria-label="事件回放控制">
          <strong className="mono">{visibleFrames} / {replay.frames.length} 帧</strong>
          <button
            type="button"
            onClick={() => { setVisibleFrames(0); setPlaying(false) }}
            disabled={replay.frames.length === 0}
          >
            从头回放
          </button>
          <button
            type="button"
            aria-label="单步推进回放"
            onClick={() => { setPlaying(false); setVisibleFrames((current) => Math.min(current + 1, replay.frames.length)) }}
            disabled={visibleFrames >= replay.frames.length}
          >
            单步
          </button>
          <button
            type="button"
            onClick={() => setPlaying((current) => !current)}
            disabled={replay.frames.length === 0 || visibleFrames >= replay.frames.length}
          >
            {playing ? '暂停回放' : '播放回放'}
          </button>
          <span className="event-replay-controls__speed" aria-label="回放速度">
            {([0.5, 1, 2, 4] as const).map((value) => (
              <button
                type="button"
                key={value}
                aria-pressed={speed === value}
                onClick={() => setSpeed(value)}
              >
                {value}×
              </button>
            ))}
          </span>
          <small>仅改变前端回放速度，不暂停或加速后台仿真。</small>
        </div>
      )}

      {waterfall.lanes.length > 0 ? (
        <div className="waterfall" aria-label="事件瀑布图">
          {waterfall.lanes.map((lane) => (
            <div className="waterfall__lane" key={lane.policyId}>
              <span className="waterfall__policy mono">{lane.policyId}</span>
              <div className="waterfall__track">
                {lane.blocks.map((block) => {
                  const position =
                    waterfall.maxTime - waterfall.minTime > 0
                      ? ((block.time - waterfall.minTime) / (waterfall.maxTime - waterfall.minTime)) * 100
                      : 0
                  return (
                    <i
                      key={block.eventId}
                      className="waterfall__block"
                      style={{ left: `${Math.min(98, Math.max(0, position))}%`, background: WATERFALL_COLORS[block.kind] }}
                      title={block.title}
                    />
                  )
                })}
              </div>
            </div>
          ))}
          <div className="waterfall__legend">
            {waterfall.kinds.map((kind) => (
              <span key={kind}>
                <i style={{ background: WATERFALL_COLORS[kind] }} />
                {WATERFALL_LABELS[kind]}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="panel-note">{events.length > 0 ? '等待回放事件。' : '该任务实例暂无事件。'}</p>
      )}

      {energy.length >= 2 ? (
        <div className="energy-chart">
          <svg
            viewBox="0 0 620 180"
            role="img"
            aria-label="能量曲线（真实事件快照）"
          >
            <polyline
              points={toSvgPoints(energy.map((point) => ({ time: point.time, value: point.est })), energy[0].time, energy[energy.length - 1].time, Math.min(...energy.map((point) => point.lower)), Math.max(...energy.map((point) => point.est)), 620, 180)}
              fill="none"
              stroke="#3bd4ed"
              strokeWidth="2"
            />
            <polyline
              points={toSvgPoints(energy.map((point) => ({ time: point.time, value: point.lower })), energy[0].time, energy[energy.length - 1].time, Math.min(...energy.map((point) => point.lower)), Math.max(...energy.map((point) => point.est)), 620, 180)}
              fill="none"
              stroke="#f6c453"
              strokeWidth="1.5"
              strokeDasharray="5 4"
            />
          </svg>
          <p className="panel-note">
            实线=公开能量估计，虚线=公开能量下界（snapshot 事件原值，不重算）；时间轴 {energy[0].time}s → {energy[energy.length - 1].time}s。
          </p>
        </div>
      ) : null}
    </div>
  )
}
