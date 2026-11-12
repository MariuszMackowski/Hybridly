import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Bar, BarChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useExerciseProgress, useExercises } from '../../api/hooks'
import BackButton from '../../components/BackButton'
import { AXIS_PROPS, shortDay, TOOLTIP_STYLE } from '../../lib/chart'
import { localDay } from '../history/weeks'
import { MaxesCard, RecentSessions, RecordsCard, ToBeat } from './ExerciseStats'

const RANGES = { '3M': 91, '1Y': 365, All: null } as const
type Range = keyof typeof RANGES

/** "YYYY-MM-DD" of the day `days` ago, or null for no limit. */
function since(days: number | null): string | null {
  if (days === null) return null
  return new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10)
}

/** Toggle chips where exactly one option is active. */
function Chips<T extends string>(props: { options: readonly T[]; value: T; label?: (v: T) => string; onChange: (v: T) => void }) {
  return (
    <div className="chips">
      {props.options.map((o) => (
        <button key={o} className={`chip${props.value === o ? ' on' : ''}`} onClick={() => props.onChange(o)}>
          {props.label ? props.label(o) : o}
        </button>
      ))}
    </div>
  )
}

/** e1RM, top set and weekly volume of one exercise over time, filterable by grip and range. */
export default function ExerciseProgressPage() {
  const id = Number(useParams().id)
  const [grip, setGrip] = useState<string>('')
  const [range, setRange] = useState<Range>('1Y')
  const exercise = useExercises(true).data?.find((e) => e.id === id)
  const query = useExerciseProgress(id, grip || null)
  const data = query.data
  const from = since(RANGES[range])
  const sessions = (data?.sessions ?? [])
    .map((s) => ({ ...s, day: localDay(s.started_at) }))
    .filter((s) => !from || s.day >= from)
  const weeks = (data?.weeks ?? []).filter((w) => !from || w.week_start >= from)
  const multiYear = sessions.length > 0 && sessions[0].day.slice(0, 4) !== sessions.at(-1)!.day.slice(0, 4)

  return (
    <div className="page stack">
      <BackButton to="/exercises" label="Exercises" />
      <h1>{exercise?.name ?? 'Progress'}</h1>
      {query.isError && <div className="banner">{query.error.message}</div>}
      {data && data.grips.length > 0 && (
        <Chips options={['', ...data.grips]} value={grip} label={(g) => g || 'All grips'} onChange={setGrip} />
      )}
      <Chips options={Object.keys(RANGES) as Range[]} value={range} onChange={setRange} />
      {data && sessions.length === 0 && <div className="muted">No rep-based working sets in this range.</div>}
      {data && <ToBeat toBeat={data.to_beat} />}
      {sessions.length > 0 && (
        <div className="card">
          <strong>Estimated 1RM & top set</strong>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={sessions} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="day" {...AXIS_PROPS} tickFormatter={(d: string) => shortDay(d, multiYear)} minTickGap={24} />
              <YAxis {...AXIS_PROPS} domain={['auto', 'auto']} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => shortDay(String(d), true)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line dataKey="best_e1rm_kg" name="e1RM" stroke="#ff7a1a" dot={false} connectNulls isAnimationActive={false} />
              <Line dataKey="top_weight_kg" name="Top set kg" stroke="#38bdf8" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {data && <RecentSessions sessions={data.recent} />}
      {data && <RecordsCard records={data.records} />}
      {data && <MaxesCard maxes={data.maxes} />}
      {weeks.length > 0 && (
        <div className="card">
          <strong>Weekly volume (kg × reps)</strong>
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={weeks} margin={{ top: 8, right: 4, left: -12, bottom: 0 }}>
              <XAxis dataKey="week_start" {...AXIS_PROPS} tickFormatter={(d: string) => shortDay(d, multiYear)} minTickGap={24} />
              <YAxis {...AXIS_PROPS} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={false} labelFormatter={(d) => `Week of ${shortDay(String(d), true)}`} />
              <Bar dataKey="volume_kg" name="Volume" fill="#ff7a1a" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
