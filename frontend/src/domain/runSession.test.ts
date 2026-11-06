import { describe, expect, it } from 'vitest'

import {
  advanceSession,
  createRunSession,
  selectSessionStep,
  switchRunMode,
} from './runSession'

describe('flow run session', () => {
  it('advances one deterministic phase at a time and completes at evidence', () => {
    let session = createRunSession()
    expect(session.stepIndex).toBe(0)
    expect(session.phase).toBe('queued')
    session = advanceSession(session, 6)
    expect(session.stepIndex).toBe(1)
    expect(session.phase).toBe('forecasting')
    session = selectSessionStep(session, 5, 6)
    expect(session.phase).toBe('evidencing')
    session = advanceSession(session, 6)
    expect(session.phase).toBe('complete')
    expect(session.stepIndex).toBe(5)
  })

  it('clears fixture state when switching to a real offline session', () => {
    const session = switchRunMode(
      { ...createRunSession(), runId: 'fixture_001', evidence: 'frozen' },
      'live',
    )
    expect(session.mode).toBe('live')
    expect(session.connection).toBe('offline')
    expect(session.runId).toBeNull()
    expect(session.evidence).toBe('unfrozen')
    expect(session.playback).toBe('paused')
  })
})
