import { describe, expect, it } from 'vitest'
import { byFatigue, fatigueColor, topMuscles } from './muscles'

describe('muscle colours', () => {
  it('fatigueColor goes white → yellow → red', () => {
    expect(fatigueColor(0)).toBe('rgb(230, 232, 236)')
    expect(fatigueColor(0.5)).toBe('rgb(250, 204, 21)')
    expect(fatigueColor(1)).toBe('rgb(239, 68, 68)')
    expect(fatigueColor(2)).toBe('rgb(239, 68, 68)')
  })

  it('topMuscles sorts by fatigue and drops near-zero', () => {
    expect(topMuscles({ chest: 0.2, glutes: 0.8, abs: 0.01 }, 5)).toEqual([
      ['glutes', 0.8],
      ['chest', 0.2],
    ])
  })

  it('byFatigue keeps every muscle, most fatigued first', () => {
    expect(byFatigue({ chest: 0.2, glutes: 0.8, abs: 0.01 })).toEqual([
      ['glutes', 0.8],
      ['chest', 0.2],
      ['abs', 0.01],
    ])
  })
})
