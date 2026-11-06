import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { createRunSession } from '../domain/runSession'
import { OperationsBar } from './OperationsBar'

describe('operations status bar', () => {
  it('states source, connection, run identity and evidence truthfully', async () => {
    const user = userEvent.setup()
    const onModeChange = vi.fn()
    render(
      <OperationsBar
        session={createRunSession()}
        onModeChange={onModeChange}
        onStep={vi.fn()}
        onPlaybackToggle={vi.fn()}
      />,
    )
    expect(screen.getByRole('region', { name: '工程运行状态' })).toHaveTextContent('标准场景演示')
    expect(screen.getByText('任务服务未接入')).toBeInTheDocument()
    expect(screen.getByText('结果待归档')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '切换到在线任务' }))
    expect(onModeChange).toHaveBeenCalledWith('live')
  })
})
