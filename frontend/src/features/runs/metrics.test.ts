import { describe, expect, it } from 'vitest'
import type { ActivityStreams } from '../../api/types'
import { availableMetrics, metricSeries } from './metrics'

const streams: ActivityStreams = {
  t: [0, 5, 10],
  hr: [140, 150, null],
  speed: [2.865, 0, 3.0],
  stride: [1.07, 1.1, 1.05],
  power: [229, 230, 231],
}

describe('run metrics', () => {
  it('pace converts speed to seconds per km and drops standstill', () => {
    const pace = metricSeries(streams, 'pace', true)
    expect(pace[0]).toBeCloseTo(349, 0)
    expect(pace[1]).toBeNull()
  })

  it('speed is km/h for non-runs', () => {
    expect(metricSeries(streams, 'pace', false)[2]).toBeCloseTo(10.8, 1)
  })

  it('availableMetrics lists only channels with data', () => {
    expect(availableMetrics(streams, true)).toEqual(['hr', 'pace', 'stride', 'power'])
  })

  it('stride passes through in metres', () => {
    expect(metricSeries(streams, 'stride', true)).toEqual([1.07, 1.1, 1.05])
  })
})
