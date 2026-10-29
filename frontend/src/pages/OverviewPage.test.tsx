import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { OverviewPage } from './OverviewPage'

describe('overview page', () => {
  it('renders the six-node chain and countdown', () => {
    render(<OverviewPage onNavigate={() => undefined} />)

    expect(screen.getByText(/系统链路/)).toBeInTheDocument()
    expect(screen.getByText('任务到达')).toBeInTheDocument()
    expect(screen.getByText('评估与证据')).toBeInTheDocument()
    expect(screen.getByTestId('countdown')).toHaveTextContent(/天/)
    expect(screen.getByText(/官方截止/)).toBeInTheDocument()
  })

  it('navigates from chain nodes and quick entries', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<OverviewPage onNavigate={onNavigate} />)

    await user.click(screen.getAllByRole('button', { name: /任务到达/ })[0])
    expect(onNavigate).toHaveBeenCalledWith('flow')

    await user.click(screen.getByRole('button', { name: /方案对比/ }))
    expect(onNavigate).toHaveBeenCalledWith('compare')
  })

  it('keeps fixture honesty visible', () => {
    render(<OverviewPage onNavigate={() => undefined} />)
    expect(screen.getByText(/契约样例展示，非实验结果/)).toBeInTheDocument()
  })
})
