/**
 * WP3：真实运行场景预设。
 * 场景配置取自 B 已提交的 configs/scenarios/r3_*.json（提交 971f221），
 * 按 API 要求剥离 actions（自动运行不允许手工脚本），固定 evaluation_end_s。
 */

import ackLossRaw from '../fixtures/presets/r3_ack_loss.json?raw'
import multiblockRaw from '../fixtures/presets/r3_multiblock.json?raw'
import normalRaw from '../fixtures/presets/r3_normal.json?raw'
import type { JsonValue, RunRequest } from '../types/contracts'

export interface ScenarioPreset {
  id: 'normal' | 'multiblock' | 'ack_loss'
  label: string
  description: string
  config: Record<string, unknown>
}

function buildConfig(raw: string): Record<string, unknown> {
  const parsed = JSON.parse(raw.replace(/^\uFEFF/, '')) as Record<string, unknown>
  return {
    ...parsed,
    actions: [],
    evaluation_end_s: typeof parsed.evaluation_end_s === 'number' ? parsed.evaluation_end_s : 24,
  }
}

export const SCENARIO_PRESETS: readonly ScenarioPreset[] = [
  {
    id: 'normal',
    label: '资源充足',
    description: '初始能量 10Wh、无实际误包：规则与 learned 均应正常完成（反例工况）。',
    config: buildConfig(normalRaw),
  },
  {
    id: 'multiblock',
    label: '期限冲突',
    description: '多块任务与紧凑期限：窗口与配额约束成为主要瓶颈。',
    config: buildConfig(multiblockRaw),
  },
  {
    id: 'ack_loss',
    label: '低能量链路扰动',
    description: 'ACK 丢失与重传场景：协议义务与能量账本共同作用。',
    config: buildConfig(ackLossRaw),
  },
]

export type PolicyPair = 'edf/value' | 'edf/learned'

export const POLICY_PAIRS: readonly { id: PolicyPair; label: string }[] = [
  { id: 'edf/value', label: 'EDF 规则 vs value 规则' },
  { id: 'edf/learned', label: 'EDF 规则 vs learned（本方案）' },
]

export function makeRunRequest(preset: ScenarioPreset, pair: PolicyPair, seed: number): RunRequest {
  return {
    schema_version: '1.0',
    config: preset.config as Record<string, JsonValue>,
    policy_ids: pair.split('/'),
    seed,
  }
}
