import type { PolicyResult } from '../types/contracts'

interface SandboxResultVisualProps {
  policies: PolicyResult[]
}

type MetricKey = 'weighted_on_time_rate' | 'critical_task_success_rate' | 'success_payload_bytes'

const METRICS: { key: MetricKey; label: string }[] = [
  { key: 'weighted_on_time_rate', label: '加权按时交付率' },
  { key: 'critical_task_success_rate', label: '关键任务成功率' },
  { key: 'success_payload_bytes', label: '成功载荷' },
]

function metricValue(policy: PolicyResult, key: MetricKey): number | null {
  const value = policy[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function metricText(policy: PolicyResult, key: MetricKey): string {
  const value = metricValue(policy, key)
  if (value === null) return `— · ${policy.metric_reasons[key] ?? '未提供原因'}`
  if (key === 'success_payload_bytes') return `${value.toLocaleString('en-US')} B`
  return `${(value * 100).toFixed(1)}%`
}

function metricWidth(policy: PolicyResult, key: MetricKey, payloadMax: number): number {
  const value = metricValue(policy, key)
  if (value === null) return 0
  if (key === 'success_payload_bytes') return payloadMax > 0 ? Math.min(100, value / payloadMax * 100) : 0
  return Math.min(100, Math.max(0, value * 100))
}

function signedPp(value: number): string {
  if (value > 0) return `+${value.toFixed(1)} pp`
  if (value < 0) return `−${Math.abs(value).toFixed(1)} pp`
  return '0.0 pp'
}

export function SandboxResultVisual({ policies }: SandboxResultVisualProps) {
  const payloadMax = Math.max(...policies.map((policy) => policy.success_payload_bytes), 0)
  const learned = policies.find((policy) => policy.policy_id === 'learned')
  const baseline = policies.find((policy) => policy.policy_id !== 'learned')
  const learnedRate = learned ? metricValue(learned, 'weighted_on_time_rate') : null
  const baselineRate = baseline ? metricValue(baseline, 'weighted_on_time_rate') : null
  const delta = learnedRate !== null && baselineRate !== null ? (learnedRate - baselineRate) * 100 : null
  const deltaClass = delta === null || delta === 0 ? 'neutral' : delta > 0 ? 'positive' : 'negative'

  return (
    <section className="sandbox-visual" aria-label="本次运行结果画像">
      <header className="sandbox-visual__head">
        <div><strong>本次运行结果画像</strong><small>所有条形与数字直接读取后端results</small></div>
        {learned && baseline ? (
          <div className={`sandbox-delta sandbox-delta--${deltaClass}`}>
            <span>Learned − {baseline.policy_id.toUpperCase()}</span>
            <strong>{delta === null ? '不可计算' : signedPp(delta)}</strong>
          </div>
        ) : null}
      </header>
      <div className="sandbox-visual__grid">
        {policies.map((policy) => (
          <article className="sandbox-policy-profile" key={policy.policy_id}>
            <h3>{policy.policy_id}</h3>
            {METRICS.map((metric) => (
              <div className="sandbox-metric" key={metric.key}>
                <div><span>{metric.label}</span><strong>{metricText(policy, metric.key)}</strong></div>
                <div className="sandbox-metric__track" aria-hidden="true">
                  <i
                    data-testid={`bar-${policy.policy_id}-${metric.key}`}
                    style={{ width: `${metricWidth(policy, metric.key, payloadMax)}%` }}
                  />
                </div>
              </div>
            ))}
            <footer>
              <span>能量违规</span><strong>{policy.energy_violation_count ?? `— · ${policy.metric_reasons.energy_violation_count ?? '未提供原因'}`}</strong>
              <span>待处理任务</span><strong>{policy.pending_task_count}</strong>
            </footer>
          </article>
        ))}
      </div>
      <p>仅比较同一run_id内、同配置与同seed的策略结果；参数或seed变化会生成新的结果画像，不解释为正式总体增益。</p>
    </section>
  )
}
