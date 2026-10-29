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
    expect(screen.getByText(/输出级交叉核对未做（F1）/)).toBeInTheDocument()
    expect(screen.getByText(/冻结JSON映射未核验（F3）/)).toBeInTheDocument()
  })

  it('keeps model boundaries honest', () => {
    render(<AssetsPage />)
    expect(screen.getByText(/禁止=SOC\/容量\/能量\/在线RUL/)).toBeInTheDocument()
    expect(screen.getByText(/accepted_with_notes；正式 HealthEstimate 适配/)).toBeInTheDocument()
  })
})
