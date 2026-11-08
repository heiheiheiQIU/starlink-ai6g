import type { FlowStep, StageTask } from '../domain/flow'
import type { Event } from '../types/contracts'
import { LiveStageExperience } from './LiveStageExperience'
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
    ['追溯对象', '27'],
    ['完整性校验', '100%'],
    ['待归档', '01'],
  ],
}

interface StagePanelProps {
  step: FlowStep
  stepNumber: number
  tasks: readonly StageTask[]
  onTasksChange: (tasks: StageTask[]) => void
  liveEvents?: readonly Event[]
}

function liveMetrics(stepId: FlowStep['id'], events: readonly Event[]): readonly [string, string][] {
  const count = (type: Event['event_type']) => events.filter((event) => event.event_type === type).length
  const latest = events.at(-1)
  const decisions = events.filter((event) => event.event_type === 'decision' && event.data !== null && 'candidate_scores' in event.data)
  const decision = decisions.at(-1)
  const decisionData = decision?.data && 'candidate_scores' in decision.data ? decision.data : null
  if (stepId === 'arrival') return [['到达任务', String(count('arrived'))], ['载荷字节', String(events.filter((event) => event.event_type === 'arrived').reduce((sum, event) => sum + event.payload_bytes, 0))], ['最新事件', latest ? `e=${latest.event_id}` : '—']]
  if (stepId === 'forecast') return [['窗口变化', String(count('window_changed'))], ['状态快照', String(count('snapshot'))], ['最新时刻', latest ? `${latest.sim_time_s}s` : '—']]
  if (stepId === 'score') return [['决策事件', String(decisions.length)], ['候选动作', String(decisionData?.candidate_scores.length ?? 0)], ['策略数量', String(new Set(events.map((event) => event.policy_id)).size)]]
  if (stepId === 'decode') return [['约束检查', String(decisionData?.constraint_checks.length ?? 0)], ['拒绝项', String(decisionData?.constraint_checks.filter((check) => !check.passed).length ?? 0)], ['安全回退', decisionData?.fallback ? 'YES' : 'NO']]
  if (stepId === 'confirm') return [['发送', String(count('sent'))], ['确认', String(count('acked'))], ['丢失', String(count('dropped'))]]
  return [['事件总数', String(events.length)], ['策略数量', String(new Set(events.map((event) => event.policy_id)).size)], ['最新事件', latest ? `e=${latest.event_id}` : '—']]
}

export function StagePanel({ step, stepNumber, tasks, onTasksChange, liveEvents }: StagePanelProps) {
  const metrics =
    liveEvents !== undefined
      ? liveMetrics(step.id, liveEvents)
      : step.id === 'arrival'
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
              : '结果追溯层'}
        </span>
      </div>

      <p className="stage-description">{step.description}</p>

      {liveEvents === undefined
        ? <StageExperience key={step.id} stepId={step.id} tasks={tasks} onTasksChange={onTasksChange} />
        : <LiveStageExperience stepId={step.id} events={liveEvents} />}

      <div className="stage-metrics" aria-label={liveEvents === undefined ? '当前步骤演示指标' : '当前步骤在线摘要'}>
        {metrics.map(([label, value]) => (
          <div className="stage-metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{liveEvents === undefined ? '演示' : '在线事件'}</small>
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
