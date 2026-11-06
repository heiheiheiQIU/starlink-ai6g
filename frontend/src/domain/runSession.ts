export type RunMode = 'fixture' | 'live'
export type RunConnection = 'fixture' | 'online' | 'offline'
export type RunPlayback = 'paused' | 'playing' | 'complete' | 'failed'
export type RunPhase =
  | 'queued'
  | 'forecasting'
  | 'scoring'
  | 'guarding'
  | 'transmitting'
  | 'evidencing'
  | 'complete'
  | 'failed'

export interface RunSessionState {
  mode: RunMode
  connection: RunConnection
  playback: RunPlayback
  phase: RunPhase
  stepIndex: number
  runId: string | null
  lastSync: string | null
  evidence: 'unfrozen' | 'frozen'
}

const STEP_PHASES: readonly RunPhase[] = [
  'queued',
  'forecasting',
  'scoring',
  'guarding',
  'transmitting',
  'evidencing',
]

export function createRunSession(): RunSessionState {
  return {
    mode: 'fixture',
    connection: 'fixture',
    playback: 'paused',
    phase: 'queued',
    stepIndex: 0,
    runId: 'fixture_XA-202608',
    lastSync: null,
    evidence: 'unfrozen',
  }
}

export function selectSessionStep(
  session: RunSessionState,
  requestedIndex: number,
  totalSteps: number,
): RunSessionState {
  const stepIndex = Math.min(Math.max(requestedIndex, 0), totalSteps - 1)
  return { ...session, stepIndex, phase: STEP_PHASES[stepIndex] ?? 'queued' }
}

export function advanceSession(session: RunSessionState, totalSteps: number): RunSessionState {
  if (session.phase === 'failed') return session
  if (session.stepIndex >= totalSteps - 1) {
    return { ...session, phase: 'complete', playback: 'complete' }
  }
  return selectSessionStep(session, session.stepIndex + 1, totalSteps)
}

export function switchRunMode(session: RunSessionState, mode: RunMode): RunSessionState {
  if (mode === session.mode) return session
  return {
    ...createRunSession(),
    mode,
    connection: mode === 'live' ? 'offline' : 'fixture',
    playback: 'paused',
    runId: mode === 'live' ? null : 'fixture_XA-202608',
    evidence: 'unfrozen',
  }
}
