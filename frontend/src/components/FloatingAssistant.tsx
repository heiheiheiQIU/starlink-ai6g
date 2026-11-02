import { FormEvent, useState } from 'react'

import { answerFixtureQuestion } from '../domain/assistant'

const QUICK_QUESTIONS = ['这些数字是真的吗？', 'AI 控制了通信的什么？', '当前证据能支持哪些结论？']

interface FloatingAssistantProps {
  onOpenAssistant: () => void
}

export function FloatingAssistant({ onOpenAssistant }: FloatingAssistantProps) {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed) return
    setAnswer(answerFixtureQuestion(trimmed).content)
    setQuestion('')
  }

  return (
    <>
      <button
        className="floating-orb"
        type="button"
        aria-label="打开全局 AI 助手"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        ✦
      </button>
      {open ? (
        <aside className="floating-panel" aria-label="全局 AI 助手面板">
          <header>
            <strong>星地智调 · AI 助手</strong>
            <small>只依据证据索引回答 · 契约样例</small>
          </header>
          <div className="floating-panel__body">
            {answer ? <p className="floating-answer">{answer}</p> : null}
            <div className="quick-chips">
              {QUICK_QUESTIONS.map((item) => (
                <button
                  className="chip"
                  key={item}
                  type="button"
                  onClick={() => setAnswer(answerFixtureQuestion(item).content)}
                >
                  {item}
                </button>
              ))}
            </div>
            <button className="link-button" type="button" onClick={onOpenAssistant}>
              打开完整对话页 ▸
            </button>
          </div>
          <form className="floating-panel__input" onSubmit={submit}>
            <input
              aria-label="向全局助手提问"
              placeholder="快速提问…"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <button type="submit">发送</button>
          </form>
        </aside>
      ) : null}
    </>
  )
}
