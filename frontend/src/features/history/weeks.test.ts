import { describe, expect, it } from 'vitest'
import type { HistoryItem } from '../../api/types'
import { groupByWeek, isoWeek, localDay, monthGrid } from './weeks'

function item(started_at: string, sport: string, distance_m: number | null = null): HistoryItem {
  return {
    kind: sport === 'gym' ? 'workout' : 'activity', id: 1, started_at, title: null, sport,
    duration_s: null, distance_m, avg_pace_s_per_km: null, avg_speed: null, avg_hr: null,
    training_load: null, exercise_count: null, set_count: null, pr_count: null,
  }
}

describe('weeks', () => {
  it('localDay uses Warsaw time', () => {
    expect(localDay('2026-11-01T23:30:00Z')).toBe('2026-11-02')
  })

  it('isoWeek numbers Monday-based weeks', () => {
    expect(isoWeek('2026-11-02')).toEqual({ year: 2026, week: 45, monday: '2026-11-02' })
    expect(isoWeek('2026-11-08')).toEqual({ year: 2026, week: 45, monday: '2026-11-02' })
    expect(isoWeek('2027-01-01').week).toBe(53)
  })

  it('groupByWeek keeps order and sums the week', () => {
    const groups = groupByWeek([
      item('2026-11-04T07:00:00Z', 'gym'),
      item('2026-11-03T07:00:00Z', 'run', 5000),
      item('2026-11-02T07:00:00Z', 'walk', 3000),
      item('2026-10-30T07:00:00Z', 'run', 8000),
    ])
    expect(groups.map((g) => g.items.length)).toEqual([3, 1])
    expect(groups[0]).toMatchObject({ week: 45, gym: 1, run: 1, walk: 1, km: 8 })
    expect(groups[1]).toMatchObject({ week: 44, run: 1, km: 8 })
  })

  it('monthGrid pads to Monday-first weeks', () => {
    const grid = monthGrid(2026, 11)
    expect(grid[0].slice(0, 7)).toEqual([null, null, null, null, null, null, '2026-11-01'])
    expect(grid.at(-1)).toContain('2026-11-30')
    expect(grid.every((w) => w.length === 7)).toBe(true)
  })
})
