import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TeacherAuditCard } from './TeacherAuditCard'

describe('TeacherAuditCard', () => {
  it('renders audit KPIs from the frozen v2 data', () => {
    render(<TeacherAuditCard />)

    expect(screen.getByText('19/20')).toBeInTheDocument()
    expect(screen.getByText('1/20')).toBeInTheDocument()
    expect(screen.getByText('13/20')).toBeInTheDocument()
    expect(screen.getByText('0/20')).toBeInTheDocument()
  })

  it('declares regression-only purpose and reconstruction status', () => {
    render(<TeacherAuditCard />)

    expect(screen.getByText(/仅用于管线回归，不构成学习评分器效果依据/)).toBeInTheDocument()
    expect(screen.getByText(/训练数据升级仍在进行/)).toBeInTheDocument()
    expect(screen.getByLabelText('逐样本标签类别')).toBeInTheDocument()
  })
})
