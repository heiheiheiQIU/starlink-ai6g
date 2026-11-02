import type { FlowStep } from '../domain/flow'

export function StepContextPanel({ step, index }: { step: FlowStep; index: number }) {
  return (
    <aside className="step-context" aria-label="当前步骤上下文">
      <span className="step-context__label">WHY THIS STEP</span>
      <h3>{step.title}</h3>
      <dl>
        <div><dt>是什么</dt><dd>{step.output}</dd></div>
        <div><dt>为什么</dt><dd>{step.question}</dd></div>
        <div><dt>产物</dt><dd>{step.artifact}</dd></div>
      </dl>
      <div className="step-progress"><span style={{ width: `${((index + 1) / 6) * 100}%` }} /></div>
      <strong>{String(index + 1).padStart(2, '0')} / 06</strong>
    </aside>
  )
}
