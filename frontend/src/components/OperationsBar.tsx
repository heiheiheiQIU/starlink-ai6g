import type { RunMode, RunSessionState } from '../domain/runSession'

interface OperationsBarProps {
  session: RunSessionState
  onModeChange: (mode: RunMode) => void
  onStep: () => void
  onPlaybackToggle: () => void
  liveControlled?: boolean
}

const PHASE_LABELS: Record<RunSessionState['phase'], string> = {
  queued: '任务已入队',
  forecasting: '窗口预测中',
  scoring: 'AI 评分中',
  guarding: '安全约束校验中',
  transmitting: '链路执行中',
  evidencing: '结果归档中',
  complete: '流程完成',
  failed: '运行失败',
}

export function OperationsBar({
  session,
  onModeChange,
  onStep,
  onPlaybackToggle,
  liveControlled = false,
}: OperationsBarProps) {
  const modeLabel = session.mode === 'fixture' ? '标准场景演示' : '在线任务执行'
  const connectionLabel =
    session.connection === 'online'
      ? '任务服务在线'
      : session.connection === 'offline'
        ? '任务服务离线'
        : '任务服务未接入'
  return (
    <section className="operations-bar" aria-label="工程运行状态">
      <div className="operations-bar__identity">
        <span className={`operations-mode operations-mode--${session.mode}`}>{modeLabel}</span>
        <div>
          <strong>{session.runId ?? '尚未创建任务实例'}</strong>
          <small>
            <span>{connectionLabel}</span>
            <span aria-hidden="true"> · </span>
            <span>{session.lastSync ? `同步 ${session.lastSync}` : '无远端同步'}</span>
          </small>
        </div>
      </div>

      <div
        className="runtime-pulse"
        data-phase={session.phase}
        data-playback={session.playback}
        data-testid="runtime-pulse"
      >
        <span className="runtime-pulse__beam" />
        <strong>{PHASE_LABELS[session.phase]}</strong>
        <small>{String(session.stepIndex + 1).padStart(2, '0')} / 06</small>
      </div>

      <div className="operations-bar__truth">
        <span data-state={session.evidence}>{session.evidence === 'frozen' ? '结果已归档' : '结果待归档'}</span>
        <span>{session.mode === 'fixture' ? '演示数值不作实验结论' : '仅完成任务展示最终指标'}</span>
      </div>

      <div className="operations-bar__actions">
        <button type="button" disabled={liveControlled} onClick={() => onModeChange(session.mode === 'fixture' ? 'live' : 'fixture')}>
          {liveControlled ? '在线任务已接管' : session.mode === 'fixture' ? '切换到在线任务' : '返回场景演示'}
        </button>
        <button type="button" onClick={onStep} disabled={liveControlled || session.phase === 'complete' || session.phase === 'failed'}>
          {liveControlled ? '由事件推进' : '单步推进'}
        </button>
        <button className="operations-bar__primary" type="button" disabled={liveControlled} onClick={onPlaybackToggle}>
          {liveControlled ? '实时事件模式' : session.playback === 'playing' ? '暂停自动运行' : '自动运行'}
        </button>
      </div>
    </section>
  )
}
