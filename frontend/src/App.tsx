import { useEffect, useRef, useState } from 'react'

import { AppSidebar } from './components/AppSidebar'
import { FixtureBanner } from './components/FixtureBanner'
import { FloatingAssistant } from './components/FloatingAssistant'
import { PAGE_SOURCES } from './domain/dataSource'
import type { PageSourceInfo } from './domain/dataSource'
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
  const onlineSource: PageSourceInfo | null = controller.state.kind === 'online'
    ? {
        kind: 'development_run',
        badge: '在线任务',
        note: `任务 ${controller.state.runId}：状态与事件来自任务服务，完成后才展示最终指标。`,
      }
    : null
  const statusLabel = sharedStatus === 'queued'
    ? '排队中'
    : sharedStatus === 'running'
      ? '运行中'
      : sharedStatus === 'completed'
        ? '已完成'
        : sharedStatus === 'failed'
          ? '运行失败'
          : '状态同步中'
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
            <span className="snapshot-chip">
              {controller.state.kind === 'online'
                ? `${statusLabel} · ${controller.state.runId}`
                : '标准场景 · 固定观测快照'}
            </span>
            <button
              className="assistant-trigger"
              type="button"
              onClick={() => setCurrentPage('assistant')}
            >
              <span aria-hidden="true">✦</span> 智能研判
            </button>
          </div>
        </header>

        <FixtureBanner source={onlineSource ?? PAGE_SOURCES[currentPage]} />

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
