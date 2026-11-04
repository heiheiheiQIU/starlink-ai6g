/**
 * 教师标签质量审计卡（P1-② 精简版）：
 * 展示冻结 v2 数据的标签辨识度（真实数据：samples.jsonl，SHA前缀 2df964e7）。
 * 结论口径：仅用于管线回归，不构成 learned 效果证据；数据重建（A-N4b）进行中。
 */

import auditFixture from '../fixtures/teacher_audit.json'

interface AuditSample {
  sample_id: string
  kind: 'unique-nonidle' | 'all-zero' | 'idle-tied' | 'other'
  energy_lower_Wh: number
  windows: number
}

interface AuditFixture {
  source: string
  source_sha256_prefix: string
  summary: {
    total: number
    allZero: number
    idleTied: number
    uniqueNonidle: number
    lowReserve: number
    noWindow: number
    preDeadline: number
  }
  samples: AuditSample[]
}

const KIND_LABELS: Record<AuditSample['kind'], string> = {
  'unique-nonidle': '唯一非idle最优',
  'all-zero': '任务标签全零',
  'idle-tied': 'idle并列最优',
  other: '其他',
}

const KIND_COLORS: Record<AuditSample['kind'], string> = {
  'unique-nonidle': '#2f9e6b',
  'all-zero': '#9c3b3b',
  'idle-tied': '#b8860b',
  other: '#4b6b84',
}

const fixture = auditFixture as AuditFixture

export function TeacherAuditCard() {
  const { summary, samples } = fixture
  return (
    <div className="console-card">
      <h2>教师标签质量审计（契约样例数据）</h2>
      <p className="panel-note" style={{ marginBottom: 10 }}>
        数据来源：{fixture.source}（SHA 前缀 {fixture.source_sha256_prefix}）；审计结论经 A 执行、C 独立复算一致。
        结论：冻结包仅用于管线回归，不构成学习评分器效果证据；数据重建（A-N4b）进行中。
      </p>

      <div className="audit-kpis">
        <div className="audit-kpi">
          <span>样本数</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="audit-kpi">
          <span>idle 并列最优</span>
          <strong>{summary.idleTied}/{summary.total}</strong>
        </div>
        <div className="audit-kpi">
          <span>唯一非idle最优</span>
          <strong>{summary.uniqueNonidle}/{summary.total}</strong>
        </div>
        <div className="audit-kpi">
          <span>任务标签全零</span>
          <strong>{summary.allZero}/{summary.total}</strong>
        </div>
        <div className="audit-kpi">
          <span>困难工况覆盖</span>
          <strong>{summary.lowReserve + summary.noWindow + summary.preDeadline}/{summary.total}</strong>
        </div>
      </div>

      <div className="audit-strip" aria-label="逐样本标签类别">
        {samples.map((sample) => (
          <i
            key={sample.sample_id}
            className="audit-strip__cell"
            style={{ background: KIND_COLORS[sample.kind] }}
            title={`${sample.sample_id}：${KIND_LABELS[sample.kind]}；能量下界 ${sample.energy_lower_Wh} Wh；未来窗口 ${sample.windows}`}
          />
        ))}
      </div>
      <div className="audit-legend">
        {(Object.keys(KIND_LABELS) as AuditSample['kind'][]).map((kind) => (
          <span key={kind}>
            <i style={{ background: KIND_COLORS[kind] }} />
            {KIND_LABELS[kind]}
          </span>
        ))}
      </div>
    </div>
  )
}
