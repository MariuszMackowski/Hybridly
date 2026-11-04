import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ActivityStreams } from '../../api/types'
import { clampTo, robustDomain, rollingMedian } from '../../lib/chart'
import { formatDuration, formatPace } from '../../lib/format'

const HR_COLOR = '#ef4444'
const PACE_COLOR = '#ff7a1a'
const SLOWEST_PACE_S = 900 // clip standing still to 15:00/km so the axis stays readable
const SMOOTH_POINTS = 7 // streams are 5 s apart → ~35 s rolling median

/** Chart rows: time, HR and pace (s/km) for runs or speed (km/h) otherwise. */
function rows(streams: ActivityStreams, isRun: boolean) {
  return streams.t.map((t, i) => {
    const speed = streams.speed?.[i] ?? null
    const pace = speed && speed > 0 ? Math.min(1000 / speed, SLOWEST_PACE_S) : null
    return {
      t,
      hr: streams.hr?.[i] ?? null,
      pace: isRun ? pace : speed !== null ? speed * 3.6 : null,
    }
  })
}

/** HR and pace over time; pace axis reversed so faster is higher. */
export default function RunCharts(props: { streams: ActivityStreams; isRun: boolean }) {
  const raw = rows(props.streams, props.isRun)
  const smoothed = rollingMedian(raw.map((d) => d.pace), SMOOTH_POINTS)
  const paceDomain = robustDomain(smoothed)
  const pace = paceDomain ? clampTo(smoothed, paceDomain) : smoothed
  const data = raw.map((d, i) => ({ ...d, pace: pace[i] }))
  const hasHr = data.some((d) => d.hr !== null)
  const hasPace = data.some((d) => d.pace !== null)
  if (!hasHr && !hasPace) return null
  return (
    <div className="card chart-card">
      <div className="row muted chart-legend">
        {hasHr && <span style={{ color: HR_COLOR }}>● HR</span>}
        {hasPace && <span style={{ color: PACE_COLOR }}>● {props.isRun ? 'Pace' : 'Speed'}</span>}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#2a2f3a" vertical={false} />
          <XAxis dataKey="t" tickFormatter={(t) => formatDuration(t)} stroke="#8a90a0" fontSize={11} minTickGap={40} />
          {hasHr && <YAxis yAxisId="hr" stroke={HR_COLOR} fontSize={11} domain={['dataMin - 5', 'dataMax + 5']} />}
          {hasPace && (
            <YAxis
              yAxisId="pace"
              orientation="right"
              stroke={PACE_COLOR}
              fontSize={11}
              reversed={props.isRun}
              domain={paceDomain ?? ['dataMin', 'dataMax']}
              tickFormatter={(v) => (props.isRun ? formatPace(v) : v.toFixed(0))}
            />
          )}
          <Tooltip
            contentStyle={{ background: '#181b22', border: '1px solid #2a2f3a' }}
            labelFormatter={(t) => formatDuration(Number(t))}
            formatter={(value, name) =>
              name === 'pace' && props.isRun ? [`${formatPace(Number(value))} /km`, 'Pace'] : [String(value), String(name)]
            }
          />
          {hasHr && <Line yAxisId="hr" dataKey="hr" stroke={HR_COLOR} dot={false} strokeWidth={1.5} connectNulls />}
          {hasPace && <Line yAxisId="pace" dataKey="pace" stroke={PACE_COLOR} dot={false} strokeWidth={1.5} connectNulls />}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
