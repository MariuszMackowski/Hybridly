import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useBodyweight } from '../../api/hooks'
import { AXIS_PROPS, shortDay, TOOLTIP_STYLE } from '../../lib/chart'
import { kg } from '../../lib/format'

/** Bodyweight over time (entries come from Settings). */
export default function BodyweightCard() {
  const entries = [...(useBodyweight().data ?? [])].reverse() // API returns newest first
  if (entries.length === 0) return null
  const multiYear = entries[0].day.slice(0, 4) !== entries.at(-1)!.day.slice(0, 4)
  return (
    <div className="card">
      <div className="row spread">
        <strong>Bodyweight</strong>
        <span>
          <strong>{kg(entries.at(-1)!.kg)} kg</strong>
          <span className="muted"> · {shortDay(entries.at(-1)!.day, true)}</span>
        </span>
      </div>
      {entries.length > 1 && (
        <ResponsiveContainer width="100%" height={170}>
          <LineChart data={entries} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="day" {...AXIS_PROPS} tickFormatter={(d: string) => shortDay(d, multiYear)} minTickGap={24} />
            <YAxis {...AXIS_PROPS} domain={['auto', 'auto']} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => shortDay(String(d), true)} />
            <Line dataKey="kg" name="kg" stroke="#ff7a1a" dot={entries.length < 30} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
