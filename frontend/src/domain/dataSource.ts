/**
 * 页面级数据来源声明（Task 1）：
 * 每页显式声明其展示数据的性质，禁止用一个全局 FIXTURE 横幅覆盖真实数据页面。
 */

import type { PageId } from './navigation'

export type DataSourceKind = 'fixture' | 'mixed' | 'development_run' | 'verified_asset'

export interface PageSourceInfo {
  kind: DataSourceKind
  badge: string
  note: string
}

export const PAGE_SOURCES: Record<PageId, PageSourceInfo> = {
  flow: {
    kind: 'fixture',
    badge: 'FIXTURE',
    note: '本页交互、动效与数字均为契约样例，仅演示流程与数据结构，非实验结果。',
  },
  overview: {
    kind: 'fixture',
    badge: 'FIXTURE',
    note: '汇总卡、倒计时与进展列表为演示数据。',
  },
  assistant: {
    kind: 'fixture',
    badge: 'FIXTURE',
    note: '回答仅来自已索引证据文档，不生成任何实验数字。',
  },
  compare: {
    kind: 'mixed',
    badge: 'MIXED',
    note: '真实运行区展示真实 run 结果；下方契约样例对比区为演示数据，两者标注相互独立。',
  },
  matrix: {
    kind: 'development_run',
    badge: 'DEV-RUN',
    note: 'B R5 规则矩阵的 360 次真实开发期运行；属规则基线验证，非正式 AI 实验。',
  },
  evidence: {
    kind: 'mixed',
    badge: 'MIXED',
    note: '数据源卡片与真实事件流为真实 run；实验列表与证据索引样例为契约演示。',
  },
  assets: {
    kind: 'verified_asset',
    badge: 'VERIFIED',
    note: '资产 SHA 来自实际审计与冻结包核对；黄色项为待补来源说明。',
  },
}
