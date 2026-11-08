import type { PolicyResult, RunResult } from '../types/contracts'

interface RunResultComparisonProps {
  current: RunResult
  previous?: RunResult | null
}

function metric(
  policy: PolicyResult,
  key: keyof Pick<PolicyResult, 'weighted_on_time_rate' | 'critical_task_success_rate' | 'goodput_bps' | 'minimum_soc_true' | 'energy_violation_count' | 'joule_per_success_bit'>,
  format: (value: number) => string,
) {
  const value = policy[key]
  if (typeof value === 'number') return format(value)
  return `— · ${policy.metric_reasons[key] ?? '未提供原因'}`
}

function resultRows(label: string, result: RunResult) {
  return result.by_policy.map((policy) => ({ label, result, policy }))
}

export function RunResultComparison({ current, previous }: RunResultComparisonProps) {
  const comparedRuns: { label: string; result: RunResult }[] = [
    { label: '当前任务', result: current },
    ...(previous ? [{ label: '上一任务', result: previous }] : []),
  ]
  const rows = [
    ...resultRows('当前', current),
    ...(previous ? resultRows('上一', previous) : []),
  ]
  return (
    <section className="console-card run-result-comparison" aria-label="真实任务结果并排比较">
      <header className="run-result-comparison__head">
        <div>
          <h2>真实任务结果并排比较</h2>
          <p>所有指标直接读取results接口；不在前端计算跨任务提升率，也不把不同seed解释为因果增益。</p>
        </div>
        <span className="chip">BACKEND RESULTS ONLY</span>
      </header>
      <div className="run-result-comparison__meta">
        {comparedRuns.map(({ label, result }) => (
          <div key={result.run_id}>
            <span>{label}</span><strong className="mono">{result.run_id}</strong>
            <small>seed={result.seed} · config_hash</small><code>{result.config_hash}</code>
          </div>
        ))}
      </div>
      <div className="run-result-comparison__table-wrap">
        <table className="console-table">
          <thead><tr><th>任务</th><th>策略</th><th>加权按时率</th><th>关键任务成功率</th><th>goodput</th><th>最小SOC真值</th><th>能量违规</th><th>J/成功bit</th></tr></thead>
          <tbody>
            {rows.map(({ label, result, policy }) => (
              <tr key={`${result.run_id}-${policy.policy_id}`}>
                <td>{label}</td><td className="mono">{policy.policy_id}</td>
                <td className="mono">{metric(policy, 'weighted_on_time_rate', (value) => `${(value * 100).toFixed(2)}%`)}</td>
                <td className="mono">{metric(policy, 'critical_task_success_rate', (value) => `${(value * 100).toFixed(2)}%`)}</td>
                <td className="mono">{metric(policy, 'goodput_bps', (value) => `${value.toFixed(2)} bps`)}</td>
                <td className="mono">{metric(policy, 'minimum_soc_true', (value) => value.toFixed(4))}</td>
                <td className="mono">{metric(policy, 'energy_violation_count', (value) => String(value))}</td>
                <td className="mono">{metric(policy, 'joule_per_success_bit', (value) => value.toExponential(3))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
