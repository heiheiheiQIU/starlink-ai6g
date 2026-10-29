import type { FlowStep } from '../domain/flow'

interface FlowStepperProps {
  activeIndex: number
  steps: readonly FlowStep[]
  onSelect: (index: number) => void
}

export function FlowStepper({ activeIndex, steps, onSelect }: FlowStepperProps) {
  return (
    <nav className="flow-stepper" aria-label="六步决策流程">
      <div className="flow-stepper__heading">
        <span>DECISION FLOW</span>
        <strong>端到端推演</strong>
      </div>
      <ol>
        {steps.map((step, index) => (
          <li key={step.id}>
            <button
              type="button"
              aria-label={`步骤 ${index + 1}：${step.title}`}
              aria-current={index === activeIndex ? 'step' : undefined}
              data-active={index === activeIndex}
              data-complete={index < activeIndex}
              onClick={() => onSelect(index)}
            >
              <span className="flow-stepper__index">
                {index < activeIndex ? '✓' : String(index + 1).padStart(2, '0')}
              </span>
              <span>
                <strong>{step.title}</strong>
                <small>{step.output}</small>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
