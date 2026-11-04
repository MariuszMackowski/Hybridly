import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ActivityStreams } from '../../api/types'
import { clampTo, robustDomain, rollingMedian } from '../../lib/chart'
import { formatDuration } from '../../lib/format'
import { availableMetrics, METRICS, metricSeries, type MetricDef, type MetricKey } from './metrics'

const STORAGE_KEY = 'hybridly.chartMetrics'
const DEFAULT: MetricKey[] = ['hr', 'pace']
const SMOOTH_POINTS = 7 // streams are 5 s apart → ~35 s rolling median

/** Selected metrics remembered between visits. */
function useSelection(): [MetricKey[], (key: MetricKey) => void] {
  const [selected, setSelected] = useState<MetricKey[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
      return Array.isArray(saved) ? saved : DEFAULT
    } catch {
      return DEFAULT
    }
  })
  const toggle = (key: MetricKey) => {
    const next = selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSelected(next)
  }
  return [selected, toggle]
}

/** One small chart; values smoothed and clamped so the line stays inside. */
function MetricChart(props: { def: MetricDef; t: number[]; values: (number | null)[]; isRun: boolean }) {
  const { def, isRun } = props
  const asSpeed = def.key === 'pace' && !isRun
  const smoothed = rollingMedian(props.values, SMOOTH_POINTS)
  const domain = robustDomain(smoothed)
  const values = domain ? clampTo(smoothed, domain) : smoothed
  const data = props.t.map((t, i) => ({ t, v: values[i] }))
  const format = asSpeed ? (v: number) => v.toFixed(1) : def.format
  const unit = asSpeed ? 'km/h' : def.unit
  const label = asSpeed ? 'Speed' : def.label
  return (
    <div className="metric-chart">
      <div className="metric-title" style={{ color: def.color }}>
        {label} <span className="muted">{unit}</span>
      </div>
      <ResponsiveContainer width="100%" height={130}>
        <LineChart data={data} syncId="run" margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#2a2f3a" vertical={false} />
          <XAxis dataKey="t" tickFormatter={(t) => formatDuration(t)} stroke="#8a90a0" fontSize={10} minTickGap={40} />
          <YAxis
            stroke={def.color}
            fontSize={10}
            width={44}
            reversed={def.reversed && isRun}
            domain={domain ?? ['dataMin', 'dataMax']}
            tickFormatter={(v) => format(Number(v))}
          />
          <Tooltip
            contentStyle={{ background: '#181b22', border: '1px solid #2a2f3a' }}
            labelFormatter={(t) => formatDuration(Number(t))}
            formatter={(value) => [`${format(Number(value))} ${unit}`, label]}
          />
          <Line dataKey="v" stroke={def.color} dot={false} strokeWidth={1.5} connectNulls isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Metric toggles plus one synchronized chart per selected metric. */
export default function RunCharts(props: { streams: ActivityStreams; isRun: boolean }) {
  const [selected, toggle] = useSelection()
  const available = METRICS.filter((m) => availableMetrics(props.streams, props.isRun).includes(m.key))
  if (available.length === 0) return null
  const shown = available.filter((m) => selected.includes(m.key))
  return (
    <div className="card chart-card stack">
      <div className="chips">
        {available.map((m) => {
          const on = selected.includes(m.key)
          return (
            <button
              key={m.key}
              className={`chip${on ? ' on' : ''}`}
              style={on ? { borderColor: m.color, color: m.color, background: 'transparent' } : undefined}
              onClick={() => toggle(m.key)}
            >
              {m.key === 'pace' && !props.isRun ? 'Speed' : m.label}
            </button>
          )
        })}
      </div>
      {shown.map((def) => (
        <MetricChart
          key={def.key}
          def={def}
          t={props.streams.t}
          values={metricSeries(props.streams, def.key, props.isRun)}
          isRun={props.isRun}
        />
      ))}
      {shown.length === 0 && <span className="muted">Pick a metric above.</span>}
    </div>
  )
}
