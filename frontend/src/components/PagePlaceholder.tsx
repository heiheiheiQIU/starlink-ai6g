import type { PageId } from '../domain/navigation'
import { getPageLabel } from '../domain/navigation'

const PAGE_SUMMARIES: Record<PageId, string> = {
  flow: '从健康估计出发，完成信息价值评估、星地链路决策与可复核下发。',
  overview: '汇总任务窗口、航天器健康风险与当前通信资源状态。',
  assistant: '围绕异常、策略依据和证据链进行可追溯问答。',
  compare: '在同一观测快照下对比多种遥测调度策略。',
  evidence: '核验输入、预测版本、决策版本与执行回执。',
  assets: '管理契约样例、模型版本与前端可视化资源。',
}

interface PagePlaceholderProps {
  pageId: PageId
}

export function PagePlaceholder({ pageId }: PagePlaceholderProps) {
  return (
    <section className="page-placeholder">
      <p className="eyebrow">XINGDI COMMAND / {pageId.toUpperCase()}</p>
      <h1>{getPageLabel(pageId)}</h1>
      <p>{PAGE_SUMMARIES[pageId]}</p>
      <div className="placeholder-panel">
        <span className="placeholder-panel__index">01</span>
        <div>
          <strong>工作区正在按 v4 结构建设</strong>
          <p>本页已进入正式导航体系，后续内容按接口契约逐项接入。</p>
        </div>
      </div>
    </section>
  )
}
