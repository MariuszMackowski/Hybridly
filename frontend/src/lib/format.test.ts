import { describe, expect, it } from 'vitest'
import { formatDistance, formatDuration, formatPace } from './format'

describe('format', () => {
  it('formatPace 5:49', () => {
    expect(formatPace(349)).toBe('5:49')
  })

  it('formatPace rounds seconds without producing :60', () => {
    expect(formatPace(359.7)).toBe('6:00')
  })

  it('formatPace null', () => {
    expect(formatPace(null)).toBe('–')
  })

  it('formatDuration h:mm:ss and mm:ss', () => {
    expect(formatDuration(1748)).toBe('29:08')
    expect(formatDuration(9897)).toBe('2:44:57')
  })

  it('formatDistance in km', () => {
    expect(formatDistance(5008.79)).toBe('5.01 km')
    expect(formatDistance(null)).toBe('–')
  })
})
