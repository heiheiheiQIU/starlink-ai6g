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
        '当前页面数字均为 H00 契约样例，用于验证字段、交互和证据链展示，非真实实验结果。真实指标必须由冻结 run 生成并在证据索引中完成签核后才能引用。',
      citations: [EVIDENCE_INDEX, 'contracts/schemas/'],
    }
  }

  return {
    isFixture: true,
    content:
      '现有契约样例无法给出这个结论，我不会补写未经验证的数字。该问题已标记为“待真实 run”，请在产生 run_id、policy_id 与可复核源文件后再回答。',
    citations: [EVIDENCE_INDEX],
  }
}
