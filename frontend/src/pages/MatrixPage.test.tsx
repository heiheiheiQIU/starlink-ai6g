import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MatrixPage } from './MatrixPage'

describe('matrix page', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders KPIs from the real 360-run matrix', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
    render(<MatrixPage />)

    expect(screen.getByText('开发期运行')).toBeInTheDocument()
    expect(screen.getByText('360')).toBeInTheDocument()
    expect(screen.getByText('18')).toBeInTheDocument()
  })

  it('renders the 18-cell heat grid with honest source note', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
    render(<MatrixPage />)

    expect(screen.getByLabelText('18工况规则基线热力网格')).toBeInTheDocument()
    expect(screen.getByText('低载')).toBeInTheDocument()
    expect(screen.getByText('过载')).toBeInTheDocument()
    expect(screen.getByText(/规则基线验证，非 AI 实验结果/)).toBeInTheDocument()
    expect(screen.getByText(/不删负结果/)).toBeInTheDocument()
  })
})
