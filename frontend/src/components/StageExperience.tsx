import { useState } from 'react'

interface StageExperienceProps {
  stepId: string
}

export function StageExperience({ stepId }: StageExperienceProps) {
  const [queueCount, setQueueCount] = useState(3)
  const [windowStart, setWindowStart] = useState(68)
  const [disturbance, setDisturbance] = useState(false)
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
          <strong>队列任务 {String(queueCount).padStart(2, '0')}</strong>
        </div>
        <div className="task-stack">
          {Array.from({ length: queueCount }, (_, index) => (
            <button className="task-card task-drop" key={index} type="button">
              <span>{index === 0 ? '异常摘要' : index === 1 ? '周期记录' : '批量历史'}</span>
              <strong>T-{101 + index}</strong>
              <small>w={index === 0 ? '3.0' : index === 1 ? '1.5' : '1.0'}</small>
            </button>
          ))}
        </div>
        <div className="experience-actions">
          <button type="button" onClick={() => setQueueCount((count) => count + 1)}>
            添加异常摘要
          </button>
          <button type="button" onClick={() => setQueueCount((count) => Math.max(0, count - 1))}>
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
        <button type="button" data-active={disturbance} onClick={() => setDisturbance((v) => !v)}>
          {disturbance ? '已注入链路扰动' : '注入链路扰动'}
        </button>
      </div>
    )
  }

  if (stepId === 'score') {
    const scores = scoreTask === 'T-101' ? [92, 95, 55] : [55, 68, 40]
    return (
      <div className="experience experience--score">
        <div className="score-tabs">
          {['T-101', 'T-102', 'T-103'].map((task) => (
            <button key={task} type="button" data-active={task === scoreTask} onClick={() => { setScoreTask(task); setScored(false) }}>
              {task}
            </button>
          ))}
        </div>
        {['风险权重', '期限紧迫度', '能耗影响'].map((label, index) => (
          <div className="score-factor" key={label}>
            <span>{label}</span>
            <i><b style={{ width: scored ? `${scores[index]}%` : 0 }} /></i>
            <strong>{scored ? `${scores[index]}%` : '—'}</strong>
          </div>
        ))}
        <button className="experience-primary" type="button" onClick={() => setScored(true)}>运行 AI 评分</button>
      </div>
    )
  }

  if (stepId === 'decode') {
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
