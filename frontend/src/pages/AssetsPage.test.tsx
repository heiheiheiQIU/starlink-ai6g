import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AssetsPage } from './AssetsPage'

describe('assets page', () => {
  it('shows frozen asset hashes and license state', () => {
    render(<AssetsPage />)

    expect(screen.getByText('battery_source_windows.npz')).toBeInTheDocument()
    expect(screen.getByText(/DE8EA216/)).toBeInTheDocument()
    expect(screen.getByText(/公开 NASA 数据/)).toBeInTheDocument()
  })

  it('marks unresolved lineage items explicitly', () => {
    render(<AssetsPage />)

    expect(screen.getAllByText(/谱系未闭合/).length).toBeGreaterThan(0)
    expect(screen.getByText(/输出一致性待核验/)).toBeInTheDocument()
    expect(screen.getByText(/冻结配置映射待核验/)).toBeInTheDocument()
  })

  it('keeps model boundaries honest', () => {
    const { container } = render(<AssetsPage />)
    expect(screen.getByText(/禁止=SOC\/容量\/能量\/在线RUL/)).toBeInTheDocument()
    expect(screen.getByText('电池健康估计服务')).toBeInTheDocument()
    expect(screen.getByText(/演示适配已接入/)).toBeInTheDocument()
    expect(container).not.toHaveTextContent(/A-N\d|B-N\d|accepted_with_notes|内部核心|待队长确认/)
  })
})
