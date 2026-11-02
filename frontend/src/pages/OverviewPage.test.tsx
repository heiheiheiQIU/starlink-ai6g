import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { OverviewPage } from './OverviewPage'

describe('overview page', () => {
  it('renders the six-node chain and product runtime status without internal project management', () => {
    const { container } = render(<OverviewPage onNavigate={() => undefined} />)

    expect(screen.getByText(/系统链路/)).toBeInTheDocument()
    expect(screen.getByText('任务到达')).toBeInTheDocument()
    expect(screen.getByText('评估与证据')).toBeInTheDocument()
    expect(screen.getByText('当前链路态势')).toBeInTheDocument()
    expect(screen.getByText('可用服务')).toBeInTheDocument()
    expect(container).not.toHaveTextContent(/内部提交|A-N\d|B-R\d|I-\d|M-\d|合入 main/)
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
    expect(screen.getByText(/当前展示为契约样例，非实验结果/)).toBeInTheDocument()
  })
})
