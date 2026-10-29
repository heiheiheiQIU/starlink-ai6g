import type { PageId } from '../domain/navigation'
import { NAV_GROUPS } from '../domain/navigation'

const NAV_ICONS: Record<PageId, string> = {
  flow: '⌁',
  overview: '◫',
  assistant: '✦',
  compare: '⇄',
  evidence: '✓',
  assets: '◇',
}

interface AppSidebarProps {
  currentPage: PageId
  onNavigate: (pageId: PageId) => void
}

export function AppSidebar({ currentPage, onNavigate }: AppSidebarProps) {
  return (
    <aside className="app-sidebar">
      <div className="brand-lockup" aria-label="星地智调">
        <span className="brand-lockup__mark" aria-hidden="true">
          X
        </span>
        <span>
          <strong>星地智调</strong>
          <small>AI+6G 遥测决策中枢</small>
        </span>
      </div>

      <nav className="app-navigation" aria-label="产品主导航">
        {NAV_GROUPS.map((group) => (
          <section className="nav-group" key={group.label}>
            <h2>{group.label}</h2>
            {group.items.map((item) => (
              <button
                className="nav-entry"
                data-active={item.id === currentPage}
                key={item.id}
                type="button"
                aria-current={item.id === currentPage ? 'page' : undefined}
                onClick={() => onNavigate(item.id)}
              >
                <span className="nav-entry__icon" aria-hidden="true">
                  {NAV_ICONS[item.id]}
                </span>
                {item.label}
              </button>
            ))}
          </section>
        ))}
      </nav>

      <div className="system-status" aria-label="系统状态">
        <span className="status-dot" aria-hidden="true" />
        <span>
          <strong>契约服务已连接</strong>
          <small>H00 · fixture only</small>
        </span>
      </div>
    </aside>
  )
}
