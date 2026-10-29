import { useState } from 'react'

import { FIXTURE_HASH, FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import type { RunResult } from '../types/contracts'

function completedMetrics(result: RunResult): string {
  const learned = result.by_policy.find((policy) => policy.policy_id === 'learned')
  if (learned?.weighted_on_time_rate === null || learned?.weighted_on_time_rate === undefined) {
    return '—（契约样例）'
  }
  return `${(learned.weighted_on_time_rate * 100).toFixed(1)}%（占位）`
}

const RUNS = [
  {
    id: FIXTURE_RUN_RESULT.run_id,
    scenario: '中载 / 紧张 / 扰动',
    policies: 'edf + learned',
    status: 'completed',
    statusLabel: 'completed',
    metrics: completedMetrics(FIXTURE_RUN_RESULT),
  },
  {
    id: 'fixture_running_002',
    scenario: '低载 / 充足 / 无扰动',
    policies: 'edf + learned',
    status: 'running',
    statusLabel: 'running 37%',
    metrics: '— 未完成不显示最终指标',
  },
  {
    id: 'fixture_failed_003',
    scenario: '过载 / 极低 / 扰动',
    policies: 'edf + learned',
    status: 'failed',
    statusLabel: 'failed',
    metrics: '— 保留 partial，不伪成功',
  },
] as const

const EVIDENCE_ROWS = [
  {
    claim: '冻结资产 SHA 与 v3 包一致',
    level: '已复核',
    levelKind: 'a' as const,
    source: 'docs/evidence/B/R0_2026-10-29',
    boundary: '支持"资产未篡改"；不支持"谱系闭合"',
  },
  {
    claim: '旧模型可真实前向（离线）',
    level: '已复核',
    levelKind: 'a' as const,
    source: 'docs/evidence/A1/health_success.json',
    boundary: '支持"前向可用"；不支持"在线精度/SOC"',
  },
  {
    claim: '学习调度优于基线',
    level: '待实验',
    levelKind: 'c' as const,
    source: '11/04 G4 前禁止引用百分比',
    boundary: '任何收益数字当前均不可写',
  },
] as const

export function EvidencePage() {
  const [exported, setExported] = useState(false)

  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">TRACEABLE EVIDENCE CHAIN</p>
        <h1>证据链</h1>
        <p>每个数字必须能定位到 run_id、结果、事件与源文件；缺证据就显示缺失，不伪造链接。</p>
      </header>

      <div className="console-card">
        <h2>实验列表</h2>
        <p className="panel-note" style={{ marginBottom: 10 }}>
          已完成 run 的指标来自单一事实源 fixtures/contracts.ts（config_hash={FIXTURE_HASH}，占位）；
          正式版由 GET /runs 提供，页面不重算。
        </p>
        <table className="console-table">
          <thead>
            <tr>
              <th>run_id</th>
              <th>配置</th>
              <th>策略</th>
              <th>状态</th>
              <th>加权交付率</th>
              <th>证据</th>
            </tr>
          </thead>
          <tbody>
            {RUNS.map((run) => (
              <tr key={run.id}>
                <td className="mono">{run.id}</td>
                <td>{run.scenario}</td>
                <td>{run.policies}</td>
                <td>
                  <span className={`run-status run-status--${run.status}`}>{run.statusLabel}</span>
                </td>
                <td className="mono">{run.metrics}</td>
                <td>
                  {run.status === 'completed' ? (
                    <button className="link-button" type="button" onClick={() => setExported(true)}>
                      打开证据 ▸
                    </button>
                  ) : (
                    <span className="table-note">{run.status === 'running' ? '409 语义演示' : '错误码演示'}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {exported ? (
          <p className="panel-note" role="status">
            已导出 run 包（契约样例：正式版调用 GET /runs/{'{id}'}/export，仅 completed 可导出）。
          </p>
        ) : null}
      </div>

      <div className="console-card">
        <h2>证据索引</h2>
        <table className="console-table">
          <thead>
            <tr>
              <th>结论</th>
              <th>等级</th>
              <th>run_id / 源文件</th>
              <th>可支持 / 不可支持</th>
            </tr>
          </thead>
          <tbody>
            {EVIDENCE_ROWS.map((row) => (
              <tr key={row.claim}>
                <td>{row.claim}</td>
                <td>
                  <span className={`evidence-level evidence-level--${row.levelKind}`}>{row.level}</span>
                </td>
                <td className="mono">{row.source}</td>
                <td className="table-note">{row.boundary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="console-card">
        <h2>事件日志样例</h2>
        <pre className="event-sample">
          {`e=1001 policy=learned t=301.0 decision mode=idle reason=WINDOW_CLOSED
e=1002 policy=edf     t=301.0 decision mode=idle reason=WINDOW_CLOSED
e=1003 policy=learned t=302.0 snapshot energy_est=6.2Wh lower=5.1Wh
e=1004 policy=edf     t=302.0 snapshot energy_est=6.2Wh lower=5.1Wh`}
        </pre>
        <p className="panel-note">
          契约样例：event_id 跨策略递增、policy_id 隔离；页面不重算科学指标，只消费后端结果。
        </p>
      </div>
    </section>
  )
}
