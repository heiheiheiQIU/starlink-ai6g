import { describe, expect, it } from 'vitest'

import { PAGE_SOURCES } from './dataSource'
import { getPageLabel } from './navigation'

describe('judge-facing product language', () => {
  it('presents every page source as a readable Chinese operational state', () => {
    expect(Object.values(PAGE_SOURCES).map(({ badge }) => badge)).toEqual([
      '演示数据',
      '演示数据',
      '演示数据',
      '多源数据',
      '开发验证',
      '多源数据',
      '已核验资产',
    ])
    expect(Object.values(PAGE_SOURCES).every(({ badge }) => !/[A-Z-]{3,}/.test(badge))).toBe(true)
  })

  it('uses task-oriented page names instead of internal workbench language', () => {
    expect(getPageLabel('flow')).toBe('任务决策')
    expect(getPageLabel('overview')).toBe('运行总览')
    expect(getPageLabel('assistant')).toBe('智能研判')
    expect(getPageLabel('compare')).toBe('策略评估')
    expect(getPageLabel('matrix')).toBe('场景验证')
    expect(getPageLabel('evidence')).toBe('结果追溯')
    expect(getPageLabel('assets')).toBe('模型与资产')
  })
})
