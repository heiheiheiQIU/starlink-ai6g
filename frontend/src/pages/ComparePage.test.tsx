import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { ComparePage } from './ComparePage'

describe('compare page', () => {
  it('marks fixture data and invalidates old results on config change', async () => {
    const user = userEvent.setup()
    render(<ComparePage />)

    expect(screen.getAllByText(/契约样例/).length).toBeGreaterThan(0)
    expect(screen.getByText('EDF 能源约束基线')).toBeInTheDocument()
    expect(screen.getByText(/58\.3%/)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('负载'), '2')
    expect(screen.getByRole('alert')).toHaveTextContent(/已标记为历史\/失效/)
    expect(screen.queryByText(/新 run 已创建/)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '新建 run 并重算' }))
    expect(screen.getByRole('status')).toHaveTextContent(/新 run 已创建/)
  })

  it('keeps both policy series on the same axis contract', () => {
    render(<ComparePage />)
    expect(screen.getAllByRole('img', { name: /同时间轴/ })).toHaveLength(2)
    expect(screen.getByText(/policy_id 严格隔离/)).toBeInTheDocument()
  })
})
