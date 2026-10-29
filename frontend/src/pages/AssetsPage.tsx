const ASSETS = [
  {
    name: 'battery_source_windows.npz',
    sha: 'DE8EA216…F55499',
    size: '87.8 KB · (585,15,11)',
    license: '公开 NASA 数据 · 许可待补台账',
    licenseKind: 'warn' as const,
    note: 'R0 已核 SHA；谱系未闭合',
  },
  {
    name: 'battery_target_windows.npz',
    sha: 'E6D98DCF…BADC',
    size: '6.9 MB · (79710,15,11)',
    license: '半物理仿真 · 谱系未闭合',
    licenseKind: 'warn' as const,
    note: '目标域谱系待核',
  },
  {
    name: 'battery_lstm_source_only.pt',
    sha: '3145020C…D893',
    size: '216.7 KB',
    license: '队内旧成果 · 授权边界待队长确认',
    licenseKind: 'warn' as const,
    note: 'strict 加载 ✓',
  },
  {
    name: 'battery_lstm_finetune_best.pt',
    sha: '569B7D20…A4C',
    size: '216.7 KB',
    license: '队内旧成果 · ↔冻结JSON映射未核验（F3）',
    licenseKind: 'warn' as const,
    note: '仅哈希核验',
  },
  {
    name: 'battery_bilstm_coral_best.pt',
    sha: '756B58B7…694',
    size: '580.2 KB',
    license: '队内旧成果 · 输出级交叉核对未做（F1）',
    licenseKind: 'warn' as const,
    note: '两窗口前向 ✓',
  },
  {
    name: 'public_battery_fixed.csv',
    sha: '86CF8C06…984',
    size: '1.3 MB',
    license: '修正版 · 来源可定位',
    licenseKind: 'ok' as const,
    note: '标签 585/585 吻合',
  },
] as const

const MODEL_CARDS = [
  {
    model: 'LSTMRegressor / BiLSTMAttention',
    input: '冻结NPZ窗口(15,11)',
    output: 'raw_fraction（可>1，不裁剪）',
    boundary: '允许=离线证据；禁止=SOC/容量/能量/在线RUL',
  },
  {
    model: 'estimate_health（A-N1 内部核心）',
    input: 'history + now_s（仅 synthetic）',
    output: 'HealthCoreEstimate（内部类型）',
    boundary: '内部核心已 C 复核 accepted_with_notes；正式 HealthEstimate 适配+三样例待交付',
  },
  {
    model: 'score_actions（A-N3）',
    input: 'Observation',
    output: 'CandidateScore[]',
    boundary: '待交付（依赖 B-N2 教师接口）',
  },
] as const

export function AssetsPage() {
  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">FROZEN ASSET LEDGER</p>
        <h1>资产管理</h1>
        <p>冻结资产台账：来源、SHA256、许可状态与已知边界；未闭合项显式标注，不把旧指标当新成绩。</p>
      </header>

      <div className="console-card">
        <h2>冻结资产台账</h2>
        <div className="asset-grid">
          {ASSETS.map((asset) => (
            <article className="asset-card" key={asset.name}>
              <h3>{asset.name}</h3>
              <p className="mono asset-card__sha">{asset.sha}</p>
              <p className="table-note">{asset.size} · {asset.note}</p>
              <span className={`license-badge license-badge--${asset.licenseKind}`}>{asset.license}</span>
            </article>
          ))}
        </div>
        <p className="panel-note">
          数据来源：docs/evidence/B/R0_2026-10-29 与 v3 包 SOURCE_MANIFEST；大文件不入库，引用哈希与包内位置。
        </p>
      </div>

      <div className="console-card">
        <h2>模型卡</h2>
        <table className="console-table">
          <thead>
            <tr>
              <th>模型</th>
              <th>输入</th>
              <th>输出</th>
              <th>允许 / 禁止</th>
            </tr>
          </thead>
          <tbody>
            {MODEL_CARDS.map((card) => (
              <tr key={card.model}>
                <td>{card.model}</td>
                <td className="mono">{card.input}</td>
                <td className="mono">{card.output}</td>
                <td className="table-note">{card.boundary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
