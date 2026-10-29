import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { FlowWorkspace } from './FlowWorkspace'

describe('six-step operations stage', () => {
  it('navigates the fixed steps and reveals traceable engineer details', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    expect(
      screen.getByRole('heading', { name: '任务到达', level: 2 }),
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

    expect(screen.queryByLabelText('契约样例预览')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '展开工程师详情' }))

    expect(screen.getAllByText('events.jsonl').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('契约样例预览')).toBeInTheDocument()
    expect(screen.getByText(/契约样例/)).toBeInTheDocument()
  })

  it('keeps the approved live interactions and automatic demo controls', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    expect(screen.getByText('队列任务 03')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '添加异常摘要' }))
    expect(screen.getByText('队列任务 04')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '自动演示' }))
    expect(screen.getByRole('button', { name: '停止演示' })).toBeInTheDocument()
    expect(screen.getByText('AUTO · 3S')).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: '步骤 5：发送/确认' }),
    )
    await user.click(screen.getByRole('button', { name: '注入 ACK 丢失' }))
    expect(screen.getByText(/ACK 已丢失/)).toBeInTheDocument()
  })
})
