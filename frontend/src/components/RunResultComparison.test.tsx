import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type { RunResult } from '../types/contracts'
import { RunResultComparison } from './RunResultComparison'

function result(runId: string, seed: number, weighted: number | null, reason?: string): RunResult {
  return {
    ...FIXTURE_RUN_RESULT,
    run_id: runId,
    seed,
    config_hash: `${runId}-config`,
    input_hash: `${runId}-input`,
    by_policy: FIXTURE_RUN_RESULT.by_policy.map((policy) => policy.policy_id === 'learned'
      ? { ...policy, weighted_on_time_rate: weighted, metric_reasons: reason ? { weighted_on_time_rate: reason } : {} }
      : { ...policy }),
  }
}

describe('RunResultComparison', () => {
  it('shows current and previous backend results without inventing a gain', () => {
    render(<RunResultComparison
      current={result('run-new', 22, null, 'EMPTY_DENOMINATOR')}
      previous={result('run-old', 11, 0.61)}
    />)

    expect(screen.getByText('run-new')).toBeInTheDocument()
    expect(screen.getByText('run-old')).toBeInTheDocument()
    expect(screen.getByText(/EMPTY_DENOMINATOR/)).toBeInTheDocument()
    expect(screen.getByText('run-new-config')).toBeInTheDocument()
    expect(screen.getByText('run-old-config')).toBeInTheDocument()
    expect(screen.queryByText(/^提升[：:]/)).not.toBeInTheDocument()
    expect(screen.getByText(/不在前端计算跨任务提升率/)).toBeInTheDocument()
  })
})
