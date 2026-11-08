import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

import type { RunController, RunSource } from './useRun'

export interface RunHistory {
  current: RunSource
  previous: RunSource | null
}

interface RunContextValue {
  controller: RunController
  history: RunHistory
}

const RunContext = createContext<RunContextValue | null>(null)

export function RunProvider({
  controller,
  children,
}: {
  controller: RunController
  children: ReactNode
}) {
  const [previous, setPrevious] = useState<RunSource | null>(null)
  const lastOnline = useRef<Extract<RunSource, { kind: 'online' }> | null>(null)

  useEffect(() => {
    if (controller.state.kind !== 'online') return
    if (lastOnline.current !== null && lastOnline.current.runId !== controller.state.runId) {
      setPrevious(lastOnline.current)
    }
    lastOnline.current = controller.state
  }, [controller.state])

  return (
    <RunContext.Provider value={{ controller, history: { current: controller.state, previous } }}>
      {children}
    </RunContext.Provider>
  )
}

export function useSharedRun(): RunController {
  const controller = useContext(RunContext)
  if (controller === null) {
    throw new Error('useSharedRun must be used inside RunProvider')
  }
  return controller.controller
}

/** 允许可复用页面在独立故事/测试中退回自有控制器。产品入口仍使用 RunProvider。 */
export function useOptionalSharedRun(): RunController | null {
  return useContext(RunContext)?.controller ?? null
}

export function useRunHistory(): RunHistory {
  const value = useContext(RunContext)
  if (value === null) throw new Error('useRunHistory must be used inside RunProvider')
  return value.history
}

export function useOptionalRunHistory(): RunHistory | null {
  return useContext(RunContext)?.history ?? null
}
