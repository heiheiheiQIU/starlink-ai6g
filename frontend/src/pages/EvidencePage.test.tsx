import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { RunApi } from '../api/runs'
import { FIXTURE_RUN_RESULT } from '../fixtures/contracts'
import { RUN_ID_STORAGE_KEY } from '../state/useRun'
import { EvidencePage } from './EvidencePage'

function fakeStorage(): Storage {
  const map = new Map<string, string>()
  return {
    get length() { return map.size },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => Array.from(map.keys())[index] ?? null,
    removeItem: (key: string) => { map.delete(key) },
    setItem: (key: string, value: string) => { map.set(key, value) },
  }
}

function spyApi() {
  const api = {
    createRun: vi.fn(),
    getRunStatus: vi.fn(),
    getResults: vi.fn(),
    getEvents: vi.fn(),
    getAllEvents: vi.fn(),
    exportRun: vi.fn(),
    pollUntilComplete: vi.fn(),
  }
  return api as unknown as RunApi & typeof api
}

describe('evidence page', () => {
  it('never shows final metrics for unfinished runs', () => {
    render(<EvidencePage />)

    expect(screen.getByText('demo_fixture_001')).toBeInTheDocument()
    expect(screen.getByText(/未完成不显示最终指标/)).toBeInTheDocument()
    expect(screen.getByText(/保留 partial，不伪成功/)).toBeInTheDocument()
  })

  it('only completed runs expose an evidence entry', async () => {
    const user = userEvent.setup()
    render(<EvidencePage />)

    const entries = screen.getAllByRole('button', { name: /打开证据/ })
    expect(entries).toHaveLength(1)
    await user.click(entries[0])
    const statuses = screen.getAllByRole('status')
    const note = statuses.find((element) => element.textContent?.includes('仅 completed 可导出'))
    expect(note).toBeTruthy()
    expect(note).toHaveTextContent(/仅 completed 可导出/)
  })

  it('keeps pending claims marked as pending', () => {
    render(<EvidencePage />)
    expect(screen.getByText('学习调度优于基线')).toBeInTheDocument()
    expect(screen.getByText('待实验')).toBeInTheDocument()
    expect(screen.getByText(/任何收益数字当前均不可写/)).toBeInTheDocument()
  })

  it('shows a real run results card only after completion', async () => {
    const storage = fakeStorage()
    storage.setItem(RUN_ID_STORAGE_KEY, 'run-9')
    const api = spyApi()
    api.getRunStatus.mockResolvedValue({
      run_id: 'run-9', status: 'completed', progress: 1, active_policies: ['edf', 'learned'], error: null,
    })
    api.getResults.mockResolvedValue(FIXTURE_RUN_RESULT)

    render(<EvidencePage api={api} storage={storage} />)

    await waitFor(() => {
      expect(screen.getByText('真实 run 结果')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('真实运行指标')).toBeInTheDocument()
    expect(screen.getByText(/来源：GET \/runs/)).toBeInTheDocument()
  })
})
