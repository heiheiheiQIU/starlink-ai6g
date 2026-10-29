export type PageId =
  | 'flow'
  | 'overview'
  | 'assistant'
  | 'compare'
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
