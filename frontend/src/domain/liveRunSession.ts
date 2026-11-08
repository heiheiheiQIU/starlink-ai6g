import type { Event } from '../types/contracts'
import type { RunSource } from '../state/useRun'
import { normalizeReplayEvents } from './eventReplay'
import { createRunSession, type RunPhase, type RunSessionState } from './runSession'

const EVENT_STAGE: Record<Event['event_type'], { stepIndex: number; phase: RunPhase }> = {
  arrived: { stepIndex: 0, phase: 'queued' },
  window_changed: { stepIndex: 1, phase: 'forecasting' },
  snapshot: { stepIndex: 1, phase: 'forecasting' },
  decision: { stepIndex: 3, phase: 'guarding' },
  sent: { stepIndex: 4, phase: 'transmitting' },
  received: { stepIndex: 4, phase: 'transmitting' },
  acked: { stepIndex: 4, phase: 'transmitting' },
  dropped: { stepIndex: 4, phase: 'transmitting' },
  fallback: { stepIndex: 4, phase: 'transmitting' },
}

/**
 * 把后端权威状态/事件投影为六步工作台进度。这里只做展示映射，不重算指标、
 * 不推断未出现的业务事件，也不承担 B 负责的场景配置编译。
 */
export function liveRunSession(source: Extract<RunSource, { kind: 'online' }>): RunSessionState {
  const events = normalizeReplayEvents(source.events ?? [])
  const latest = events.at(-1)
  const stage = latest ? EVENT_STAGE[latest.event_type] : EVENT_STAGE.arrived
  const backendStatus = source.status?.status
  const completed = backendStatus === 'completed'
  const failed = backendStatus === 'failed' || backendStatus === 'cancelled'

  return {
    ...createRunSession(),
    mode: 'live',
    connection: source.offline ? 'offline' : 'online',
    playback: completed ? 'complete' : failed ? 'failed' : 'paused',
    phase: completed ? 'complete' : failed ? 'failed' : stage.phase,
    stepIndex: completed ? 5 : stage.stepIndex,
    runId: source.runId,
    lastSync: latest ? `e=${latest.event_id} · t=${latest.sim_time_s}s` : backendStatus ?? null,
    evidence: completed ? 'frozen' : 'unfrozen',
  }
}
