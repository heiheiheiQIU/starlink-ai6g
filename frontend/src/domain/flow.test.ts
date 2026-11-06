import { describe, expect, it } from 'vitest'

import { clampStep, FLOW_STEPS } from './flow'

describe('six-step decision flow contract', () => {
  it('keeps the approved operational order and evidence artifact', () => {
    expect(FLOW_STEPS.map(({ title }) => title)).toEqual([
      '任务到达',
      '窗口预测',
      'AI评分',
      '安全约束决策',
      '发送/确认',
      '结果与追溯',
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

  it('keeps step copy free of over-claiming language', () => {
    const forbidden = /VoI|信息新鲜度|不确定性|走哪条链路|显著优于|模型解释归因/
    for (const step of FLOW_STEPS) {
      const text = [step.description, step.narration, step.method].join(' ')
      expect(text).not.toMatch(forbidden)
    }
  })
})
