import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DecisionData, Event } from '../types/contracts'
import { LiveStageExperience } from './LiveStageExperience'

function event(overrides: Partial<Event>): Event {
  return {
    event_id: 1,
    run_id: 'run-live',
    policy_id: 'learned',
    sim_time_s: 120,
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

describe('LiveStageExperience', () => {
  it('renders authoritative candidate scores, action and guard rejection', () => {
    const data: DecisionData = {
      action: { task_id: 'T-101', mode: 'robust', scheduled_bytes: 1024, reason_codes: ['ENERGY_GUARD_REJECTED'], fallback: true },
      candidate_scores: [
        { task_id: 'T-101', mode: 'robust', score: 0.84 },
        { task_id: 'T-101', mode: 'fast', score: 0.91 },
      ],
      constraint_checks: [
        { code: 'WINDOW_VISIBLE', passed: true, details: {} },
        { code: 'ENERGY_GUARD', passed: false, details: { lower_Wh: 0.8 } },
      ],
      latency_ms: 8,
      fallback: true,
      model_version: 'model-v1',
      policy_version: 'policy-v2',
    }

    render(<LiveStageExperience stepId="decode" events={[event({ event_type: 'decision', data })]} />)

    expect(screen.getByText('T-101 × robust · 1024 B')).toBeInTheDocument()
    expect(screen.getByText(/fast 0\.910/)).toBeInTheDocument()
    expect(screen.getByText('ENERGY_GUARD')).toBeInTheDocument()
    expect(screen.getByText('拒绝')).toBeInTheDocument()
    expect(screen.getByText(/后端事件原值/)).toBeInTheDocument()
  })

  it('shows transport outcomes that differ between runs', () => {
    render(<LiveStageExperience stepId="confirm" events={[
      event({ event_id: 2, event_type: 'sent', task_id: 'T-101', block_id: 1, payload_bytes: 1024 }),
      event({ event_id: 3, event_type: 'dropped', task_id: 'T-102', block_id: 1, reason_code: 'LINK_LOSS' }),
      event({ event_id: 4, event_type: 'acked', task_id: 'T-101', block_id: 1 }),
    ]} />)

    expect(screen.getByText('发送 1')).toBeInTheDocument()
    expect(screen.getByText('确认 1')).toBeInTheDocument()
    expect(screen.getByText('丢失 1')).toBeInTheDocument()
    expect(screen.getByText(/LINK_LOSS/)).toBeInTheDocument()
  })
})
