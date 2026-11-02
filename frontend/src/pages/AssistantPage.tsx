import { FormEvent, useState } from 'react'

import {
  answerFixtureQuestion,
  type FixtureAnswer,
} from '../domain/assistant'

const INITIAL_ANSWER: FixtureAnswer = {
  isFixture: true,
  content:
    '我只依据系统契约、证据索引和已签核 run 回答。现在接入的是契约样例，因此可以解释字段和流程，但不会把样例指标包装成实验结论。',
  citations: ['docs/evidence_index.md'],
}

const SUGGESTED_QUESTIONS = [
  '这些数字是真的吗？',
  '为什么选择这条链路？',
  '当前证据能支持哪些结论？',
]

export function AssistantPage() {
  const [question, setQuestion] = useState('')
  const [lastQuestion, setLastQuestion] = useState('当前有哪些回答边界？')
  const [answer, setAnswer] = useState<FixtureAnswer>(INITIAL_ANSWER)

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed) return

    setLastQuestion(trimmed)
    setAnswer(answerFixtureQuestion(trimmed))
    setQuestion('')
  }

  function askSuggestedQuestion(value: string) {
    setLastQuestion(value)
    setAnswer(answerFixtureQuestion(value))
  }

  return (
    <section className="assistant-page">
      <header className="assistant-page__intro">
        <div>
          <p className="eyebrow">EVIDENCE-GROUNDED COPILOT</p>
          <h1>AI 助手</h1>
          <p>解释每次调度的依据、边界与证据，不生成尚未产生的实验结论。</p>
        </div>
        <div className="assistant-boundary">
          <span>回答模式</span>
          <strong>契约样例 · 防编造</strong>
          <small>仅允许本地证据引用</small>
        </div>
      </header>

      <div className="assistant-layout">
        <div className="assistant-thread">
          <div className="assistant-message assistant-message--user">
            <span>用户提问</span>
            <p>{lastQuestion}</p>
          </div>
          <article className="assistant-message assistant-message--answer">
            <div className="assistant-message__meta">
              <span className="assistant-avatar" aria-hidden="true">
                ✦
              </span>
              <span>
                <strong>星地证据助手</strong>
                <small>{answer.isFixture ? 'FIXTURE BOUNDARY ACTIVE' : ''}</small>
              </span>
            </div>
            <p>{answer.content}</p>
            <div className="assistant-citations" aria-label="本次回答引用">
              <span>本地引用</span>
              {answer.citations.map((citation) => (
                <code key={citation}>{citation}</code>
              ))}
            </div>
          </article>

          <form className="assistant-composer" onSubmit={submitQuestion}>
            <label htmlFor="assistant-question">向证据助手提问</label>
            <div>
              <input
                id="assistant-question"
                value={question}
                placeholder="例如：这个结论由哪个 run 支持？"
                onChange={(event) => setQuestion(event.target.value)}
              />
              <button type="submit" aria-label="发送问题">
                发送
              </button>
            </div>
          </form>
        </div>

        <aside className="assistant-context" aria-label="助手上下文">
          <div>
            <span className="assistant-context__label">KNOWN CONTEXT</span>
            <h2>本轮可用证据</h2>
            <ul>
              <li>
                <span>接口数据契约</span>
                <strong>已接入</strong>
              </li>
              <li>
                <span>前端 fixture</span>
                <strong>已接入</strong>
              </li>
              <li>
                <span>真实实验 run</span>
                <strong className="pending">待接入</strong>
              </li>
            </ul>
          </div>
          <div>
            <span className="assistant-context__label">QUICK QUESTIONS</span>
            <h2>建议提问</h2>
            <div className="suggested-questions">
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => askSuggestedQuestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  )
}
