import { describe, expect, it } from 'vitest'

import { getPageLabel, NAV_GROUPS } from './navigation'

describe('navigation contract', () => {
  it('keeps the seven approved entries in their fixed group order', () => {
    expect(NAV_GROUPS).toEqual([
      {
        label: '主流程',
        items: [
          { id: 'flow', label: '任务决策' },
          { id: 'overview', label: '运行总览' },
          { id: 'assistant', label: '智能研判' },
        ],
      },
      {
        label: '工作台',
        items: [
          { id: 'compare', label: '策略评估' },
          { id: 'matrix', label: '场景验证' },
          { id: 'evidence', label: '结果追溯' },
          { id: 'assets', label: '模型与资产' },
        ],
      },
    ])
  })

  it('resolves the approved labels from page ids', () => {
    expect(getPageLabel('flow')).toBe('任务决策')
    expect(getPageLabel('assistant')).toBe('智能研判')
    expect(getPageLabel('matrix')).toBe('场景验证')
  })
})
