import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { FlowWorkspace } from './FlowWorkspace'

describe('six-step operations stage', () => {
  it('navigates the fixed steps and reveals traceable engineer details', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    expect(
      screen.getByRole('heading', { name: '健康估计', level: 2 }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '下一步' }))
    expect(
      screen.getByRole('heading', { name: '窗口预测', level: 2 }),
    ).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: '步骤 5：发送/确认' }),
    )
    expect(
      screen.getByRole('heading', { name: '发送/确认', level: 2 }),
    ).toBeInTheDocument()

    expect(screen.queryByText('events.jsonl')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '展开工程师详情' }))

    expect(screen.getByText('events.jsonl')).toBeInTheDocument()
    expect(screen.getByText(/契约样例/)).toBeInTheDocument()
  })
})
