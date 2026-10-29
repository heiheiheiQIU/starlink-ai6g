import { describe, expect, it } from 'vitest'

import { answerFixtureQuestion } from './assistant'

describe('fixture-safe assistant boundary', () => {
  it('explains that displayed numbers are fixtures with an evidence path', () => {
    const answer = answerFixtureQuestion('这些数字是真的吗？')

    expect(answer.isFixture).toBe(true)
    expect(answer.content).toMatch(/契约样例/)
    expect(answer.content).toMatch(/非真实实验结果/)
    expect(answer.citations).toContain('docs/evidence_index.md')
  })

  it('refuses to invent unsupported answers or percentage gains', () => {
    const answer = answerFixtureQuestion('相比基线提升了多少？')

    expect(answer.isFixture).toBe(true)
    expect(answer.content).toMatch(/无法给出/)
    expect(answer.content).toMatch(/待真实 run/)
    expect(answer.content).not.toMatch(/提升\s*\d+(?:\.\d+)?%/)
  })
})
