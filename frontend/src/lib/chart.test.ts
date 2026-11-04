import { describe, expect, it } from 'vitest'
import { clampTo, robustDomain, rollingMedian } from './chart'

describe('chart helpers', () => {
  it('rollingMedian removes single spikes', () => {
    expect(rollingMedian([300, 300, 900, 300, 300], 3)).toEqual([300, 300, 300, 300, 300])
  })

  it('rollingMedian keeps nulls where there is no data', () => {
    expect(rollingMedian([null, 300, null], 3)).toEqual([null, 300, null])
  })

  it('clampTo keeps every value inside the domain', () => {
    expect(clampTo([100, 300, 900, null], [250, 400])).toEqual([250, 300, 400, null])
  })

  it('robustDomain ignores outliers', () => {
    const values = [...Array(100).fill(330), 900, 120]
    const [lo, hi] = robustDomain(values)!
    expect(lo).toBeGreaterThan(200)
    expect(hi).toBeLessThan(500)
  })
})
