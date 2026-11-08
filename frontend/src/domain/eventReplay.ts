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
  const bySimulationTime = new Map<number, Event[]>()
  for (const event of normalizeReplayEvents(events)) {
    const frameEvents = bySimulationTime.get(event.sim_time_s) ?? []
    frameEvents.push(event)
    bySimulationTime.set(event.sim_time_s, frameEvents)
  }
  return [...bySimulationTime.entries()]
    .sort(([left], [right]) => left - right)
    .map(([simTimeS, frameEvents]) => ({ simTimeS, events: frameEvents }))
}
