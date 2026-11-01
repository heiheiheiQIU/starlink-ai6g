/**
 * 真实事件流的展示派生（只读，不重算科学指标）：
 * - eventKind：把合同事件类型归并为瀑布图分类；
 * - eventWaterfall：按 policy_id 分泳道、按 sim_time 归一化位置；
 * - energySeries：从 snapshot 事件的公开能量估计/下界提取曲线点。
 */

import type { Event, SnapshotData } from '../types/contracts'

export type WaterfallKind = 'sent' | 'received' | 'acked' | 'dropped' | 'decision' | 'snapshot' | 'other'

export const WATERFALL_COLORS: Record<WaterfallKind, string> = {
  sent: '#3bd4ed',
  received: '#63d9eb',
  acked: '#63dda9',
  dropped: '#f49898',
  decision: '#8f9bff',
  snapshot: '#8ea7bb',
  other: '#4b6b84',
}

export const WATERFALL_LABELS: Record<WaterfallKind, string> = {
  sent: '发送',
  received: '接收',
  acked: '确认ACK',
  dropped: '丢失',
  decision: '决策',
  snapshot: '快照',
  other: '其他',
}

export function eventKind(event: Event): WaterfallKind {
  switch (event.event_type) {
    case 'sent':
    case 'fallback':
      return 'sent'
    case 'received':
      return 'received'
    case 'acked':
      return 'acked'
    case 'dropped':
      return 'dropped'
    case 'decision':
      return 'decision'
    case 'snapshot':
      return 'snapshot'
    case 'arrived':
    case 'window_changed':
    default:
      return 'other'
  }
}

export interface WaterfallLane {
  policyId: string
  blocks: { eventId: number; kind: WaterfallKind; time: number; title: string }[]
}

export interface WaterfallView {
  lanes: WaterfallLane[]
  minTime: number
  maxTime: number
  kinds: WaterfallKind[]
}

export function eventWaterfall(events: Event[]): WaterfallView {
  const byPolicy = new Map<string, Event[]>()
  const kinds = new Set<WaterfallKind>()
  for (const event of events) {
    const lane = byPolicy.get(event.policy_id) ?? []
    lane.push(event)
    byPolicy.set(event.policy_id, lane)
    kinds.add(eventKind(event))
  }
  const times = events.map((event) => event.sim_time_s)
  const minTime = times.length > 0 ? Math.min(...times) : 0
  const maxTime = times.length > 0 ? Math.max(...times) : 1
  return {
    lanes: Array.from(byPolicy.entries()).map(([policyId, laneEvents]) => ({
      policyId,
      blocks: laneEvents
        .slice()
        .sort((left, right) => left.sim_time_s - right.sim_time_s)
        .map((event) => {
          const kind = eventKind(event)
          return {
            eventId: event.event_id,
            kind,
            time: event.sim_time_s,
            title: `e=${event.event_id} ${kind} t=${event.sim_time_s}s ${event.reason_code ?? ''}`,
          }
        }),
    })),
    minTime,
    maxTime,
    kinds: Array.from(kinds),
  }
}

export interface EnergyPoint {
  time: number
  est: number
  lower: number
}

export function energySeries(events: Event[]): EnergyPoint[] {
  return events
    .filter((event) => event.event_type === 'snapshot' && event.data !== null)
    .map((event) => {
      const data = event.data as SnapshotData
      return {
        time: event.sim_time_s,
        est: Number(data.energy_est_Wh),
        lower: Number(data.energy_lower_Wh),
      }
    })
    .filter((point) => Number.isFinite(point.est) && Number.isFinite(point.lower))
    .sort((left, right) => left.time - right.time)
}
