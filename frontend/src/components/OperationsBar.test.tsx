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
    expect(screen.getByRole('region', { name: '工程运行状态' })).toHaveTextContent('契约演示')
    expect(screen.getByText('API 未连接')).toBeInTheDocument()
    expect(screen.getByText('证据未冻结')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '切换到真实运行' }))
    expect(onModeChange).toHaveBeenCalledWith('live')
  })
})
