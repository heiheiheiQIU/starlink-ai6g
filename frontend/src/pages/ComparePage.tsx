import { useState } from 'react'

import {
  COMPARE_AXIS,
  COMPARE_SCENARIO_LABELS,
  FIXTURE_METRICS,
  FIXTURE_SERIES,
  type PolicyMetricRow,
} from '../domain/compare'

function seriesPath(values: readonly number[], width: number, height: number): string {
  const max = Math.max(...values, 1)
  return values
    .map((value, index) => {
      const x = 8 + (index / (values.length - 1)) * (width - 16)
      const y = height - 10 - (value / max) * (height - 28)
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function Chart({ values, color }: { values: readonly number[]; color: string }) {
  return (
    <svg
      className="compare-chart"
      viewBox="0 0 560 170"
      role="img"
      aria-label="同时间轴累计完整交付任务数（契约样例）"
    >
      <line x1="8" y1="8" x2="8" y2="160" stroke="rgba(255,255,255,0.08)" />
      <line x1="8" y1="160" x2="552" y2="160" stroke="rgba(255,255,255,0.08)" />
      <path d={seriesPath(values, 560, 170)} fill="none" stroke={color} strokeWidth="2.5" />
    </svg>
  )
}

function MetricTable({ rows }: { rows: readonly PolicyMetricRow[] }) {
  return (
    <table className="console-table">
      <thead>
        <tr>
          <th>指标</th>
          <th>EDF 基线</th>
          <th>learned</th>
          <th>差异</th>
          <th>口径说明</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.metric}>
            <td>{row.metric}</td>
            <td className="mono">{row.edf}</td>
            <td className="mono">{row.learned}</td>
            <td>
              <span className={`diff-badge diff-badge--${row.diffKind}`}>{row.diff}</span>
            </td>
            <td className="table-note">{row.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function ComparePage() {
  const [load, setLoad] = useState(1)
  const [energy, setEnergy] = useState(1)
  const [link, setLink] = useState(1)
  const [stale, setStale] = useState(false)
  const [created, setCreated] = useState(false)

  function touchConfig() {
    setStale(true)
    setCreated(false)
  }

  function createRun() {
    setStale(false)
    setCreated(true)
  }

  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">FAIR COMPARISON BENCH</p>
        <h1>方案对比</h1>
        <p>同配置、同 seed、同外部轨迹与评价口径下，并排对照两种策略；参数变更立即让旧结果失效。</p>
      </header>

      <div className="compare-config" aria-label="实验配置（契约样例）">
        <label>
          负载
          <select value={load} onChange={(event) => { setLoad(Number(event.target.value)); touchConfig() }}>
            {COMPARE_SCENARIO_LABELS.load.map((label, index) => (
              <option key={label} value={index}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          能量余量
          <select value={energy} onChange={(event) => { setEnergy(Number(event.target.value)); touchConfig() }}>
            {COMPARE_SCENARIO_LABELS.energy.map((label, index) => (
              <option key={label} value={index}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          链路扰动
          <select value={link} onChange={(event) => { setLink(Number(event.target.value)); touchConfig() }}>
            {COMPARE_SCENARIO_LABELS.link.map((label, index) => (
              <option key={label} value={index}>{label}</option>
            ))}
          </select>
        </label>
        <span className="mono chip">seed=42 · 18工况×10轨迹</span>
        <div className="spacer" />
        <button className="primary-button" type="button" onClick={createRun}>
          新建 run 并重算
        </button>
      </div>

      {stale ? (
        <div className="stale-banner" role="alert">
          ⚠ 配置已变更：旧结果（demo_fixture_001）已标记为历史/失效；请新建 run 后再比较。
        </div>
      ) : null}
      {created ? (
        <div className="created-banner" role="status">
          ✅ 新 run 已创建（契约样例 fixture_002）：仅 completed 后展示结果，数字仍为占位。
        </div>
      ) : null}

      <div className="compare-grid">
        <div className="policy-panel">
          <header className="policy-panel__head">
            <strong>EDF 能源约束基线</strong>
            <span className="chip">规则 · 无模型</span>
          </header>
          <Chart values={FIXTURE_SERIES.map((point) => point.edf)} color="#93a7bd" />
          <p className="panel-note">同一外部轨迹与观测；policy_id=edf。</p>
        </div>
        <div className="policy-panel">
          <header className="policy-panel__head">
            <strong>learned 学习调度（本方案）</strong>
            <span className="chip">policy_v001 · 契约样例</span>
          </header>
          <Chart values={FIXTURE_SERIES.map((point) => point.learned)} color="#6d7cff" />
          <p className="panel-note">同一外部轨迹与观测；policy_id=learned。</p>
        </div>
      </div>

      <div className="console-card">
        <h2>指标对比</h2>
        <MetricTable rows={FIXTURE_METRICS} />
        <p className="panel-note">
          轴刻度（秒）：{COMPARE_AXIS.join(' / ')} · 两策略事件按 policy_id 严格隔离 · 全部为契约样例占位，非实验结果。
        </p>
        <div className="negative-note">
          工程化原则：低负载/能量充足工况若两策略无显著差异，必须如实展示并注明"该工况下额外预测无益"，
          不删负结果；相对优化器的配对统计只在预冻结 54 条子集上声称。
        </div>
      </div>
    </section>
  )
}
