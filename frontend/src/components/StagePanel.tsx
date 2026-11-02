import type { FlowStep, StageTask } from '../domain/flow'
import { StageExperience } from './StageExperience'

const STAGE_METRICS: Record<FlowStep['id'], readonly [string, string][]> = {
  arrival: [
    ['队列任务', ''],
    ['缓存占用', '4.8 KB'],
    ['最高权重', '3.0'],
  ],
  forecast: [
    ['风险窗口', '03'],
    ['预测跨度', '12 h'],
    ['版本一致', 'YES'],
  ],
  score: [
    ['候选遥测', '18'],
    ['高价值项', '05'],
    ['最高 VoI', '0.86'],
  ],
  decode: [
    ['可见链路', '04'],
    ['资源利用', '73%'],
    ['约束违反', '0'],
  ],
  confirm: [
    ['计划发送', '05'],
    ['已确认', '04'],
    ['等待确认', '01'],
  ],
  evaluate: [
    ['证据对象', '27'],
    ['哈希覆盖', '100%'],
    ['待冻结', '01'],
  ],
}

interface StagePanelProps {
  step: FlowStep
  stepNumber: number
  tasks: readonly StageTask[]
  onTasksChange: (tasks: StageTask[]) => void
}

export function StagePanel({ step, stepNumber, tasks, onTasksChange }: StagePanelProps) {
  const metrics =
    step.id === 'arrival'
      ? [['队列任务', String(tasks.length).padStart(2, '0')], ['缓存占用', '4.8 KB'], ['最高权重', '3.0']]
      : STAGE_METRICS[step.id]
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

      <StageExperience key={step.id} stepId={step.id} tasks={tasks} onTasksChange={onTasksChange} />

      <div className="stage-metrics" aria-label="当前步骤样例指标">
        {metrics.map(([label, value]) => (
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
