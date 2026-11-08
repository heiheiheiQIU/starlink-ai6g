import { useEffect, useState } from 'react'

import { CountUp } from '../components/CountUp'
import { EventStreamCard } from '../components/EventStreamCard'
import { RunSourceBadge } from '../components/RunSourceBadge'
import type { RunApi } from '../api/runs'
import { FIXTURE_HASH, FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import { useOptionalSharedRun } from '../state/RunContext'
import { RUN_ID_STORAGE_KEY, useRun, type RunController } from '../state/useRun'
import type { RunResult } from '../types/contracts'

function completedMetrics(result: RunResult): string {
  const learned = result.by_policy.find((policy) => policy.policy_id === 'learned')
  if (learned?.weighted_on_time_rate === null || learned?.weighted_on_time_rate === undefined) {
    return '—（演示数据）'
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
    claim: '版本锁定资产 SHA 与 v3 包一致',
    level: '已复核',
    levelKind: 'a' as const,
    source: '资产结果依据索引 / 公开数据清单',
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
    level: '待正式验证',
    levelKind: 'c' as const,
    source: '正式验证完成前禁止引用百分比',
    boundary: '任何收益数字当前均不可写',
  },
] as const

function EvidenceContent({ run }: { run: RunController }) {
  const [exported, setExported] = useState(false)
  const { state } = run

  const realResults =
    state.kind === 'online' && state.status?.status === 'completed' && state.results !== null
      ? state.results
      : null

  const realEvents =
    state.kind === 'online' && state.events !== null && state.events.length > 0
      ? { runId: state.runId, events: state.events }
      : null

  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">TRACEABLE RESULTS</p>
        <h1>结果追溯</h1>
        <p>每项结果均可定位到任务实例、运行事件与源文件；缺少依据时明确显示缺失。</p>
      </header>

      <div className="console-card">
        <h2>数据源</h2>
        <RunSourceBadge controller={run} />
      </div>

      {realResults ? (
        <div className="console-card">
          <h2>在线任务结果</h2>
          <p className="panel-note" style={{ marginBottom: 10 }}>
            来源：任务结果接口 GET /runs/{'{id}'}/results（run_id={realResults.run_id}）；页面只读展示、不重算指标。
          </p>
          <table className="console-table" aria-label="在线任务指标">
            <thead>
              <tr>
                <th>policy_id</th>
                <th>加权按时交付率</th>
                <th>成功载荷字节</th>
                <th>J / 成功 bit</th>
                <th>能量违规段</th>
              </tr>
            </thead>
            <tbody>
              {realResults.by_policy.map((policy) => (
                <tr key={policy.policy_id}>
                  <td className="mono">{policy.policy_id}</td>
                  <td className="mono">
                    {policy.weighted_on_time_rate === null ? '—（未测）' : <><CountUp value={policy.weighted_on_time_rate * 100} />%</>}
                  </td>
                  <td className="mono">{policy.success_payload_bytes ?? '—'}</td>
                  <td className="mono">
                    {policy.joule_per_success_bit === null ? '—（无成功载荷）' : <CountUp value={policy.joule_per_success_bit} decimals={8} />}
                  </td>
                  <td className="mono">{policy.energy_violation_count ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {realEvents ? <EventStreamCard runId={realEvents.runId} events={realEvents.events} /> : null}

      <div className="console-card">
        <h2>任务实例列表（演示数据 · 状态说明）</h2>
        <p className="panel-note" style={{ marginBottom: 10 }}>
          下表用于说明任务状态与交互（config_hash={FIXTURE_HASH}，占位）；在线任务指标见上方“在线任务结果”。
        </p>
        <table className="console-table">
          <thead>
            <tr>
              <th>run_id</th>
              <th>配置</th>
              <th>策略</th>
              <th>状态</th>
              <th>加权交付率</th>
              <th>依据</th>
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
                      查看依据 ▸
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
            已导出任务结果包（演示流程：正式版调用 GET /runs/{'{id}'}/export，仅 completed 可导出）。
          </p>
        ) : null}
      </div>

      <div className="console-card">
        <h2>结果依据索引</h2>
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
        <h2>事件记录示例</h2>
        <pre className="event-sample">
          {`e=1001 policy=learned t=301.0 decision mode=idle reason=WINDOW_CLOSED
e=1002 policy=edf     t=301.0 decision mode=idle reason=WINDOW_CLOSED
e=1003 policy=learned t=302.0 snapshot energy_est=6.2Wh lower=5.1Wh
e=1004 policy=edf     t=302.0 snapshot energy_est=6.2Wh lower=5.1Wh`}
        </pre>
        <p className="panel-note">
          演示说明：event_id 跨策略递增、policy_id 隔离；页面不重算科学指标，只展示后端结果。
        </p>
      </div>
    </section>
  )
}

function EvidenceWithSharedRun() {
  const sharedRun = useOptionalSharedRun()
  const ownedRun = useRun()
  return <EvidenceContent run={sharedRun ?? ownedRun} />
}

function EvidenceWithOwnedRun({ api, storage }: { api?: RunApi; storage?: Storage }) {
  const run = useRun({ api, storage })
  const { resume } = run

  useEffect(() => {
    const source = storage ?? window.localStorage
    const stored = source.getItem(RUN_ID_STORAGE_KEY)
    if (stored) {
      void resume(stored)
    }
  }, [storage, resume])

  return <EvidenceContent run={run} />
}

export function EvidencePage({ api, storage }: { api?: RunApi; storage?: Storage } = {}) {
  return api || storage
    ? <EvidenceWithOwnedRun api={api} storage={storage} />
    : <EvidenceWithSharedRun />
}
