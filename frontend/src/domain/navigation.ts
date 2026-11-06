export type PageId =
  | 'flow'
  | 'overview'
  | 'assistant'
  | 'compare'
  | 'matrix'
  | 'evidence'
  | 'assets'

export interface NavigationItem {
  id: PageId
  label: string
}

export interface NavigationGroup {
  label: string
  items: readonly NavigationItem[]
}

export const NAV_GROUPS: readonly NavigationGroup[] = [
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
] as const

export function getPageLabel(pageId: PageId): string {
  for (const group of NAV_GROUPS) {
    const item = group.items.find(({ id }) => id === pageId)
    if (item) {
      return item.label
    }
  }

  throw new Error(`Unknown page id: ${pageId}`)
}
