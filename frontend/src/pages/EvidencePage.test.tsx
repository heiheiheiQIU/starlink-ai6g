import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { EvidencePage } from './EvidencePage'

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
    expect(screen.getByRole('status', { name: /已导出 run 包/ })).toHaveTextContent(/仅 completed 可导出/)
  })

  it('keeps pending claims marked as pending', () => {
    render(<EvidencePage />)
    expect(screen.getByText('学习调度优于基线')).toBeInTheDocument()
    expect(screen.getByText('待实验')).toBeInTheDocument()
    expect(screen.getByText(/任何收益数字当前均不可写/)).toBeInTheDocument()
  })
})
