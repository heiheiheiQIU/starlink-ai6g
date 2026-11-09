import { useMemo, useState } from 'react'

import {
  DEFAULT_SANDBOX_AXES,
  makeSandboxRunRequest,
  validateSandboxInput,
  type SandboxAxes,
  type SandboxPolicyPair,
} from '../domain/sandbox'
import type { RunController } from '../state/useRun'

interface SandboxControlPanelProps { controller: RunController }

const OPTIONS = {
  task_count: [[2, '2（轻载）'], [6, '6（中载）'], [10, '10（高载）']] as const,
  deadline_s: [[8, '8 s（紧急）'], [12, '12 s'], [18, '18 s'], [24, '24 s（宽松）']] as const,
  weights: [['equal', '均衡'], ['tiered', '分级'], ['urgent', '首任务优先']] as const,
  initial_energy_Wh: [[0.8, '0.8 Wh'], [1.2, '1.2 Wh'], [10, '10 Wh']] as const,
  health: [['healthy', '健康'], ['degraded', '退化'], ['critical', '临界']] as const,
  disturbance: [['none', '无扰动'], ['mild', '轻度丢包'], ['strong', '强扰动']] as const,
  rate: [['robust', '稳健速率'], ['fast', '高速率']] as const,
}

function statusText(status: string | undefined) {
  return status === 'completed' ? '已完成' : status === 'running' ? '运行中' : status === 'queued' ? '排队中' : status === 'failed' ? '失败' : '等待任务'
}

export function SandboxControlPanel({ controller }: SandboxControlPanelProps) {
  const [axes, setAxes] = useState<SandboxAxes>(DEFAULT_SANDBOX_AXES)
  const [pair, setPair] = useState<SandboxPolicyPair>('edf/learned')
  const [seedText, setSeedText] = useState('600001')
  const [lastKey, setLastKey] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const seed = Number(seedText)
  const errors = validateSandboxInput(axes, seed)
  const selectionKey = JSON.stringify({ axes, pair, seedText })
  const stale = lastKey !== null && lastKey !== selectionKey && controller.state.kind === 'online'
  const description = useMemo(() => `${axes.task_count}项任务 · ${axes.deadline_s}s期限 · ${OPTIONS.health.find(([id]) => id === axes.health)?.[1]} · ${OPTIONS.disturbance.find(([id]) => id === axes.disturbance)?.[1]}`, [axes])

  function update<K extends keyof SandboxAxes>(key: K, value: SandboxAxes[K]) {
    setAxes((current) => ({ ...current, [key]: value }))
  }

  async function run() {
    if (errors.length > 0) return
    setBusy(true)
    try {
      await controller.create(makeSandboxRunRequest(axes, pair, seed))
      setLastKey(selectionKey)
    } finally { setBusy(false) }
  }

  return (
    <div className="console-card sandbox-panel">
      <div className="sandbox-panel__heading">
        <div><p className="eyebrow">LIVE SIMULATION SANDBOX</p><h2>交互仿真沙盒</h2></div>
        <span className="sandbox-badge">合成工况 · 非正式实验</span>
      </div>
      <p className="panel-note">浏览器只提交八项工程轴，完整场景由后端 sandbox-axis-v1 编译并校验；每次运行均产生独立 run_id、真实事件和可导出结果。</p>
      <div className="sandbox-grid">
        <label>任务数量<select aria-label="任务数量" value={axes.task_count} onChange={(e) => update('task_count', Number(e.target.value) as SandboxAxes['task_count'])}>{OPTIONS.task_count.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>任务期限<select aria-label="任务期限" value={axes.deadline_s} onChange={(e) => update('deadline_s', Number(e.target.value) as SandboxAxes['deadline_s'])}>{OPTIONS.deadline_s.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>业务权重<select aria-label="业务权重" value={axes.weights} onChange={(e) => update('weights', e.target.value as SandboxAxes['weights'])}>{OPTIONS.weights.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>初始可用能量<select aria-label="初始可用能量" value={axes.initial_energy_Wh} onChange={(e) => update('initial_energy_Wh', Number(e.target.value) as SandboxAxes['initial_energy_Wh'])}>{OPTIONS.initial_energy_Wh.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>健康状态<select aria-label="健康状态" value={axes.health} onChange={(e) => update('health', e.target.value as SandboxAxes['health'])}>{OPTIONS.health.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>安全储能下限<input aria-label="安全储能下限" type="number" min="0" max="20" step="0.1" value={axes.reserve_Wh} onChange={(e) => update('reserve_Wh', Number(e.target.value))} /></label>
        <label>链路扰动<select aria-label="链路扰动" value={axes.disturbance} onChange={(e) => update('disturbance', e.target.value as SandboxAxes['disturbance'])}>{OPTIONS.disturbance.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>传输速率档<select aria-label="传输速率档" value={axes.rate} onChange={(e) => update('rate', e.target.value as SandboxAxes['rate'])}>{OPTIONS.rate.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>策略对<select aria-label="策略对" value={pair} onChange={(e) => setPair(e.target.value as SandboxPolicyPair)}><option value="edf/learned">EDF vs Learned</option><option value="edf/value">EDF vs Value</option></select></label>
        <label>随机种子<input aria-label="随机种子" className="mono" value={seedText} onChange={(e) => setSeedText(e.target.value)} /></label>
      </div>
      <div className="sandbox-command">
        <div><strong>{description}</strong><small>配置版本 sandbox-axis-v1 · 结果随参数与种子变化</small></div>
        <button className="primary-button" type="button" disabled={busy || errors.length > 0} onClick={() => void run()}>运行沙盒对照</button>
      </div>
      {errors.map((error) => <p className="real-run-error" role="alert" key={error}>{error}</p>)}
      {stale ? <div className="stale-banner" role="alert">参数已变更；下方仍是上一配置的历史结果，请重新运行。</div> : null}
      {controller.state.kind === 'online' ? (
        <div className="sandbox-result">
          <p>任务 <span className="mono">{controller.state.runId}</span> · {statusText(controller.state.status?.status)}{controller.state.offline ? ' · 服务暂不可达' : ''}</p>
          {controller.state.error ? <p className="real-run-error">{controller.state.error}</p> : null}
          {controller.state.results ? <>
            <table className="console-table" aria-label="沙盒策略对照结果"><thead><tr><th>策略</th><th>加权按时交付率</th><th>成功载荷</th><th>能量违规</th></tr></thead><tbody>{controller.state.results.by_policy.map((result) => <tr key={result.policy_id}><td className="mono">{result.policy_id}</td><td>{result.weighted_on_time_rate === null ? '—' : `${(result.weighted_on_time_rate * 100).toFixed(1)}%`}</td><td>{result.success_payload_bytes} B</td><td>{result.energy_violation_count ?? '—'}</td></tr>)}</tbody></table>
            <p className="panel-note">以上为该合成工况的实测结果，不代表增益；Learned 为 0 或落后时原样保留。</p>
            <button className="link-button" type="button" onClick={() => void controller.exportZip()}>导出本次配置、哈希、事件与结果</button>
          </> : null}
        </div>
      ) : <p className="panel-note">连接本机实验服务后可运行；当前未生成任务实例。</p>}
    </div>
  )
}
