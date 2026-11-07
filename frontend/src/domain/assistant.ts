export interface FixtureAnswer {
  isFixture: true
  content: string
  citations: readonly string[]
}

const EVIDENCE_INDEX = 'docs/evidence_index.md'

export function answerFixtureQuestion(question: string): FixtureAnswer {
  const normalized = question.trim()
  const asksAboutAuthenticity = /(数字|数据).*(真|来源)|真实.*(吗|数据)/.test(
    normalized,
  )

  if (asksAboutAuthenticity) {
    return {
      isFixture: true,
      content:
        '当前页面数字为标准场景演示数据，用于说明字段、交互和结果追溯流程，并非真实实验结果。正式指标必须由版本锁定的在线任务生成，并在结果依据索引中完成签核后才能引用。',
      citations: [EVIDENCE_INDEX, 'contracts/schemas/'],
    }
  }

  return {
    isFixture: true,
    content:
      '现有演示数据无法给出这个结论，我不会补写未经验证的数字。该问题已标记为“等待在线任务结果”，请在产生 run_id、policy_id 与可复核源文件后再回答。',
    citations: [EVIDENCE_INDEX],
  }
}
