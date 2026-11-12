import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'

import { parseFormalAnalysis } from './formalResults'

it('rejects malformed publication provenance rather than presenting it as verified', () => {
  const summary = makeSummary({ publication: { version: 'release', object_sha256: 'invalid' } })
  expect(parseFormalAnalysis(summary).ok).toBe(false)
})

function makeSummary(overrides: Record<string, unknown> = {}) {
  const cells = Array.from({ length: 18 }, (_, index) => ({
    cell_id: `cell-${String(index + 1).padStart(2, '0')}`,
    n: 10,
    missing: 0,
    mean_delta: 0.01,
    ci95: [-0.01, 0.03],
  }))
  const comparison = {
    cells,
    paired_count: 180,
    overall: { mean_delta: 0.01, ci95: [-0.01, 0.03], aggregation: 'equal_cell_weight' },
    statistical_verdict: '未检出稳定差异',
    formal_verdict: '未完成',
  }
  return {
    schema_version: 'formal-analysis-summary-v1',
    expected_policy_runs: 540,
    completed_policy_runs: 540,
    missing_policy_runs: 0,
    failed_policy_runs: 0,
    failed_attempts: 0,
    result_signoff: 'pending',
    data_scope: 'formal_v2',
    domain: 'lossy_random_link',
    multiplicity: 'two_primary_comparisons',
    policy_ids: ['edf', 'value', 'learned'],
    comparisons: {
      'learned-edf': comparison,
      'learned-value': comparison,
    },
    provenance: {
      frozen_manifest_sha256: 'a'.repeat(64),
      run_index_sha256: 'b'.repeat(64),
      binding: { code_sha256: 'c'.repeat(64) },
    },
    inference: {
      requests: 20,
      fallback_count: 0,
      fallback_rate: 0,
      cold_load_ms: [12.3],
      decision_latency_count: 20,
      decision_latency_median_ms: 2.1,
      decision_latency_p95_ms: 3.4,
      scope: 'local_CPU_end_to_end_decision_not_pure_model_forward',
    },
    ...overrides,
  }
}

describe('formal analysis parser', () => {
  it('accepts the frozen 18-cell paired-analysis shape', () => {
    const parsed = parseFormalAnalysis(makeSummary())
    expect(parsed.ok).toBe(true)
    if (parsed.ok) {
      expect(parsed.value.comparisons['learned-edf'].cells).toHaveLength(18)
      expect(parsed.value.completed_policy_runs).toBe(540)
    }
  })

  it('rejects a summary that silently drops a cell', () => {
    const summary = makeSummary()
    const comparisons = summary.comparisons as Record<string, Record<string, unknown>>
    const learnedEdf = comparisons['learned-edf']
    learnedEdf.cells = (learnedEdf.cells as unknown[]).slice(0, 17)
    const parsed = parseFormalAnalysis(summary)
    expect(parsed).toEqual(expect.objectContaining({ ok: false }))
  })

  it('rejects unknown verdict wording instead of guessing its meaning', () => {
    const summary = makeSummary()
    const comparisons = summary.comparisons as Record<string, Record<string, unknown>>
    comparisons['learned-value'].statistical_verdict = '等效'
    const parsed = parseFormalAnalysis(summary)
    expect(parsed).toEqual(expect.objectContaining({ ok: false }))
  })

  it('rejects run counts that are internally inconsistent', () => {
    const parsed = parseFormalAnalysis(makeSummary({ completed_policy_runs: 539, missing_policy_runs: 0 }))
    expect(parsed).toEqual(expect.objectContaining({ ok: false }))
  })

  it('rejects a published verdict before result signoff', () => {
    const summary = makeSummary()
    const comparisons = summary.comparisons as Record<string, Record<string, unknown>>
    comparisons['learned-edf'].formal_verdict = '胜'
    const parsed = parseFormalAnalysis(summary)
    expect(parsed).toEqual(expect.objectContaining({ ok: false }))
  })

  it('keeps the original pending while accepting the separately reviewed published summary', () => {
    const summary = JSON.parse(readFileSync(resolve(process.cwd(), 'public/data/formal_v2_technical_summary.json'), 'utf8'))
    const parsed = parseFormalAnalysis(summary)
    expect(parsed.ok).toBe(true)
    if (parsed.ok) {
      expect(parsed.value.completed_policy_runs).toBe(540)
      expect(parsed.value.result_signoff).toBe('accepted')
      expect(parsed.value.comparisons['learned-edf'].statistical_verdict).toBe('负')
      expect(parsed.value.comparisons['learned-edf'].formal_verdict).toBe('负')
    }
    const original = JSON.parse(readFileSync(resolve(process.cwd(), '../docs/evidence/B/delegated_execution_2026-11-10/analysis/summary.json'), 'utf8'))
    expect(original.result_signoff).toBe('pending')
    expect(original.comparisons['learned-edf'].formal_verdict).toBe('未完成')
    const releaseRaw = readFileSync(resolve(process.cwd(), 'public/data/formal_v2_release.json'))
    expect(createHash('sha256').update(releaseRaw).digest('hex')).toBe(summary.publication.object_sha256)
    const { publication: _publication, ...derived } = summary
    expect(derived).toEqual(JSON.parse(releaseRaw.toString('utf8')).analysis)
  })

  it.each(['missing', 'hash', 'version', 'positive'])('rejects publication binding mutation %s', (mutation) => {
    const summary = JSON.parse(readFileSync(resolve(process.cwd(), 'public/data/formal_v2_technical_summary.json'), 'utf8'))
    if (mutation === 'missing') delete summary.publication
    if (mutation === 'hash') summary.publication.object_sha256 = '0'.repeat(64)
    if (mutation === 'version') summary.publication.version = 'unapproved-version'
    if (mutation === 'positive') {
      for (const c of Object.values(summary.comparisons) as Record<string, unknown>[]) {
        c.overall = { mean_delta: .5, ci95: [.4, .6], aggregation: 'equal_cell_weight' }
        c.formal_verdict = '胜'; c.statistical_verdict = '胜'
      }
    }
    expect(parseFormalAnalysis(summary).ok).toBe(false)
  })
})
