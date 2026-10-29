import { describe, expect, it } from 'vitest'

import { clampStep, FLOW_STEPS } from './flow'

describe('six-step decision flow contract', () => {
  it('keeps the approved operational order and evidence artifact', () => {
    expect(FLOW_STEPS.map(({ title }) => title)).toEqual([
      '健康估计',
      '窗口预测',
      '信息价值评估',
      '通信资源分配',
      '发送/确认',
      '证据归档',
    ])
    expect(FLOW_STEPS[4]).toMatchObject({
      title: '发送/确认',
      artifact: 'events.jsonl',
    })
  })

  it('clamps navigation to the six valid indices', () => {
    expect(clampStep(-1)).toBe(0)
    expect(clampStep(0)).toBe(0)
    expect(clampStep(5)).toBe(5)
    expect(clampStep(6)).toBe(5)
  })
})
