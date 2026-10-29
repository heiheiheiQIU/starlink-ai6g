import type { FlowStep } from '../domain/flow'

const STAGE_METRICS: Record<FlowStep['id'], readonly [string, string][]> = {
  health: [
    ['SOH', '82.4%'],
    ['RUL P50', '184 cyc'],
    ['置信度', '0.91'],
  ],
  forecast: [
    ['风险窗口', '03'],
    ['预测跨度', '12 h'],
    ['版本一致', 'YES'],
  ],
  value: [
    ['候选遥测', '18'],
    ['高价值项', '05'],
    ['最高 VoI', '0.86'],
  ],
  allocate: [
    ['可见链路', '04'],
    ['资源利用', '73%'],
    ['约束违反', '0'],
  ],
  confirm: [
    ['计划发送', '05'],
    ['已确认', '04'],
    ['等待确认', '01'],
  ],
  archive: [
    ['证据对象', '27'],
    ['哈希覆盖', '100%'],
    ['待冻结', '01'],
  ],
}

interface StagePanelProps {
  step: FlowStep
  stepNumber: number
}

export function StagePanel({ step, stepNumber }: StagePanelProps) {
  return (
    <section className="stage-panel">
      <div className="stage-panel__header">
        <div>
          <p className="stage-kicker">
            STAGE {String(stepNumber).padStart(2, '0')} / 06
          </p>
          <h2>{step.title}</h2>
          <p className="stage-question">{step.question}</p>
        </div>
        <span className={`stage-state stage-state--${step.status}`}>
          {step.status === 'ready'
            ? '估计层'
            : step.status === 'decision'
              ? 'AI+6G 决策层'
              : '执行证据层'}
        </span>
      </div>

      <p className="stage-description">{step.description}</p>

      <div className="stage-metrics" aria-label="当前步骤样例指标">
        {STAGE_METRICS[step.id].map(([label, value]) => (
          <div className="stage-metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>FIXTURE</small>
          </div>
        ))}
      </div>

      <div className="logic-strip">
        <div>
          <span>输入</span>
          <strong>{step.input}</strong>
        </div>
        <span className="logic-strip__arrow" aria-hidden="true">
          →
        </span>
        <div>
          <span>核心方法</span>
          <strong>{step.method}</strong>
        </div>
        <span className="logic-strip__arrow" aria-hidden="true">
          →
        </span>
        <div>
          <span>输出</span>
          <strong>{step.output}</strong>
        </div>
      </div>
    </section>
  )
}
