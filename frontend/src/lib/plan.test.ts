import { describe, expect, it } from 'vitest'
import { paceRangeLabel, sessionStatus, zoneBar } from './plan'

describe('plan helpers', () => {
  it('paceRangeLabel shows range or single pace', () => {
    expect(paceRangeLabel(340, 380)).toBe('5:40–6:20 /km')
    expect(paceRangeLabel(298, 298)).toBe('4:58 /km')
    expect(paceRangeLabel(null, null)).toBeNull()
  })

  it('zoneBar returns widths that add up to 100', () => {
    expect(zoneBar(25, 50, 25)).toEqual([
      { key: 'below', pct: 25 },
      { key: 'in', pct: 50 },
      { key: 'above', pct: 25 },
    ])
    expect(zoneBar(null, null, null)).toBeNull()
  })

  it('sessionStatus: done, missed or upcoming', () => {
    expect(sessionStatus({ date: '2026-11-02', activity_id: 5 }, '2026-11-04')).toBe('done')
    expect(sessionStatus({ date: '2026-11-02', activity_id: null }, '2026-11-04')).toBe('missed')
    expect(sessionStatus({ date: '2026-11-04', activity_id: null }, '2026-11-04')).toBe('today')
    expect(sessionStatus({ date: '2026-11-06', activity_id: null }, '2026-11-04')).toBe('upcoming')
  })
})
