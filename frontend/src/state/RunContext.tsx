import { createContext, useContext, type ReactNode } from 'react'

import type { RunController } from './useRun'

const RunContext = createContext<RunController | null>(null)

export function RunProvider({
  controller,
  children,
}: {
  controller: RunController
  children: ReactNode
}) {
  return <RunContext.Provider value={controller}>{children}</RunContext.Provider>
}

export function useSharedRun(): RunController {
  const controller = useContext(RunContext)
  if (controller === null) {
    throw new Error('useSharedRun must be used inside RunProvider')
  }
  return controller
}

/** 允许可复用页面在独立故事/测试中退回自有控制器。产品入口仍使用 RunProvider。 */
export function useOptionalSharedRun(): RunController | null {
  return useContext(RunContext)
}
