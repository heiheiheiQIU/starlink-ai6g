import { useEffect, useRef, useState } from 'react'

import { AppSidebar } from './components/AppSidebar'
import { FixtureBanner } from './components/FixtureBanner'
import { FloatingAssistant } from './components/FloatingAssistant'
import { PAGE_SOURCES } from './domain/dataSource'
import type { PageId } from './domain/navigation'
import { getPageLabel } from './domain/navigation'
import { AssistantPage } from './pages/AssistantPage'
import { AssetsPage } from './pages/AssetsPage'
import { ComparePage } from './pages/ComparePage'
import { EvidencePage } from './pages/EvidencePage'
import { FlowWorkspace } from './pages/FlowWorkspace'
import { MatrixPage } from './pages/MatrixPage'
import { OverviewPage } from './pages/OverviewPage'
import { RunProvider } from './state/RunContext'
import { RUN_ID_STORAGE_KEY, useRun, type RunController } from './state/useRun'

interface AppProps {
  runController?: RunController
  storage?: Storage
}

export default function App({ runController, storage }: AppProps = {}) {
  const [currentPage, setCurrentPage] = useState<PageId>('flow')
  const ownedController = useRun({ storage })
  const controller = runController ?? ownedController
  const restoredRun = useRef(false)

  useEffect(() => {
    if (restoredRun.current) return
    restoredRun.current = true
    const source = storage ?? window.localStorage
    const storedRunId = source.getItem(RUN_ID_STORAGE_KEY)
    if (storedRunId) void controller.resume(storedRunId)
  }, [controller, storage])

  const sharedStatus = controller.state.kind === 'online' ? controller.state.status?.status : null
  useEffect(() => {
    const active = sharedStatus === 'queued' || sharedStatus === 'running'
    if (!active || controller.polling) return
    const timer = window.setInterval(() => void controller.refresh(), 2000)
    return () => window.clearInterval(timer)
  }, [controller, controller.polling, sharedStatus])

  return (
    <RunProvider controller={controller}>
      <div className="app-shell app-shell--mission app-shell--glass">
      <AppSidebar currentPage={currentPage} onNavigate={setCurrentPage} />

      <main className="app-main">
        <header className="topbar">
          <div>
            <span className="topbar__context">星地任务 / 智能通信调度</span>
            <strong>{getPageLabel(currentPage)}</strong>
          </div>
          <div className="topbar__actions">
            <span className="snapshot-chip">演示观测 · 2026-10-29T15:00Z</span>
            <button
              className="assistant-trigger"
              type="button"
              onClick={() => setCurrentPage('assistant')}
            >
              <span aria-hidden="true">✦</span> 智能研判
            </button>
          </div>
        </header>

        <FixtureBanner source={PAGE_SOURCES[currentPage]} />

        <div className="page-stage">
          {currentPage === 'flow' ? (
            <FlowWorkspace />
          ) : currentPage === 'overview' ? (
            <OverviewPage onNavigate={setCurrentPage} />
          ) : currentPage === 'assistant' ? (
            <AssistantPage />
          ) : currentPage === 'compare' ? (
            <ComparePage />
          ) : currentPage === 'matrix' ? (
            <MatrixPage />
          ) : currentPage === 'evidence' ? (
            <EvidencePage />
          ) : currentPage === 'assets' ? (
            <AssetsPage />
          ) : null}
        </div>
      </main>

      <FloatingAssistant onOpenAssistant={() => setCurrentPage('assistant')} />
      </div>
    </RunProvider>
  )
}
