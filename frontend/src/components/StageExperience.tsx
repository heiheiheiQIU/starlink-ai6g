import { useState } from 'react'

import type { StageTask } from '../domain/flow'

interface StageExperienceProps {
  stepId: string
  tasks: readonly StageTask[]
  onTasksChange: (tasks: StageTask[]) => void
}

const SCORE_TABLE: Record<string, { factors: [number, number, number]; total: string }> = {
  '3.0': { factors: [92, 95, 55], total: '0.861' },
  '1.5': { factors: [55, 68, 40], total: '0.562' },
  '1.0': { factors: [30, 22, 60], total: '0.318' },
}

export function StageExperience({ stepId, tasks, onTasksChange }: StageExperienceProps) {
  const [windowStart, setWindowStart] = useState(68)
  const [disturbance, setDisturbance] = useState(false)
  const [showReal, setShowReal] = useState(false)
  const [scored, setScored] = useState(false)
  const [scoreTask, setScoreTask] = useState('T-101')
  const [mode, setMode] = useState('robust')
  const [playing, setPlaying] = useState(false)
  const [ackLost, setAckLost] = useState(false)
  const [generated, setGenerated] = useState(false)

  if (stepId === 'arrival') {
    return (
      <div className="experience experience--queue">
        <div className="experience-toolbar">
          <span className="live-pill">LIVE FIXTURE</span>
          <strong>队列任务 {String(tasks.length).padStart(2, '0')}</strong>
        </div>
        <div className="task-stack">
          {tasks.map((task) => (
            <button className="task-card task-drop" key={task.id} type="button">
              <span>{task.name}</span>
              <strong>{task.id}</strong>
              <small>w={task.weight}</small>
            </button>
          ))}
        </div>
        <div className="experience-actions">
          <button
            type="button"
            onClick={() => onTasksChange([...tasks, { id: `T-${104 + tasks.length - 3}`, name: '异常摘要', weight: '3.0', kind: 'a', deadline: '600s', remaining: '8KB' }])}
          >
            添加异常摘要
          </button>
          <button
            type="button"
            disabled={tasks.length === 0}
            onClick={() => onTasksChange(tasks.slice(0, -1))}
          >
            移除末项
          </button>
        </div>
      </div>
    )
  }

  if (stepId === 'forecast') {
    return (
      <div className="experience experience--timeline">
        <div className="timeline-track">
          <span className="timeline-window timeline-window--one" />
          <span className="timeline-window timeline-window--two" />
          <span
            className="timeline-window timeline-window--forecast"
            style={{ left: `${windowStart}%` }}
          />
          {showReal ? (
            <span className="timeline-window timeline-window--real" title="事后真实窗口，仅供对比，策略不可见" />
          ) : null}
          <div className="timeline-axis"><span>0s</span><span>300s</span><span>600s</span></div>
        </div>
        <label>
          调整预测窗口
          <input
            type="range"
            min="50"
            max="84"
            value={windowStart}
            onChange={(event) => setWindowStart(Number(event.target.value))}
          />
        </label>
        <p className="experience-hint">
          拖动滑杆=提前或推迟第三个预测窗口：观察下一步发送安排如何变化（策略对窗口的敏感度演示）。
        </p>
        <div className="experience-actions">
          <button type="button" data-active={showReal} onClick={() => setShowReal((value) => !value)}>
            {showReal ? '隐藏事后真实窗口' : '显示事后真实窗口'}
          </button>
          <button type="button" data-active={disturbance} onClick={() => setDisturbance((value) => !value)}>
            {disturbance ? '已注入链路扰动' : '注入链路扰动'}
          </button>
        </div>
        {showReal ? (
          <p className="experience-hint">灰色虚线=事后评估参考，在线策略不可见（防未来信息泄漏）。</p>
        ) : null}
      </div>
    )
  }

  if (stepId === 'score') {
    const current = tasks.find((task) => task.id === scoreTask) ?? tasks[0]
    const table = SCORE_TABLE[current.weight] ?? SCORE_TABLE['1.0']
    const top = [...tasks].sort((a, b) => Number(b.weight) - Number(a.weight))[0]
    return (
      <div className="experience experience--score">
        <div className="score-tabs">
          {tasks.map((task) => (
            <button
              key={task.id}
              type="button"
              data-active={task.id === current.id}
              onClick={() => { setScoreTask(task.id); setScored(false) }}
            >
              {task.id}
            </button>
          ))}
        </div>
        {['风险权重', '期限紧迫度', '能耗影响'].map((label, index) => (
          <div className="score-factor" key={label}>
            <span>{label}</span>
            <i><b style={{ width: scored ? `${table.factors[index]}%` : 0 }} /></i>
            <strong>{scored ? `${table.factors[index]}%` : '—'}</strong>
          </div>
        ))}
        <button className="experience-primary" type="button" onClick={() => setScored(true)}>运行 AI 评分</button>
        {scored ? (
          <div className="score-verdict">
            <span>决策候选</span>
            <strong>{top.id} × robust</strong>
            <small>综合评分 {SCORE_TABLE[top.weight].total}（队列最高）→ 交给下一步约束解码</small>
          </div>
        ) : null}
      </div>
    )
  }

  if (stepId === 'decode') {
    const quota = mode === 'idle'
      ? ['本时隙无可见窗口 → 不发送', '字节配额 = 0 B']
      : mode === 'fast'
        ? ['fast 功耗 16W 将触及能量储备 → 被否决', '回退 robust：8000 bit/s × 60s = 480000 bit', '÷ 8 = 60000 B → min(1024, 60000) = 1024 B']
        : ['8000 bit/s × 剩余窗口 60s = 480000 bit', '÷ 8 = 60000 B → min(1024, 60000)', '本时隙字节配额 = 1024 B']
    return (
      <div className="experience experience--checks">
        <div className="mode-picker">
          {['robust', 'fast', 'idle'].map((value) => (
            <button key={value} type="button" data-active={mode === value} onClick={() => setMode(value)}>{value}</button>
          ))}
        </div>
        {['窗口可见', '数据位置匹配', '单在途无冲突', '能量储备', '字节配额'].map((check, index) => {
          const failed = mode === 'fast' && index === 3
          return <div className={`constraint-row ${failed ? 'constraint-row--failed' : ''}`} key={check}><span>{failed ? '×' : '✓'}</span><strong>{check}</strong><small>{failed ? 'ENERGY_GUARD_REJECTED' : 'PASS'}</small></div>
        })}
        <div className="quota-panel" key={mode}>
          {quota.map((line, index) => (
            <p key={line} style={{ animationDelay: `${index * 380}ms` }}>{line}</p>
          ))}
        </div>
      </div>
    )
  }

  if (stepId === 'confirm') {
    return (
      <div className="experience experience--orbit">
        <div className="orbit-scene" data-playing={playing} data-lost={ackLost}>
          <span className="earth" />
          <span className="orbit-ring" />
          <span className="satellite">SAT</span>
          <span className="ground">GW</span>
          <span className="signal-beam" />
          <span className="packet">1024B</span>
          {!ackLost ? <span className="ack-packet">ACK</span> : null}
        </div>
        <div className="orbit-legend" aria-label="链路动画图例">
          <span>光束=数据发送</span>
          <span>1024B=数据块</span>
          <span>ACK=网关确认回传</span>
        </div>
        <p className="orbit-status">{ackLost ? 'ACK 已丢失 · 下一窗口重传 · 网关去重' : playing ? '链路播放中 · 数据块传输' : '链路已暂停 · 等待操作'}</p>
        <div className="experience-actions">
          <button type="button" onClick={() => setPlaying((value) => !value)}>{playing ? '暂停回放' : '播放回放'}</button>
          <button type="button" onClick={() => setPlaying(true)}>单步 +30s</button>
          <button type="button" onClick={() => setAckLost(true)}>注入 ACK 丢失</button>
        </div>
      </div>
    )
  }

  return (
    <div className="experience experience--evidence" data-generated={generated}>
      <div className="evidence-metrics">
        {['加权按时交付率', '关键任务成功率', 'J / 成功 bit'].map((label, index) => (
          <button type="button" key={label}><span>{label}</span><strong>{generated ? ['待真实 run', '待真实 run', '待真实 run'][index] : '—'}</strong></button>
        ))}
      </div>
      <svg className="evidence-chart" viewBox="0 0 620 130" role="img" aria-label="指标曲线契约样例">
        <path d="M20 108 L120 90 L220 96 L320 62 L420 70 L520 34 L600 42" />
        <path d="M20 112 L120 104 L220 82 L320 88 L420 54 L520 60 L600 28" />
      </svg>
      <button className="experience-primary" type="button" onClick={() => setGenerated(true)}>生成实验报告</button>
      {generated ? <p className="report-ready">证据卡已生成 · 指标仍待真实 run</p> : null}
    </div>
  )
}
