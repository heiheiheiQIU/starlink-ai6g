import type { DataSourceKind } from './dataSource'

export const PRODUCT_TERMS = {
  demoScenario: '标准场景演示',
  demoData: '演示数据',
  taskInstance: '任务实例',
  safetyDecision: '安全约束决策',
  optimalLabel: '最优决策标注',
  resultTrace: '结果与追溯',
  versionLock: '版本锁定',
  integrityCheck: '完整性校验',
  onlineExecution: '在线任务执行',
} as const

const SOURCE_LABELS: Record<DataSourceKind, string> = {
  fixture: PRODUCT_TERMS.demoData,
  mixed: '多源数据',
  development_run: '开发验证',
  verified_asset: '已核验资产',
}

export function sourceLabel(kind: DataSourceKind): string {
  return SOURCE_LABELS[kind]
}
