import type { PageId } from '../domain/navigation'

const CHAIN_NODES = [
  { id: 'arrival', label: '任务到达', sub: '数据入星上队列' },
  { id: 'window', label: '窗口预测', sub: '未来3个联系窗口' },
  { id: 'score', label: 'AI 评分', sub: '任务×模式打分' },
  { id: 'guard', label: '约束解码', sub: '窗口/能量/在途' },
  { id: 'send', label: '发送/确认', sub: '分块→ACK→去重' },
  { id: 'evaluate', label: '评估与证据', sub: '指标与证据卡' },
] as const

interface OverviewPageProps {
  onNavigate: (pageId: PageId) => void
}

export function OverviewPage({ onNavigate }: OverviewPageProps) {
  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">MISSION OVERVIEW</p>
        <h1>任务总览</h1>
        <p>一条链路贯穿全部页面：从任务到达星上队列，到窗口预测、AI评分、约束解码、发送确认与证据评估。</p>
      </header>

      <div className="overview-hero">
        <div className="chain-panel" aria-label="系统链路（契约样例）">
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
            六步与“流程主舞台”一一对应；当前展示为契约样例，非实验结果。
          </p>
        </div>

        <div className="overview-cards">
          <div className="ov-card">
            <h3>当前实验</h3>
            <p className="mono">demo_fixture_001 · completed（占位）</p>
            <p className="table-note">edf（规则）+ learned（AI）· 同配置同 seed · 契约样例</p>
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
              <li><span className="status-dot" aria-hidden="true" /><span>发送确认与证据导出 · 可用</span></li>
            </ul>
          </div>
        </div>
      </div>

      <div className="quick-row">
        <button className="quick-entry" type="button" onClick={() => onNavigate('flow')}>
          <span className="quick-entry__icon" aria-hidden="true">⌁</span>
          <span><strong>流程主舞台</strong><small>六步层层递进</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('compare')}>
          <span className="quick-entry__icon" aria-hidden="true">⇄</span>
          <span><strong>方案对比</strong><small>同配置双策略</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('evidence')}>
          <span className="quick-entry__icon" aria-hidden="true">✓</span>
          <span><strong>证据链</strong><small>数字可定位</small></span>
        </button>
        <button className="quick-entry" type="button" onClick={() => onNavigate('assistant')}>
          <span className="quick-entry__icon" aria-hidden="true">✦</span>
          <span><strong>AI 助手</strong><small>只答证据索引</small></span>
        </button>
      </div>
    </section>
  )
}
