import { describe, expect, it } from 'vitest'

import type { Event } from '../types/contracts'
import { buildReplayFrames, normalizeReplayEvents } from './eventReplay'

function event(eventId: number, simTime: number, type: Event['event_type'] = 'snapshot'): Event {
  return {
    event_id: eventId,
    run_id: 'run-1',
    policy_id: 'learned',
    sim_time_s: simTime,
    event_type: type,
    task_id: null,
    block_id: null,
    payload_bytes: 0,
    overhead_bytes: 0,
    energy_Wh: 0,
    reason_code: null,
    data: null,
  }
}

describe('event replay normalization', () => {
  it('sorts by event id and removes exact duplicate pages', () => {
    const events = normalizeReplayEvents([event(3, 2), event(1, 0), event(2, 1), event(2, 1)])
    expect(events.map((item) => item.event_id)).toEqual([1, 2, 3])
  })

  it('rejects conflicting events that reuse an event id', () => {
    expect(() => normalizeReplayEvents([event(2, 1, 'sent'), event(2, 1, 'dropped')])).toThrow(
      /event_id 2/,
    )
  })

  it('groups simultaneous events into deterministic simulation-time frames', () => {
    const frames = buildReplayFrames([event(3, 2), event(1, 0), event(2, 0), event(4, 1)])
    expect(frames.map((frame) => [frame.simTimeS, frame.events.map((item) => item.event_id)])).toEqual([
      [0, [1, 2]],
      [1, [4]],
      [2, [3]],
    ])
  })
})
