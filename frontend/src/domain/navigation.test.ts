import { describe, expect, it } from 'vitest'

import { getPageLabel, NAV_GROUPS } from './navigation'

describe('v4 navigation contract', () => {
  it('keeps the six approved entries in their fixed group order', () => {
    expect(NAV_GROUPS).toEqual([
      {
        label: '主流程',
        items: [
          { id: 'flow', label: '流程主舞台' },
          { id: 'overview', label: '任务总览' },
          { id: 'assistant', label: 'AI 助手' },
        ],
      },
      {
        label: '工作台',
        items: [
          { id: 'compare', label: '方案对比' },
          { id: 'evidence', label: '证据链' },
          { id: 'assets', label: '资产管理' },
        ],
      },
    ])
  })

  it('resolves the approved labels from page ids', () => {
    expect(getPageLabel('flow')).toBe('流程主舞台')
    expect(getPageLabel('assistant')).toBe('AI 助手')
  })
})
