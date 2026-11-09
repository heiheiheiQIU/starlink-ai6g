import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SandboxResultVisual } from './SandboxResultVisual'
import type { PolicyResult } from '../types/contracts'

function policy(id: string, rate: number | null, bytes: number, overrides: Partial<PolicyResult> = {}): PolicyResult {
  return {
    policy_id: id, model_hash: null, sample_count: 2, evaluation_end_s: 32, pending_task_count: 0,
    weighted_on_time_rate: rate, critical_task_success_rate: rate, goodput_bps: 100, minimum_soc_true: 0.5,
    energy_violation_count: 0, energy_violation_duration_s: 0, success_payload_bytes: bytes,
    joule_per_success_bit: 0.1, wait_p50_s: 1, wait_p95_s: 1, decision_p50_ms: 1,
    decision_p95_ms: 1, timeout_rate: 0, parameter_count: null, memory_bytes: null, metric_reasons: {},
    ...overrides,
  }
}

describe('sandbox result visual', () => {
  it('visualizes backend values and preserves a negative learned delta', () => {
    render(<SandboxResultVisual policies={[policy('edf', 0.8, 4096), policy('learned', 0.2, 1024)]} />)
    expect(screen.getByText('本次运行结果画像')).toBeInTheDocument()
    expect(screen.getByText('−60.0 pp')).toBeInTheDocument()
    expect(screen.getByTestId('bar-edf-weighted_on_time_rate')).toHaveStyle({ width: '80%' })
    expect(screen.getByTestId('bar-learned-weighted_on_time_rate')).toHaveStyle({ width: '20%' })
    expect(screen.getByText('4,096 B')).toBeInTheDocument()
    expect(screen.getByText(/同一run_id内/)).toBeInTheDocument()
  })

  it('shows metric reasons instead of converting null to zero', () => {
    render(<SandboxResultVisual policies={[
      policy('edf', null, 0, { metric_reasons: { weighted_on_time_rate: 'NO_DUE_TASK' } }),
      policy('learned', 0, 0),
    ]} />)
    expect(screen.getByText('— · NO_DUE_TASK')).toBeInTheDocument()
    expect(screen.queryByText(/−0\.0 pp/)).not.toBeInTheDocument()
  })
})
