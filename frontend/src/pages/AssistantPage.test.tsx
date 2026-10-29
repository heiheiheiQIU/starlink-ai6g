import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AssistantPage } from './AssistantPage'

describe('evidence-grounded assistant page', () => {
  it('refuses unsupported questions and keeps local citations visible', async () => {
    const user = userEvent.setup()
    render(<AssistantPage />)

    expect(screen.getAllByText(/契约样例/).length).toBeGreaterThan(0)
    expect(screen.getByText('docs/evidence_index.md')).toBeInTheDocument()

    await user.type(
      screen.getByRole('textbox', { name: '向证据助手提问' }),
      '相比基线提升了多少？',
    )
    await user.click(screen.getByRole('button', { name: '发送问题' }))

    expect(screen.getByText(/无法给出这个结论/)).toBeInTheDocument()
    expect(screen.getByText(/待真实 run/)).toBeInTheDocument()
  })
})
