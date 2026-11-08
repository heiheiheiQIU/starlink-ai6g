import { normalizeReplayEvents } from '../domain/eventReplay'
import type { DecisionData, Event, SnapshotData, WindowChangedData } from '../types/contracts'

interface LiveStageExperienceProps {
  stepId: string
  events: readonly Event[]
}

const TRANSPORT_TYPES = new Set<Event['event_type']>(['sent', 'received', 'acked', 'dropped', 'fallback'])

function decisionData(event: Event): DecisionData | null {
  if (event.event_type !== 'decision' || event.data === null || !('action' in event.data)) return null
  return event.data as DecisionData
}

function snapshotData(event: Event): SnapshotData | null {
  if (event.event_type !== 'snapshot' || event.data === null || !('energy_est_Wh' in event.data)) return null
  return event.data as SnapshotData
}

function windowData(event: Event): WindowChangedData | null {
  if (event.event_type !== 'window_changed' || event.data === null || !('window_id' in event.data)) return null
  return event.data as WindowChangedData
}

function relevantEvents(stepId: string, events: Event[]): Event[] {
  if (stepId === 'arrival') return events.filter((event) => event.event_type === 'arrived')
  if (stepId === 'forecast') return events.filter((event) => event.event_type === 'window_changed' || event.event_type === 'snapshot')
  if (stepId === 'score' || stepId === 'decode') return events.filter((event) => event.event_type === 'decision')
  if (stepId === 'confirm') return events.filter((event) => TRANSPORT_TYPES.has(event.event_type))
  return events
}

export function LiveStageExperience({ stepId, events }: LiveStageExperienceProps) {
  let ordered: Event[]
  try {
    ordered = normalizeReplayEvents(events)
  } catch (error) {
    return <div className="live-stage live-stage--error" role="alert">事件合同错误：{error instanceof Error ? error.message : String(error)}</div>
  }
  const relevant = relevantEvents(stepId, ordered)
  const latest = relevant.at(-1)

  if (!latest) {
    return (
      <div className="live-stage live-stage--waiting" role="status">
        <span className="live-pill">在线任务</span>
        <strong>等待该阶段的权威事件</strong>
        <small>页面不会以标准场景数据填充在线任务空缺。</small>
      </div>
    )
  }

  if (stepId === 'score' || stepId === 'decode') {
    const data = decisionData(latest)
    if (!data) return <div className="live-stage live-stage--error" role="alert">decision事件缺少合同内决策数据。</div>
    const candidates = [...data.candidate_scores].sort((a, b) => b.score - a.score)
    return (
      <div className="live-stage live-stage--decision">
        <header><span className="live-pill">在线决策 · e={latest.event_id}</span><small>t={latest.sim_time_s}s · {latest.policy_id}</small></header>
        <div className="live-decision-action">
          <span>后端执行动作</span>
          <strong>{data.action.task_id ?? 'idle'} × {data.action.mode} · {data.action.scheduled_bytes} B</strong>
          <small>{data.fallback ? '已触发安全回退' : '未触发回退'} · latency={data.latency_ms} ms</small>
        </div>
        <div className="live-candidate-grid" aria-label="在线候选评分">
          {candidates.map((candidate) => (
            <span key={`${candidate.task_id}-${candidate.mode}`}>
              <small>{candidate.task_id ?? 'idle'}</small>
              <strong className="mono">{candidate.mode} {candidate.score.toFixed(3)}</strong>
            </span>
          ))}
        </div>
        <div className="live-guard-list" aria-label="在线约束检查">
          {data.constraint_checks.map((check) => (
            <div key={check.code} data-passed={check.passed}>
              <span>{check.passed ? '✓' : '×'}</span><strong>{check.code}</strong><small>{check.passed ? '通过' : '拒绝'}</small>
            </div>
          ))}
        </div>
        <p>以上分数、动作和约束结论均为后端事件原值，前端不重算、不改判。</p>
      </div>
    )
  }

  if (stepId === 'confirm') {
    const count = (type: Event['event_type']) => relevant.filter((event) => event.event_type === type).length
    return (
      <div className="live-stage live-stage--transport">
        <header><span className="live-pill">在线链路事件</span><small>最新 e={latest.event_id} · t={latest.sim_time_s}s</small></header>
        <div className="live-transport-counts">
          <strong>发送 {count('sent')}</strong><strong>接收 {count('received')}</strong><strong>确认 {count('acked')}</strong><strong data-alert={count('dropped') > 0}>丢失 {count('dropped')}</strong>
        </div>
        <ol>
          {relevant.slice(-8).map((event) => (
            <li key={event.event_id} data-kind={event.event_type}>
              <span className="mono">e={event.event_id} · {event.event_type}</span>
              <strong>{event.task_id ?? '—'} · block {event.block_id ?? '—'} · {event.payload_bytes} B</strong>
              <small>{event.reason_code ?? `t=${event.sim_time_s}s`}</small>
            </li>
          ))}
        </ol>
      </div>
    )
  }

  if (stepId === 'forecast') {
    return (
      <div className="live-stage live-stage--forecast">
        <header><span className="live-pill">在线观测事件</span><small>{relevant.length}条</small></header>
        <div className="live-event-cards">
          {relevant.slice(-6).map((event) => {
            const window = windowData(event)
            const snapshot = snapshotData(event)
            return <div key={event.event_id}><span className="mono">e={event.event_id} · t={event.sim_time_s}s</span><strong>{window ? `${window.window_id} · ${window.is_visible ? '可见' : '不可见'}` : snapshot ? `能量 ${snapshot.energy_est_Wh} Wh · 下界 ${snapshot.energy_lower_Wh} Wh` : event.event_type}</strong></div>
          })}
        </div>
      </div>
    )
  }

  if (stepId === 'arrival') {
    return (
      <div className="live-stage live-stage--arrival">
        <header><span className="live-pill">在线到达事件</span><small>{relevant.length}项</small></header>
        <div className="live-event-cards">{relevant.map((event) => <div key={event.event_id}><span className="mono">e={event.event_id}</span><strong>{event.task_id ?? '未知任务'} · {event.payload_bytes} B</strong><small>t={event.sim_time_s}s</small></div>)}</div>
      </div>
    )
  }

  const policies = new Set(ordered.map((event) => event.policy_id))
  return (
    <div className="live-stage live-stage--evidence">
      <header><span className="live-pill">在线追溯摘要</span><small>run_id={latest.run_id}</small></header>
      <div className="live-transport-counts"><strong>事件 {ordered.length}</strong><strong>策略 {policies.size}</strong><strong>最新 e={ordered.at(-1)?.event_id}</strong></div>
      <p>正式指标仅从results接口读取；事件摘要只说明执行过程。</p>
    </div>
  )
}
