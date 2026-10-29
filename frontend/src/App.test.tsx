import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('v4 application shell', () => {
  it('keeps the fixture warning visible while navigating all approved pages', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(
      screen.getByRole('heading', { name: '流程主舞台', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByText(/契约样例/)).toBeInTheDocument()
    expect(screen.getByText(/非实验结果/)).toBeInTheDocument()

    const assistantEntry = screen.getByRole('button', { name: 'AI 助手' })
    expect(
      screen.getByRole('button', { name: '流程主舞台' }),
    ).toHaveAttribute('aria-current', 'page')

    await user.click(assistantEntry)

    expect(
      screen.getByRole('heading', { name: 'AI 助手', level: 1 }),
    ).toBeInTheDocument()
    expect(assistantEntry).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText(/契约样例/)).toBeInTheDocument()
    expect(screen.getByText(/非实验结果/)).toBeInTheDocument()
  })
})
