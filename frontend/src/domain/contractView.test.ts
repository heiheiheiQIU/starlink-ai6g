import { describe, expect, it } from 'vitest'

import {
  forecastBatchConflict,
  formatMetricValue,
  metricDisplay,
  teacherCandidateSetIssues,
} from './contractView'
import {
  FIXTURE_CONFLICT_POLICY,
  FIXTURE_NO_DELIVERY_POLICY,
  FIXTURE_OBSERVATION_CONSISTENT,
  FIXTURE_OBSERVATION_MIXED,
  FIXTURE_RUN_RESULT,
  fixtureTeacherResult,
} from '../fixtures/contracts'

describe('metric display semantics (null + reason / measured 0)', () => {
  it('treats a real measured zero as measured, not missing', () => {
    const display = metricDisplay(FIXTURE_RUN_RESULT.by_policy[0], 'energy_violation_count')
    expect(display.kind).toBe('measured')
    expect(formatMetricValue(display)).toBe('0')
  })

  it('shows null metrics as N/A with their reason', () => {
    const display = metricDisplay(FIXTURE_NO_DELIVERY_POLICY, 'joule_per_success_bit')
    expect(display).toEqual({ kind: 'missing', reason: 'NO_DELIVERY' })
    expect(formatMetricValue(display)).toBe('N/A（NO_DELIVERY）')
  })

  it('flags a non-null metric carrying a missing reason as a contract conflict', () => {
    const display = metricDisplay(FIXTURE_CONFLICT_POLICY, 'goodput_bps')
    expect(display.kind).toBe('conflict')
    expect(formatMetricValue(display)).toContain('合同错误')
  })
})

describe('forecast batch semantics', () => {
  it('accepts windows all matching the top-level batch', () => {
    expect(forecastBatchConflict(FIXTURE_OBSERVATION_CONSISTENT)).toBeNull()
  })

  it('flags mixed forecast versions as a contract conflict without choosing one', () => {
    expect(forecastBatchConflict(FIXTURE_OBSERVATION_MIXED)).toMatch(/W-2/)
    expect(forecastBatchConflict(FIXTURE_OBSERVATION_MIXED)).toMatch(/合同错误态/)
  })
})

describe('teacher candidate set display guard', () => {
  it('accepts exactly one feasible idle with unique keys', () => {
    const result = fixtureTeacherResult([
      { task_id: null, mode: 'idle', score: 0, feasible: true },
      { task_id: 'T-101', mode: 'robust', score: 0.861, feasible: true },
    ])
    expect(teacherCandidateSetIssues(result)).toEqual([])
  })

  it('reports missing idle', () => {
    const result = fixtureTeacherResult([
      { task_id: 'T-101', mode: 'robust', score: 0.861, feasible: true },
    ])
    expect(teacherCandidateSetIssues(result)).toContain('缺少 idle 候选')
  })

  it('reports multiple or infeasible idle candidates', () => {
    const duplicated = fixtureTeacherResult([
      { task_id: null, mode: 'idle', score: 0, feasible: true },
      { task_id: null, mode: 'idle', score: 0, feasible: true },
    ])
    expect(teacherCandidateSetIssues(duplicated)).toContain('候选键重复')
    expect(teacherCandidateSetIssues(duplicated)).toContain('存在多个 idle 候选')

    const infeasible = fixtureTeacherResult([
      { task_id: null, mode: 'idle', score: 0, feasible: false },
    ])
    expect(teacherCandidateSetIssues(infeasible)).toContain('唯一 idle 候选不可行')
  })

  it('reports an empty candidate set', () => {
    expect(teacherCandidateSetIssues(fixtureTeacherResult([]))).toEqual(['候选集合为空'])
  })
})
