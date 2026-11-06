/**
 * 页面级数据来源声明（Task 1）：
 * 每页显式声明其展示数据的性质，禁止用一个全局 FIXTURE 横幅覆盖真实数据页面。
 */

import type { PageId } from './navigation'
import { sourceLabel } from './productLanguage'

export type DataSourceKind = 'fixture' | 'mixed' | 'development_run' | 'verified_asset'

export interface PageSourceInfo {
  kind: DataSourceKind
  badge: string
  note: string
}

export const PAGE_SOURCES: Record<PageId, PageSourceInfo> = {
  flow: {
    kind: 'fixture',
    badge: sourceLabel('fixture'),
    note: '标准场景演示：交互、动效与数值用于说明流程和数据结构，不作为实验结论。',
  },
  overview: {
    kind: 'fixture',
    badge: sourceLabel('fixture'),
    note: '标准场景演示：汇总卡、倒计时与进展列表为演示数据。',
  },
  assistant: {
    kind: 'fixture',
    badge: sourceLabel('fixture'),
    note: '回答仅引用已建立索引的项目资料，不生成或推测实验数值。',
  },
  compare: {
    kind: 'mixed',
    badge: sourceLabel('mixed'),
    note: '上方可接入在线任务结果；下方为标准场景对比，二者独立标识。',
  },
  matrix: {
    kind: 'development_run',
    badge: sourceLabel('development_run'),
    note: '360 次开发期规则基线运行，用于验证流程与统计口径，不代表正式 AI 实验结果。',
  },
  evidence: {
    kind: 'mixed',
    badge: sourceLabel('mixed'),
    note: '在线事件和结果按任务实例显示；示例列表用于说明追溯结构。',
  },
  assets: {
    kind: 'verified_asset',
    badge: sourceLabel('verified_asset'),
    note: '资产完整性标识来自 SHA 核验与版本清单；待补说明项单独标记。',
  },
}
