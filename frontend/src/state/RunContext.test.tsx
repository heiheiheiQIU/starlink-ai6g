import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { RunProvider, useSharedRun } from './RunContext'
import type { RunController } from './useRun'

function fakeController(runId = 'run_shared_001'): RunController {
  return {
    state: {
      kind: 'online',
      runId,
      status: null,
      results: null,
      events: null,
      offline: false,
      error: null,
    },
    create: vi.fn(),
    resume: vi.fn(),
    refresh: vi.fn(),
    abort: vi.fn(),
    exportZip: vi.fn(),
  }
}

function Reader({ name }: { name: string }) {
  const controller = useSharedRun()
  return <output aria-label={name}>{controller.state.kind === 'online' ? controller.state.runId : controller.state.kind}</output>
}

function Boundary({ children }: { children: ReactNode }) {
  return <>{children}</>
}

describe('RunProvider', () => {
  it('provides one run controller to every page consumer', () => {
    const controller = fakeController()
    render(
      <RunProvider controller={controller}>
        <Reader name="flow-run" />
        <Reader name="compare-run" />
      </RunProvider>,
    )

    expect(screen.getByLabelText('flow-run')).toHaveTextContent('run_shared_001')
    expect(screen.getByLabelText('compare-run')).toHaveTextContent('run_shared_001')
  })

  it('fails loudly when a page is mounted without the shared run root', () => {
    const original = console.error
    console.error = vi.fn()
    expect(() => render(<Boundary><Reader name="orphan" /></Boundary>)).toThrow(/RunProvider/)
    console.error = original
  })
})
