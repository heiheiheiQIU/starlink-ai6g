export interface FlowStep {
  id: string
  title: string
  shortTitle: string
  question: string
  description: string
  input: string
  method: string
  output: string
  artifact: string
  status: 'ready' | 'decision' | 'evidence'
}

export const FLOW_STEPS: readonly FlowStep[] = [
  {
    id: 'arrival',
    title: '任务到达',
    shortTitle: '入队',
    question: '哪些星上业务进入队列，健康风险如何影响任务权重？',
    description: '接收异常摘要、周期记录与批量历史任务，保留期限、权重、数据位置和剩余字节。健康估计作为任务风险上下文，而不是最终业务本身。',
    input: 'Task[] + HealthEstimate',
    method: '业务入队、风险标注与缓存核算',
    output: 'TeacherQueue',
    artifact: 'observation.json',
    status: 'ready',
  },
  {
    id: 'forecast',
    title: '窗口预测',
    shortTitle: '预测',
    question: '未来哪些窗口最可能暴露风险或补充关键证据？',
    description: '在可见窗口内预测风险演化，严格绑定同一观测版本，禁止引入未来信息。',
    input: 'HealthEstimate + visibility_windows',
    method: '时序风险外推与窗口对齐',
    output: 'WindowForecast[]',
    artifact: 'window_forecast.json',
    status: 'ready',
  },
  {
    id: 'score',
    title: 'AI评分',
    shortTitle: '评分',
    question: '有限链路下，哪条遥测最值得现在传？',
    description: 'AI 联合健康风险、信息新鲜度与不确定性，计算每比特的决策价值。',
    input: 'Forecast + telemetry_candidates',
    method: 'VoI / bit 与风险敏感排序',
    output: 'ValuedCandidate[]',
    artifact: 'value_scores.json',
    status: 'decision',
  },
  {
    id: 'decode',
    title: '约束解码',
    shortTitle: '解码',
    question: '在窗口、带宽和时延约束下，如何形成可执行计划？',
    description: '面向空天地一体化链路进行多约束选择，生成可解释且可降级的调度决策。',
    input: 'ValuedCandidate[] + LinkState',
    method: '风险约束优化 / 启发式基线',
    output: 'ScheduleDecision',
    artifact: 'schedule_decision.json',
    status: 'decision',
  },
  {
    id: 'confirm',
    title: '发送/确认',
    shortTitle: '执行',
    question: '决策是否被执行，并取得端到端确认？',
    description: '模拟星地发送、确认、超时和重试事件，保留每个状态变化的可追溯记录。',
    input: 'ScheduleDecision + TeacherQueue',
    method: '离散事件仿真与幂等确认',
    output: 'ExecutionReceipt',
    artifact: 'events.jsonl',
    status: 'evidence',
  },
  {
    id: 'evaluate',
    title: '评估与证据',
    shortTitle: '评估',
    question: '评委能否复核这次决策从何而来？',
    description: '冻结输入、模型、策略和事件哈希，形成从观测到执行的闭环证据链。',
    input: 'Inputs + decisions + receipts',
    method: '版本绑定、哈希索引与审计摘要',
    output: 'EvidenceBundle',
    artifact: 'evidence_index.json',
    status: 'evidence',
  },
] as const

export function clampStep(index: number): number {
  return Math.min(Math.max(index, 0), FLOW_STEPS.length - 1)
}
