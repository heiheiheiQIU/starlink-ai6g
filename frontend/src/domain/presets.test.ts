import { describe, expect, it } from 'vitest'

import { POLICY_PAIRS, SCENARIO_PRESETS, makeRunRequest } from './presets'

describe('scenario presets', () => {
  it('ships three frozen presets with stripped actions', () => {
    expect(SCENARIO_PRESETS).toHaveLength(3)
    for (const preset of SCENARIO_PRESETS) {
      expect(preset.config.actions).toEqual([])
      expect(preset.config.scenario).toBeTruthy()
      expect(preset.config.evaluation_end_s).toBeGreaterThan(0)
    }
  })

  it('builds valid run requests for both policy pairs', () => {
    const request = makeRunRequest(SCENARIO_PRESETS[0], 'edf/learned', 42)
    expect(request.schema_version).toBe('1.0')
    expect(request.policy_ids).toEqual(['edf', 'learned'])
    expect(request.seed).toBe(42)
    expect(request.config.actions).toEqual([])
  })

  it('exposes the two supported policy pairs', () => {
    expect(POLICY_PAIRS.map((item) => item.id)).toEqual(['edf/value', 'edf/learned'])
  })
})
