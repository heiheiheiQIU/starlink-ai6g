import type { PageSourceInfo } from '../domain/dataSource'

export function FixtureBanner({ source }: { source: PageSourceInfo }) {
  return (
    <aside className="fixture-banner" aria-label="数据状态说明">
      <span className="fixture-banner__badge">{source.badge}</span>
      <span>{source.note}</span>
    </aside>
  )
}
