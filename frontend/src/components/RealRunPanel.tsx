/**
 * WP3：真实运行面板——从页面选择冻结场景预设、发起 POST /runs、
 * 展示真实状态与结果、下载 ZIP。参数变更后旧结果立即标"历史展示"。
 */

import { useState } from 'react'

import { CountUp } from './CountUp'
import {
  POLICY_PAIRS,
  SCENARIO_PRESETS,
  makeRunRequest,
  type PolicyPair,
} from '../domain/presets'
import type { RunController } from '../state/useRun'

interface RealRunPanelProps {
  controller: RunController
}

function statusLabel(status: string | undefined, progress: number | null | undefined): string {
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败（保留现场，不发布正式结果）'
  if (status === 'running') {
    const percent = progress !== null && progress !== undefined ? ` ${Math.round(progress * 100)}%` : ''
    return `运行中${percent}`
  }
  if (status === 'queued') return '排队中'
  return '未知状态'
}

export function RealRunPanel({ controller }: RealRunPanelProps) {
  const { state, create, exportZip } = controller
  const [presetId, setPresetId] = useState<(typeof SCENARIO_PRESETS)[number]['id']>('normal')
  const [pair, setPair] = useState<PolicyPair>('edf/value')
  const [seedText, setSeedText] = useState('10000')
  const [lastKey, setLastKey] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const preset = SCENARIO_PRESETS.find((item) => item.id === presetId) ?? SCENARIO_PRESETS[0]
  const seed = Number.parseInt(seedText, 10)
  const selectionKey = `${presetId}|${pair}|${seedText}`

  const stale = lastKey !== null && selectionKey !== lastKey && state.kind === 'online' && state.runId !== ''

  async function handleCreate() {
    if (!Number.isFinite(seed) || seed < 0) return
    setBusy(true)
    try {
      await create(makeRunRequest(preset, pair, seed))
      setLastKey(selectionKey)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="console-card">
      <h2>真实运行（POST /runs）</h2>
      <div className="real-run-config">
        <label>
          场景预设
          <select value={presetId} onChange={(event) => setPresetId(event.target.value as typeof presetId)}>
            {SCENARIO_PRESETS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          策略对
          <select value={pair} onChange={(event) => setPair(event.target.value as PolicyPair)}>
            {POLICY_PAIRS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          seed
          <input
            className="mono"
            value={seedText}
            onChange={(event) => setSeedText(event.target.value)}
            aria-label="实验 seed"
          />
        </label>
        <button
          className="primary-button"
          type="button"
          disabled={busy || !Number.isFinite(seed) || seed < 0}
          onClick={() => void handleCreate()}
        >
          发起真实运行
        </button>
      </div>
      <p className="panel-note">{preset.description}</p>

      {stale ? (
        <div className="stale-banner" role="alert">
          ⚠ 配置已变更：下方结果为旧配置（{lastKey?.split('|')[0]}）的历史展示；请重新发起真实运行。
        </div>
      ) : null}

      {state.kind === 'online' ? (
        <div className="real-run-status">
          <p>
            run_id：<span className="mono">{state.runId}</span> · {statusLabel(state.status?.status, state.status?.progress)}
            {state.offline ? ' · 服务连接失败（保留最后状态）' : ''}
          </p>
          {state.error ? <p className="real-run-error">{state.error}</p> : null}
          {state.status?.status === 'completed' && state.results ? (
            <>
              <table className="console-table" aria-label="真实运行指标">
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
                  {state.results.by_policy.map((policy) => (
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
              <button className="link-button" type="button" onClick={() => void exportZip()}>
                下载 ZIP 证据包（{state.runId}.zip）
              </button>
            </>
          ) : null}
        </div>
      ) : (
        <p className="panel-note">未连接实验服务时，下方为契约样例演示；发起真实运行需要本机后端（uvicorn 127.0.0.1:8000）。</p>
      )}
    </div>
  )
}
