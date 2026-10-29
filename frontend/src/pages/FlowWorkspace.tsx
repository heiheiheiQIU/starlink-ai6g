import { useEffect, useState } from 'react'

import { EngineerDetails } from '../components/EngineerDetails'
import { FlowStepper } from '../components/FlowStepper'
import { StagePanel } from '../components/StagePanel'
import { StepContextPanel } from '../components/StepContextPanel'
import { clampStep, FLOW_STEPS, INITIAL_TASKS, type StageTask } from '../domain/flow'

export function FlowWorkspace() {
  const [activeIndex, setActiveIndex] = useState(0)
  const [autoMode, setAutoMode] = useState(false)
  const [tasks, setTasks] = useState<StageTask[]>(() => [...INITIAL_TASKS])
  const activeStep = FLOW_STEPS[activeIndex]

  function selectStep(index: number) {
    setActiveIndex(clampStep(index))
  }

  useEffect(() => {
    if (!autoMode) return
    const timer = window.setInterval(() => {
      setActiveIndex((current) => {
        if (current >= FLOW_STEPS.length - 1) {
          setAutoMode(false)
          return current
        }
        return current + 1
      })
    }, 3200)
    return () => window.clearInterval(timer)
  }, [autoMode])

  return (
    <section className="flow-workspace">
      <header className="flow-workspace__intro">
        <div>
          <p className="eyebrow">MISSION DECISION WORKSPACE</p>
          <h1>流程主舞台</h1>
          <p>
            以电池健康风险为输入，让 AI 在 6G 空天地链路约束下决定“传什么、何时传、走哪条链路”。
          </p>
        </div>
        <div className="flow-intro-actions">
          {autoMode ? <span className="auto-badge">AUTO · 3S</span> : null}
          <button className="auto-demo" type="button" onClick={() => setAutoMode((value) => !value)}>
            {autoMode ? '停止演示' : '自动演示'}
          </button>
        <div className="mission-id">
          <span>MISSION</span>
          <strong>XA-202608</strong>
          <small>Observation v2026.10.29</small>
        </div>
        </div>
      </header>

      <div className="flow-workspace__grid">
        <FlowStepper
          activeIndex={activeIndex}
          steps={FLOW_STEPS}
          onSelect={selectStep}
        />
        <div className="flow-workspace__content">
          <StagePanel
            step={activeStep}
            stepNumber={activeIndex + 1}
            tasks={tasks}
            onTasksChange={setTasks}
          />
          <div className="stage-controls">
            <button
              type="button"
              disabled={activeIndex === 0}
              onClick={() => selectStep(activeIndex - 1)}
            >
              上一步
            </button>
            <span>
              {String(activeIndex + 1).padStart(2, '0')} / 06
            </span>
            <button
              className="stage-controls__primary"
              type="button"
              disabled={activeIndex === FLOW_STEPS.length - 1}
              onClick={() => selectStep(activeIndex + 1)}
            >
              下一步
            </button>
          </div>
          <EngineerDetails key={activeStep.id} step={activeStep} />
        </div>
          <StepContextPanel step={activeStep} index={activeIndex} />
      </div>
    </section>
  )
}
