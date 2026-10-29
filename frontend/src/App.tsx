import { useState } from 'react'

import { AppSidebar } from './components/AppSidebar'
import { FixtureBanner } from './components/FixtureBanner'
import { FloatingAssistant } from './components/FloatingAssistant'
import { PagePlaceholder } from './components/PagePlaceholder'
import type { PageId } from './domain/navigation'
import { getPageLabel } from './domain/navigation'
import { AssistantPage } from './pages/AssistantPage'
import { AssetsPage } from './pages/AssetsPage'
import { ComparePage } from './pages/ComparePage'
import { EvidencePage } from './pages/EvidencePage'
import { FlowWorkspace } from './pages/FlowWorkspace'

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageId>('flow')

  return (
    <div className="app-shell">
      <AppSidebar currentPage={currentPage} onNavigate={setCurrentPage} />

      <main className="app-main">
        <header className="topbar">
          <div>
            <span className="topbar__context">星地任务 / 决策工作台</span>
            <strong>{getPageLabel(currentPage)}</strong>
          </div>
          <div className="topbar__actions">
            <span className="snapshot-chip">OBS · 2026-10-29T15:00Z</span>
            <button
              className="assistant-trigger"
              type="button"
              onClick={() => setCurrentPage('assistant')}
            >
              <span aria-hidden="true">✦</span> 全局助手
            </button>
          </div>
        </header>

        <FixtureBanner />

        <div className="page-stage">
          {currentPage === 'flow' ? (
            <FlowWorkspace />
          ) : currentPage === 'assistant' ? (
            <AssistantPage />
          ) : currentPage === 'compare' ? (
            <ComparePage />
          ) : currentPage === 'evidence' ? (
            <EvidencePage />
          ) : currentPage === 'assets' ? (
            <AssetsPage />
          ) : (
            <PagePlaceholder pageId={currentPage} />
          )}
        </div>
      </main>

      <FloatingAssistant onOpenAssistant={() => setCurrentPage('assistant')} />
    </div>
  )
}
