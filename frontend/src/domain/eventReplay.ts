import type { Event } from '../types/contracts'

export interface ReplayFrame {
  simTimeS: number
  events: Event[]
}

export function normalizeReplayEvents(events: readonly Event[]): Event[] {
  const byId = new Map<number, Event>()
  for (const event of events) {
    const existing = byId.get(event.event_id)
    if (existing !== undefined && JSON.stringify(existing) !== JSON.stringify(event)) {
      throw new Error(`conflicting payload for event_id ${event.event_id}`)
    }
    byId.set(event.event_id, event)
  }
  return [...byId.values()].sort((left, right) => left.event_id - right.event_id)
}

export function buildReplayFrames(events: readonly Event[]): ReplayFrame[] {
  const frames: ReplayFrame[] = []
  for (const event of normalizeReplayEvents(events)) {
    const previous = frames.at(-1)
    if (previous?.simTimeS === event.sim_time_s) {
      previous.events.push(event)
    } else {
      frames.push({ simTimeS: event.sim_time_s, events: [event] })
    }
  }
  return frames
}
