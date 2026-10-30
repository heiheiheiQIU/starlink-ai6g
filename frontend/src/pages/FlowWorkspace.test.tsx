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

  it('keeps tasks added at arrival visible in later steps', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    await user.click(screen.getByRole('button', { name: '添加异常摘要' }))
    await user.click(screen.getByRole('button', { name: '下一步' }))
    await user.click(screen.getByRole('button', { name: '下一步' }))

    expect(screen.getByRole('button', { name: 'T-104' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'T-104' }))
    await user.click(screen.getByRole('button', { name: '运行 AI 评分' }))
    expect(screen.getByText(/综合评分 0.861/)).toBeInTheDocument()
  })

  it('shows quota computation and link legend at decode and confirm steps', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    await user.click(screen.getByRole('button', { name: '步骤 4：约束解码' }))
    expect(screen.getByText(/本时隙字节配额 = 1024 B/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '步骤 5：发送/确认' }))
    expect(screen.getByText('光束=数据发送')).toBeInTheDocument()
    expect(screen.getByText('ACK=网关确认回传')).toBeInTheDocument()
  })

  it('keeps GW, SAT, uplink data and the reverse ACK on one shared route', async () => {
    const user = userEvent.setup()
    render(<FlowWorkspace />)

    await user.click(screen.getByRole('button', { name: '步骤 5：发送/确认' }))
    await user.click(screen.getByRole('button', { name: '播放回放' }))

    const linkMap = screen.getByRole('img', { name: 'GW 到 SAT 数据链路' })
    const beamPath = linkMap.querySelector('[data-link-beam]')?.getAttribute('d')
    const uplinkPath = linkMap
      .querySelector('[data-packet="uplink"] animateMotion')
      ?.getAttribute('path')
    const ackPath = linkMap
      .querySelector('[data-packet="ack"] animateMotion')
      ?.getAttribute('path')

    expect(beamPath).toBe('M 112 154 L 688 54')
    expect(uplinkPath).toBe(beamPath)
    expect(ackPath).toBe('M 688 54 L 112 154')

    const uplinkPacket = linkMap.querySelector('[data-packet="uplink"]')
    const ackPacket = linkMap.querySelector('[data-packet="ack"]')
    const gatewayNode = linkMap.querySelector('[data-node="gateway"]')
    expect(
      uplinkPacket?.compareDocumentPosition(gatewayNode as Node) ?? 0,
    ).toEqual(Node.DOCUMENT_POSITION_FOLLOWING)
    expect(ackPacket).toHaveAttribute('opacity', '0')
    expect(ackPacket?.querySelector('set')).toHaveAttribute('begin', '0.9s')

    await user.click(screen.getByRole('button', { name: '注入 ACK 丢失' }))
    expect(linkMap.querySelector('[data-packet="ack"]')).not.toBeInTheDocument()
    expect(linkMap.querySelector('[data-packet="uplink"] animateMotion')?.getAttribute('path')).toBe(beamPath)
  })
})
