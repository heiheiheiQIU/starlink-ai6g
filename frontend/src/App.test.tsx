import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('v4 application shell', () => {
  it('keeps a readable data-source boundary visible while navigating approved pages', async () => {
    const user = userEvent.setup()
    const { container } = render(<App />)

    expect(container.querySelector('.app-shell')).toHaveClass('app-shell--mission')
    expect(container.querySelector('.app-shell')).toHaveClass('app-shell--glass')

    expect(
      screen.getByRole('heading', { name: '任务决策', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByText('演示数据')).toBeInTheDocument()
    expect(screen.getByText(/不作为实验结论/)).toBeInTheDocument()
    expect(screen.getByText('工程控制台')).toBeInTheDocument()
    expect(screen.getByText('数据源、连接与结果来源逐页可追溯')).toBeInTheDocument()
    expect(container).not.toHaveTextContent(/H00|fixture only|运行服务已连接/)

    const assistantEntry = screen.getAllByRole('button', { name: '智能研判' })[0]
    expect(
      screen.getByRole('button', { name: '任务决策' }),
    ).toHaveAttribute('aria-current', 'page')

    await user.click(assistantEntry)

    expect(
      screen.getByRole('heading', { name: '智能研判', level: 1 }),
    ).toBeInTheDocument()
    expect(assistantEntry).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('演示数据')).toBeInTheDocument()
    expect(screen.getByText(/回答仅引用已建立索引的项目资料/)).toBeInTheDocument()
  })
})
