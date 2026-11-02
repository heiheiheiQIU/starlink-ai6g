/**
 * 真实事件流卡：事件瀑布（按策略分泳道）+ 能量曲线（snapshot 事件的公开估计/下界）。
 * 只读展示；数据来自 GET /runs/{id}/events 全量分页，页面不重算科学指标。
 */

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
  const waterfall = eventWaterfall(events)
  const energy = energySeries(events)

  return (
    <div className="console-card">
      <h2>真实事件流</h2>
      <p className="panel-note" style={{ marginBottom: 12 }}>
        来源：GET /runs/{'{id}'}/events（分页全量，run_id={runId}）；只读展示，页面不重算指标。
      </p>

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
        <p className="panel-note">该 run 暂无事件。</p>
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
