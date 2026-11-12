import publishedSummary from '../../public/data/formal_v2_technical_summary.json'
import { render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FormalResultsPanel, FormalResultsSource } from './FormalResultsPanel'

function signedSummary() {
  return structuredClone(publishedSummary)
}

describe('formal results panel', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the separately published release version and object fingerprint', () => {
    render(<FormalResultsPanel analysis={{ ...signedSummary(), publication: {
      version: 'formal-v2-release-20261112-v1', object_sha256: 'c26a97658b0bf366d241f23ee79c7e9dc8e304661f851cc15f3eb29ef52cfb29',
    } }} />)
    expect(screen.getByText('formal-v2-release-20261112-v1')).toBeInTheDocument()
    expect(screen.getByText('c26a97658b0b…fb29')).toBeInTheDocument()
  })

  it('shows only a pending publication state when no technical summary is connected', () => {
    render(<FormalResultsPanel />)
    const panel = screen.getByRole('region', { name: '正式实验结果' })
    expect(within(panel).getByText('未完成')).toBeInTheDocument()
    expect(within(panel).getByText(/尚未接入技术结果摘要/)).toBeInTheDocument()
    expect(within(panel).queryByText(/58\.3%/)).not.toBeInTheDocument()
  })

  it('keeps unsigned statistical win subordinate to the incomplete formal verdict', () => {
    const summary = signedSummary()
    summary.result_signoff = 'pending'
    for (const comparison of Object.values(summary.comparisons)) comparison.formal_verdict = '未完成'
    summary.comparisons['learned-edf'].statistical_verdict = '胜'
    summary.comparisons['learned-edf'].formal_verdict = '未完成'
    summary.comparisons['learned-edf'].overall = { mean_delta: 0.02, ci95: [0.01, 0.03], aggregation: 'equal_cell_weight' }
    render(<FormalResultsPanel analysis={summary} />)
    const card = screen.getByTestId('formal-learned-edf')
    expect(within(card).getByText('未完成')).toBeInTheDocument()
    expect(within(card).getByText(/统计结论：胜/)).toBeInTheDocument()
    expect(within(card).getByText(/发布复核中/)).toBeInTheDocument()
    expect(within(card).queryByText(/正式胜/)).not.toBeInTheDocument()
  })

  it('renders the signed wording, all 18 cells, and provenance', () => {
    render(<FormalResultsPanel analysis={signedSummary()} />)
    expect(screen.getAllByText('负').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByTestId('formal-cell-table-learned-edf').querySelectorAll('tbody tr')).toHaveLength(18)
    expect(screen.getByText('3ad4bfeaf539…4d30')).toBeInTheDocument()
    expect(screen.getByText(/不等同于统计等效/)).toBeInTheDocument()
  })

  it('fails closed when the evidence object is malformed', () => {
    render(<FormalResultsPanel analysis={{ schema_version: 'formal-analysis-summary-v1' }} />)
    expect(screen.getByText('数据校验未通过')).toBeInTheDocument()
    expect(screen.getByText(/未通过结构与一致性校验/)).toBeInTheDocument()
  })

  it('loads a configured generated artifact without embedding numbers in source code', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => signedSummary() }))
    render(<FormalResultsSource url="/evidence/formal_v2/summary.json" />)
    await waitFor(() => expect(screen.getByText('结果已发布')).toBeInTheDocument())
    expect(fetch).toHaveBeenCalledWith('/evidence/formal_v2/summary.json', expect.objectContaining({ cache: 'no-store' }))
  })

  it('renders completed technical evidence while keeping an unsigned formal verdict pending', () => {
    const summary = signedSummary()
    summary.result_signoff = 'pending'
    for (const comparison of Object.values(summary.comparisons)) comparison.formal_verdict = '未完成'
    summary.completed_policy_runs = 540
    summary.failed_policy_runs = 0
    summary.missing_policy_runs = 0
    summary.comparisons['learned-edf'].statistical_verdict = '负'
    summary.comparisons['learned-edf'].formal_verdict = '未完成'
    summary.comparisons['learned-edf'].overall = { mean_delta: -0.4654, ci95: [-0.4942, -0.4359], aggregation: 'equal_cell_weight' }
    render(<FormalResultsPanel analysis={summary} />)
    expect(screen.getByText('技术结果完成 · 发布复核中')).toBeInTheDocument()
    expect(screen.getByText('540/540')).toBeInTheDocument()
    expect(screen.getAllByText(/统计结论：负 · 发布复核中/)).toHaveLength(2)
  })

  it('rejects a configured source that cannot be read', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    render(<FormalResultsSource url="/evidence/formal_v2/summary.json" />)
    await waitFor(() => expect(screen.getByText('结果摘要读取失败')).toBeInTheDocument())
    expect(screen.queryByText('结果已发布')).not.toBeInTheDocument()
  })
})
