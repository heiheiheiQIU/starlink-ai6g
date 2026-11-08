import { describe, expect, it } from 'vitest'

import type { Event } from '../types/contracts'
import { liveRunSession } from './liveRunSession'

function event(eventId: number, eventType: Event['event_type']): Event {
  return {
    event_id: eventId,
    run_id: 'run_live_7',
    policy_id: 'learned',
    sim_time_s: eventId,
    event_type: eventType,
    task_id: null,
    block_id: null,
    payload_bytes: 0,
    overhead_bytes: 0,
    energy_Wh: 0,
    reason_code: null,
    data: null,
  }
}

describe('live run session projection', () => {
  it('projects the latest transport event onto the execution stage', () => {
    const session = liveRunSession({
      kind: 'online',
      runId: 'run_live_7',
      status: { run_id: 'run_live_7', status: 'running', progress: 0.6, active_policies: ['learned'], error: null },
      results: null,
      events: [event(2, 'decision'), event(3, 'sent')],
      offline: false,
      error: null,
    })

    expect(session).toMatchObject({
      mode: 'live',
      connection: 'online',
      runId: 'run_live_7',
      stepIndex: 4,
      phase: 'transmitting',
      evidence: 'unfrozen',
    })
  })

  it('freezes evidence only after the backend reports completion', () => {
    const session = liveRunSession({
      kind: 'online',
      runId: 'run_live_7',
      status: { run_id: 'run_live_7', status: 'completed', progress: 1, active_policies: ['learned'], error: null },
      results: null,
      events: [event(1, 'acked')],
      offline: false,
      error: null,
    })

    expect(session).toMatchObject({ stepIndex: 5, phase: 'complete', playback: 'complete', evidence: 'frozen' })
  })

  it('preserves the run identity and exposes offline or failed states', () => {
    const offline = liveRunSession({
      kind: 'online',
      runId: 'run_live_7',
      status: { run_id: 'run_live_7', status: 'running', progress: null, active_policies: [], error: null },
      results: null,
      events: null,
      offline: true,
      error: 'network unavailable',
    })
    expect(offline).toMatchObject({ connection: 'offline', runId: 'run_live_7' })

    const failed = liveRunSession({
      kind: 'online',
      runId: 'run_live_7',
      status: { run_id: 'run_live_7', status: 'failed', progress: 0.4, active_policies: [], error: null },
      results: null,
      events: [],
      offline: false,
      error: null,
    })
    expect(failed).toMatchObject({ phase: 'failed', playback: 'failed', evidence: 'unfrozen' })
  })
})
