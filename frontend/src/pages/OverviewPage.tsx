import type { PageId } from '../domain/navigation'
import { useOptionalSharedRun } from '../state/RunContext'

const CHAIN_NODES = [
  { id: 'arrival', label: '任务到达', sub: '数据入星上队列' },
  { id: 'window', label: '窗口预测', sub: '未来3个联系窗口' },
  { id: 'score', label: 'AI 评分', sub: '任务×模式打分' },
  { id: 'guard', label: '安全约束决策', sub: '窗口/能量/在途' },
  { id: 'send', label: '发送/确认', sub: '分块→ACK→去重' },
  { id: 'evaluate', label: '结果与追溯', sub: '指标与追溯记录' },
] as const

interface OverviewPageProps {
  onNavigate: (pageId: PageId) => void
}

export function OverviewPage({ onNavigate }: OverviewPageProps) {
  const sharedRun = useOptionalSharedRun()
  const online = sharedRun?.state.kind === 'online' ? sharedRun.state : null
  const onlineStatus = online?.status?.status === 'queued'
    ? '排队中'
    : online?.status?.status === 'running'
      ? '运行中'
      : online?.status?.status === 'completed'
        ? '已完成'
        : online?.status?.status === 'failed'
          ? '运行失败'
          : '状态同步中'
  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">MISSION OVERVIEW</p>
        <h1>运行总览</h1>
        <p>从星上任务入队、窗口预测和 AI 价值评分，到安全约束决策、链路执行与结果追溯，一屏掌握完整运行链路。</p>
      </header>

      <div className="overview-hero">
        <div className="chain-panel" aria-label="系统链路（标准场景演示）">
          <h2>系统链路 · 星上队列 → 网关确认</h2>
          <div className="chain-flow">
            {CHAIN_NODES.map((node, index) => (
              <div className="chain-flow__group" key={node.id}>
                <button className="chain-node" type="button" onClick={() => onNavigate('flow')}>
                  <strong>{node.label}</strong>
                  <small>{node.sub}</small>
                </button>
                {index < CHAIN_NODES.length - 1 ? (
                  <span className="chain-arrow" aria-hidden="true">→</span>
                ) : null}
              </div>
            ))}
          </div>
          <p className="panel-note">
            {online
              ? '六步与“任务决策”页面一一对应；当前阶段由在线事件推进，最终指标仅在任务完成后显示。'
              : '六步与“任务决策”页面一一对应；当前展示为标准场景演示，不作为实验结果。'}
          </p>
        </div>

        <div className="overview-cards">
          <div className="ov-card">
            <h3>当前任务实例</h3>
            <p className="mono">
              {online ? `${online.runId} · ${onlineStatus}` : '标准场景快照 · 已加载'}
            </p>
            <p className="table-note">
              {online
                ? `${online.status?.active_policies.join(' + ') || '策略加载中'} · 在线任务状态与事件`
                : 'EDF（规则）+ Learned（AI）· 同配置同随机种子 · 演示数据'}
            </p>
            <button className="link-button" type="button" onClick={() => onNavigate('flow')}>
              进入驾驶舱 ▸
            </button>
          </div>
          <div className="ov-card">
            <h3>当前链路态势</h3>
            <ul className="progress-list">
              <li><span className="status-dot" aria-hidden="true" /><span>星上任务队列 · 可用</span></li>
              <li><span className="status-dot" aria-hidden="true" /><span>联系窗口预测 · 已更新</span></li>
              <li><span className="status-dot" aria-hidden="true" /><span>GW 确认通道 · 在线</span></li>
            </ul>
          </div>
          <div className="ov-card">
            <h3>可用服务</h3>
            <ul className="progress-list">
              <li><span className="status-dot" aria-hidden="true" /><span>电池健康估计 · 演示模式</span></li>
              <li><span className="status-dot" aria-hidden="true" /><span>AI 信息价值评分 · 演示模式</span></li>
              <li><span className="status-dot" aria-hidden="true" /><span>发送确认与结果导出 · 可用</span></li>
            </ul>
          </div>
        </div>
      </div>

      <div className="quick-row">
        <button className="quick-entry" type="button" onClick={() => onNavigate('flow')}>
          <span className="quick-entry__icon" aria-hidden="true">⌁</span>
          <span><strong>任务决策</strong><small>六步闭环推演</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('compare')}>
          <span className="quick-entry__icon" aria-hidden="true">⇄</span>
          <span><strong>策略评估</strong><small>同配置双策略</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('evidence')}>
          <span className="quick-entry__icon" aria-hidden="true">✓</span>
          <span><strong>结果追溯</strong><small>数字可定位</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('assistant')}>
          <span className="quick-entry__icon" aria-hidden="true">✦</span>
          <span><strong>智能研判</strong><small>基于项目资料回答</small></span>
        </button>
      </div>
    </section>
  )
}
