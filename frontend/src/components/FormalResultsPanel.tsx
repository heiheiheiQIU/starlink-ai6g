import {
  parseFormalAnalysis,
  shortHash,
  type FormalAnalysis,
  type FormalComparison,
  type FormalComparisonId,
  type FormalVerdict,
} from '../domain/formalResults'

interface FormalResultsPanelProps {
  analysis?: unknown
}

const COMPARISON_LABELS: Record<FormalComparisonId, string> = {
  'learned-edf': 'Learned vs EDF',
  'learned-value': 'Learned vs Value',
}

function verdictClass(verdict: FormalVerdict): string {
  if (verdict === '胜') return 'formal-verdict--win'
  if (verdict === '负') return 'formal-verdict--loss'
  if (verdict === '未检出稳定差异') return 'formal-verdict--neutral'
  return 'formal-verdict--pending'
}

function number(value: number | null, digits = 4): string {
  return value === null ? '—' : value.toFixed(digits)
}

function interval(value: [number, number] | null): string {
  return value === null ? '—' : `[${number(value[0])}, ${number(value[1])}]`
}

function CellTable({ id, comparison }: { id: FormalComparisonId; comparison: FormalComparison }) {
  return (
    <div className="formal-cell-table-wrap">
      <table className="console-table formal-cell-table" data-testid={`formal-cell-table-${id}`}>
        <thead><tr><th>工况格</th><th>有效配对</th><th>缺失</th><th>均值差</th><th>95% CI</th></tr></thead>
        <tbody>
          {comparison.cells.map((cell) => (
            <tr key={cell.cell_id}>
              <td className="mono">{cell.cell_id}</td>
              <td className="mono">{cell.n}/10</td>
              <td className="mono">{cell.missing}</td>
              <td className="mono">{number(cell.mean_delta)}</td>
              <td className="mono">{interval(cell.ci95)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ComparisonCard({ id, comparison, signed }: {
  id: FormalComparisonId
  comparison: FormalComparison
  signed: boolean
}) {
  return (
    <article className="formal-comparison" data-testid={`formal-${id}`}>
      <header className="formal-comparison__head">
        <div><span>主比较</span><h3>{COMPARISON_LABELS[id]}</h3></div>
        <strong className={`formal-verdict ${verdictClass(comparison.formal_verdict)}`}>
          {comparison.formal_verdict}
        </strong>
      </header>
      <div className="formal-comparison__summary">
        <div><span>配对轨迹</span><strong>{comparison.paired_count}/180</strong></div>
        <div><span>总体均值差</span><strong className="mono">{number(comparison.overall.mean_delta)}</strong></div>
        <div><span>总体95% CI</span><strong className="mono">{interval(comparison.overall.ci95)}</strong></div>
      </div>
      <p className="formal-statistical-verdict">
        统计结论：{comparison.statistical_verdict}{signed ? ' · 结果已发布' : ' · 发布复核中'}
      </p>
      <CellTable id={id} comparison={comparison} />
    </article>
  )
}

function PendingPanel() {
  return (
    <section className="console-card formal-results" role="region" aria-label="正式实验结果">
      <header className="formal-results__head">
        <div><p className="eyebrow">FORMAL V2 · PAIRED EVALUATION</p><h2>正式配对实验</h2></div>
        <strong className="formal-verdict formal-verdict--pending">未完成</strong>
      </header>
      <div className="formal-empty">
        <strong>尚未接入技术结果摘要</strong>
        <p>系统仅展示通过结构、计数和来源校验的分析文件；未接入时不使用演示数字替代正式结果。</p>
      </div>
    </section>
  )
}

function LoadingPanel() {
  return (
    <section className="console-card formal-results" role="region" aria-label="正式实验结果">
      <header className="formal-results__head">
        <div><p className="eyebrow">FORMAL V2 · PAIRED EVALUATION</p><h2>正式配对实验</h2></div>
        <strong className="formal-verdict formal-verdict--pending">校验中</strong>
      </header>
      <div className="formal-empty"><strong>正在读取实验摘要</strong><p>完成结构、运行计数、结论和来源指纹校验前不展示结果。</p></div>
    </section>
  )
}

function EvidencePanel({ analysis }: { analysis: FormalAnalysis }) {
  const signed = analysis.result_signoff === 'accepted'
  return (
    <section className="console-card formal-results" role="region" aria-label="正式实验结果">
      <header className="formal-results__head">
        <div>
          <p className="eyebrow">FORMAL V2 · PAIRED EVALUATION</p><h2>正式配对实验</h2>
          <p>{analysis.data_scope} · {analysis.domain} · 18工况×10轨迹×3策略</p>
        </div>
        <span className={`chip ${signed ? 'chip--safe' : ''}`}>{signed ? '结果已发布' : '技术结果完成 · 发布复核中'}</span>
      </header>
      <div className="formal-progress" aria-label="正式运行完成度">
        <div><span>已完成</span><strong>{analysis.completed_policy_runs}/540</strong></div>
        <div><span>异常运行</span><strong>{analysis.failed_policy_runs}</strong></div>
        <div><span>待补运行</span><strong>{analysis.missing_policy_runs}</strong></div>
        <div><span>重试记录</span><strong>{analysis.failed_attempts}</strong></div>
      </div>
      <div className="formal-comparison-grid">
        {(['learned-edf', 'learned-value'] as const).map((id) => (
          <ComparisonCard key={id} id={id} comparison={analysis.comparisons[id]} signed={signed} />
        ))}
      </div>
      <aside className="formal-provenance" aria-label="正式证据来源">
        <div><span>实验版本指纹</span><code>{shortHash(analysis.provenance.frozen_manifest_sha256)}</code></div>
        <div><span>运行记录指纹</span><code>{shortHash(analysis.provenance.run_index_sha256)}</code></div>
        <div><span>推理口径</span><code>{analysis.inference.scope}</code></div>
      </aside>
      <p className="negative-note">
        “未检出稳定差异”表示当前预登记检验未发现稳定方向，不等同于统计等效。负结果与缺失结果均按原始记录展示。
      </p>
    </section>
  )
}

export function FormalResultsPanel({ analysis }: FormalResultsPanelProps) {
  if (analysis === undefined || analysis === null) return <PendingPanel />
  const parsed = parseFormalAnalysis(analysis)
  if (!parsed.ok) {
    return (
      <section className="console-card formal-results formal-results--rejected" role="region" aria-label="正式实验结果">
        <header className="formal-results__head"><h2>正式配对实验</h2><strong>数据校验未通过</strong></header>
        <p>输入文件未通过结构与一致性校验，系统不展示结论。原因：{parsed.error}</p>
      </section>
    )
  }
  return <EvidencePanel analysis={parsed.value} />
}
import { useEffect, useState } from 'react'


interface FormalResultsSourceProps {
  url?: string
}

type SourceState =
  | { kind: 'pending' }
  | { kind: 'loading' }
  | { kind: 'loaded'; analysis: unknown }
  | { kind: 'failed'; message: string }

export function FormalResultsSource({ url }: FormalResultsSourceProps) {
  const [state, setState] = useState<SourceState>({ kind: 'pending' })

  useEffect(() => {
    if (!url) {
      setState({ kind: 'pending' })
      return undefined
    }
    const controller = new AbortController()
    setState({ kind: 'loading' })
    void fetch(url, { cache: 'no-store', signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<unknown>
      })
      .then((analysis) => setState({ kind: 'loaded', analysis }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : '未知读取错误'
        setState({ kind: 'failed', message })
      })
    return () => controller.abort()
  }, [url])

  if (state.kind === 'loaded') return <FormalResultsPanel analysis={state.analysis} />
  if (state.kind === 'failed') {
    return (
      <section className="console-card formal-results formal-results--rejected" role="region" aria-label="正式实验结果">
        <header className="formal-results__head"><h2>正式配对实验</h2><strong>结果摘要读取失败</strong></header>
        <p>已配置技术结果源但未能读取。系统不会回退到演示数据。原因：{state.message}</p>
      </section>
    )
  }
  if (state.kind === 'loading') return <LoadingPanel />
  return <FormalResultsPanel />
}
