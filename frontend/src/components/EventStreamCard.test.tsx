import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EventStreamCard } from './EventStreamCard'
import type { Event } from '../types/contracts'

function makeEvent(overrides: Partial<Event>): Event {
  return {
    event_id: 1,
    run_id: 'run-1',
    policy_id: 'edf',
    sim_time_s: 0,
    event_type: 'snapshot',
    task_id: null,
    block_id: null,
    payload_bytes: 0,
    overhead_bytes: 0,
    energy_Wh: 0,
    reason_code: null,
    data: null,
    ...overrides,
  }
}

const EVENTS: Event[] = [
  makeEvent({ event_id: 1, event_type: 'sent', sim_time_s: 0, task_id: 'T1' }),
  makeEvent({ event_id: 2, event_type: 'received', sim_time_s: 1, task_id: 'T1' }),
  makeEvent({ event_id: 3, event_type: 'acked', sim_time_s: 2, task_id: 'T1' }),
  makeEvent({
    event_id: 4,
    event_type: 'snapshot',
    sim_time_s: 1,
    data: {
      soc_est: 0.6,
      energy_est_Wh: 12,
      energy_lower_Wh: 11,
      queue_count: 3,
      forecast_energy_band: null,
      policy_version: 'synthetic',
      evaluation_truth: null,
      reason_codes: [],
    },
  }),
  makeEvent({
    event_id: 5,
    event_type: 'snapshot',
    sim_time_s: 3,
    data: {
      soc_est: 0.5,
      energy_est_Wh: 10,
      energy_lower_Wh: 9,
      queue_count: 2,
      forecast_energy_band: null,
      policy_version: 'synthetic',
      evaluation_truth: null,
      reason_codes: [],
    },
  }),
]

describe('EventStreamCard', () => {
  it('renders waterfall lanes with legend categories', () => {
    render(<EventStreamCard runId="run-1" events={EVENTS} />)

    expect(screen.getByLabelText('事件瀑布图')).toBeInTheDocument()
    expect(screen.getByText('edf')).toBeInTheDocument()
    expect(screen.getByText('发送')).toBeInTheDocument()
    expect(screen.getByText('接收')).toBeInTheDocument()
    expect(screen.getByText('快照')).toBeInTheDocument()
  })

  it('renders the energy curve from snapshot events only', () => {
    render(<EventStreamCard runId="run-1" events={EVENTS} />)

    expect(screen.getByRole('img', { name: '能量曲线（真实事件快照）' })).toBeInTheDocument()
    expect(screen.getByText(/实线=公开能量估计/)).toBeInTheDocument()
  })

  it('shows an honest empty note without events', () => {
    render(<EventStreamCard runId="run-1" events={[]} />)

    expect(screen.getByText('该 run 暂无事件。')).toBeInTheDocument()
  })
})
