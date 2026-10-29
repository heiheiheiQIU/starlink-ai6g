import { describe, expect, it } from 'vitest'

import { clampStep, FLOW_STEPS } from './flow'

describe('six-step decision flow contract', () => {
  it('keeps the approved operational order and evidence artifact', () => {
    expect(FLOW_STEPS.map(({ title }) => title)).toEqual([
      '任务到达',
      '窗口预测',
      'AI评分',
      '约束解码',
      '发送/确认',
      '评估与证据',
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
