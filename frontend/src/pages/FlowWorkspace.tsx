import { useEffect, useState } from 'react'

import { DemoOverlay } from '../components/DemoOverlay'
import { EngineerDetails } from '../components/EngineerDetails'
import { FlowStepper } from '../components/FlowStepper'
import { OperationsBar } from '../components/OperationsBar'
import { StagePanel } from '../components/StagePanel'
import { StepContextPanel } from '../components/StepContextPanel'
import { FLOW_STEPS, INITIAL_TASKS, type StageTask } from '../domain/flow'
import { liveRunSession } from '../domain/liveRunSession'
import {
  advanceSession,
  createRunSession,
  selectSessionStep,
  switchRunMode,
} from '../domain/runSession'
import { useOptionalSharedRun } from '../state/RunContext'

export function FlowWorkspace() {
  const [session, setSession] = useState(createRunSession)
  const [tasks, setTasks] = useState<StageTask[]>(() => [...INITIAL_TASKS])
  const sharedRun = useOptionalSharedRun()
  const controlledSession = sharedRun?.state.kind === 'online' ? liveRunSession(sharedRun.state) : null
  const visibleSession = controlledSession ?? session
  const activeIndex = visibleSession.stepIndex
  const autoMode = visibleSession.playback === 'playing'
  const activeStep = FLOW_STEPS[activeIndex]

  function selectStep(index: number) {
    setSession((current) => selectSessionStep(current, index, FLOW_STEPS.length))
  }

  function togglePlayback() {
    setSession((current) => ({
      ...current,
      playback: current.playback === 'playing' ? 'paused' : 'playing',
      phase: current.phase === 'complete' ? 'queued' : current.phase,
      stepIndex: current.phase === 'complete' ? 0 : current.stepIndex,
    }))
  }

  useEffect(() => {
    if (!autoMode) return
    const timer = window.setInterval(() => {
      setSession((current) => advanceSession(current, FLOW_STEPS.length))
    }, 3200)
    return () => window.clearInterval(timer)
  }, [autoMode])

  return (
    <section className="flow-workspace">
      <header className="flow-workspace__intro">
        <div>
          <p className="eyebrow">MISSION DECISION WORKSPACE</p>
          <h1>任务决策</h1>
          <p>
            以保守健康状态为输入，由 AI 评估遥测价值，再经 6G 链路安全约束形成可执行发送计划。
          </p>
        </div>
        <div className="flow-intro-actions">
          {autoMode ? <span className="auto-badge">AUTO · 3S</span> : null}
          <button className="auto-demo" type="button" disabled={controlledSession !== null} onClick={togglePlayback}>
            {controlledSession ? '实时事件驱动' : autoMode ? '停止演示' : '自动演示'}
          </button>
        <div className="mission-id">
          <span>MISSION</span>
          <strong>XA-202608</strong>
          <small>Observation v2026.10.29</small>
        </div>
        </div>
      </header>

      <OperationsBar
        session={visibleSession}
        liveControlled={controlledSession !== null}
        onModeChange={(mode) => setSession((current) => switchRunMode(current, mode))}
        onStep={() => setSession((current) => advanceSession(current, FLOW_STEPS.length))}
        onPlaybackToggle={togglePlayback}
      />

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

      <DemoOverlay
        visible={autoMode}
        step={activeStep}
        stepNumber={activeIndex + 1}
        total={FLOW_STEPS.length}
      />
    </section>
  )
}
