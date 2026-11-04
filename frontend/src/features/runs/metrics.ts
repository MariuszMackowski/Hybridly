import type { ActivityStreams } from '../../api/types'
import { formatPace } from '../../lib/format'

export type MetricKey = 'hr' | 'pace' | 'cad' | 'stride' | 'power' | 'gct' | 'vo' | 'alt'

export type MetricDef = {
  key: MetricKey
  label: string
  unit: string
  color: string
  /** Pace axis is reversed so faster sits higher. */
  reversed?: boolean
  format: (v: number) => string
}

const SLOWEST_PACE_S = 900 // standing still is clipped to 15:00/km

export const METRICS: MetricDef[] = [
  { key: 'hr', label: 'HR', unit: 'bpm', color: '#ef4444', format: (v) => v.toFixed(0) },
  { key: 'pace', label: 'Pace', unit: '/km', color: '#ff7a1a', reversed: true, format: (v) => formatPace(v) },
  { key: 'cad', label: 'Cadence', unit: 'spm', color: '#38bdf8', format: (v) => v.toFixed(0) },
  { key: 'stride', label: 'Stride', unit: 'm', color: '#a78bfa', format: (v) => v.toFixed(2) },
  { key: 'power', label: 'Power', unit: 'W', color: '#facc15', format: (v) => v.toFixed(0) },
  { key: 'gct', label: 'GCT', unit: 'ms', color: '#34d399', format: (v) => v.toFixed(0) },
  { key: 'vo', label: 'Vert. osc.', unit: 'cm', color: '#f472b6', format: (v) => v.toFixed(1) },
  { key: 'alt', label: 'Elevation', unit: 'm', color: '#94a3b8', format: (v) => v.toFixed(0) },
]

/** Values of one metric aligned with streams.t (pace in s/km for runs, km/h otherwise). */
export function metricSeries(streams: ActivityStreams, key: MetricKey, isRun: boolean): (number | null)[] {
  if (key === 'pace') {
    return (streams.speed ?? streams.t.map(() => null)).map((s) => {
      if (s === null) return null
      if (!isRun) return s * 3.6
      return s > 0 ? Math.min(1000 / s, SLOWEST_PACE_S) : null
    })
  }
  return streams[key] ?? streams.t.map(() => null)
}

/** Metrics that have at least one value in this activity, in display order. */
export function availableMetrics(streams: ActivityStreams, isRun: boolean): MetricKey[] {
  return METRICS.filter((m) => metricSeries(streams, m.key, isRun).some((v) => v !== null)).map((m) => m.key)
}
