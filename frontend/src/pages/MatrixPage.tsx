import { CountUp } from '../components/CountUp'
import { TeacherAuditCard } from '../components/TeacherAuditCard'
import {
  DISTURBANCE_LABELS,
  ENERGY_LABELS,
  LOAD_LABELS,
  MATRIX_SOURCE_NOTE,
  POLICY_LABELS,
  heatColor,
  loadMatrixSummary,
} from '../domain/matrix'

const LOAD_ORDER = ['low', 'near_capacity', 'overload'] as const
const ENERGY_ORDER = ['low', 'medium', 'ample'] as const
const DISTURBANCE_ORDER = ['mild', 'strong'] as const
const POLICY_ORDER = ['edf', 'value'] as const

const summary = loadMatrixSummary()

export function MatrixPage() {
  return (
    <section className="console-page">
      <header className="console-page__intro">
        <p className="eyebrow">EXPERIMENT MATRIX · 18 CELLS</p>
        <h1>实验矩阵</h1>
        <p>预登记的 18 个工况（3档负载 × 3档能量余量 × 2档链路扰动）下规则基线的真实运行结果热力图。</p>
      </header>

      <div className="kpi-row">
        <div className="kpi-card">
          <span>真实运行</span>
          <strong><CountUp value={summary.runCount} decimals={0} /></strong>
          <small>180 轨迹 × 2 规则</small>
        </div>
        <div className="kpi-card">
          <span>EDF 规则均按时交付率</span>
          <strong><CountUp value={summary.policyMeans.edf * 100} />%</strong>
          <small>180 次运行</small>
        </div>
        <div className="kpi-card">
          <span>value 规则均按时交付率</span>
          <strong><CountUp value={summary.policyMeans.value * 100} />%</strong>
          <small>180 次运行</small>
        </div>
        <div className="kpi-card">
          <span>工况数</span>
          <strong><CountUp value={summary.cells.length} decimals={0} /></strong>
          <small>3 × 3 × 2</small>
        </div>
      </div>

      <div className="console-card">
        <h2>18 工况热力网格</h2>
        <p className="panel-note">
          行=负载档位，列=能量余量；每格内 2×2 小格 = 扰动（轻微/强烈）× 策略（EDF/value），
          颜色=加权按时交付率（红低→绿高），数值为该工况 10 条轨迹均值。
        </p>
        <table className="matrix-grid" aria-label="18工况规则基线热力网格">
          <thead>
            <tr>
              <th className="matrix-corner">负载 ↓ / 能量 →</th>
              {ENERGY_ORDER.map((energy) => (
                <th key={energy}>{ENERGY_LABELS[energy]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LOAD_ORDER.map((load) => (
              <tr key={load}>
                <th scope="row">{LOAD_LABELS[load]}</th>
                {ENERGY_ORDER.map((energy) => {
                  const cells = DISTURBANCE_ORDER.map((disturbance) =>
                    summary.cells.find(
                      (cell) =>
                        cell.def.loadLevel === load &&
                        cell.def.energyMargin === energy &&
                        cell.def.disturbance === disturbance,
                    ),
                  )
                  return (
                    <td key={energy} className="matrix-cell">
                      {DISTURBANCE_ORDER.map((disturbance) => {
                        const cell = cells.find((item) => item?.def.disturbance === disturbance)
                        return (
                          <div key={disturbance} className="matrix-cell__block">
                            <p className="matrix-cell__label">{DISTURBANCE_LABELS[disturbance]}</p>
                            <div className="matrix-cell__tiles">
                              {POLICY_ORDER.map((policy) => {
                                const bucket = cell?.byPolicy[policy]
                                const wot = bucket?.runs ? bucket.wotMean : 0
                                return (
                                  <div
                                    key={policy}
                                    className="matrix-tile"
                                    style={{ background: heatColor(wot) }}
                                    title={`${LOAD_LABELS[load]} · ${ENERGY_LABELS[energy]} · ${DISTURBANCE_LABELS[disturbance]} · ${POLICY_LABELS[policy]}`}
                                  >
                                    <span>{POLICY_LABELS[policy].split(' ')[0]}</span>
                                    <strong>{bucket?.runs ? `${(wot * 100).toFixed(0)}%` : '—'}</strong>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )
                      })}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="matrix-legend">
          <span>0% 未交付</span>
          <i className="matrix-legend__scale" />
          <span>100% 全按时</span>
          <small>EDF=vale 规则；learned 接入后本网格自动扩展第三行对比</small>
        </div>
      </div>

      <TeacherAuditCard />

      <div className="console-card source-card">
        <h2>数据来源与边界</h2>
        <p className="panel-note">{MATRIX_SOURCE_NOTE}</p>
        <p className="panel-note">
          低载/能量充足工况两规则均接近满分属预期——该类工况正是"额外预测无益"的反例，如实展示、不删负结果。
        </p>
      </div>
    </section>
  )
}
