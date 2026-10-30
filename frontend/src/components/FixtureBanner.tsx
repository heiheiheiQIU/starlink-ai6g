export function FixtureBanner() {
  return (
    <aside className="fixture-banner" aria-label="数据状态说明">
      <span className="fixture-banner__badge">FIXTURE</span>
      <span>
        当前展示：<strong>契约样例数据</strong>，仅用于功能演示与数据结构说明，
        <strong>非实验结果</strong>。
      </span>
      <span className="fixture-banner__source">来源：接口契约样例</span>
    </aside>
  )
}
