import type { ExerciseInsight, WorkoutInsights } from '../../api/types'
import { kg } from '../../lib/format'
import { muscleLabel } from '../../lib/muscles'

export type InsightMode = 'best' | 'volume'

/** Whole number with thousands separators ("1,290"). */
const thousands = (v: number) => Math.round(v).toLocaleString('en-US')

/** Horizontal bars of effective volume per muscle (primary full, secondary half). */
export function MuscleVolumeCard({ muscles }: { muscles: WorkoutInsights['muscles'] }) {
  if (muscles.length === 0) return null
  const top = Math.max(1, muscles[0].volume_kg)
  return (
    <div className="card stack">
      <div className="row spread muted section-label">
        <span>Muscle engagement</span>
        <span>Effective volume</span>
      </div>
      {muscles.map((m) => (
        <div key={m.muscle} className="muscle-bar">
          <span>{muscleLabel(m.muscle)}</span>
          <span className="muscle-bar-track">
            <span className="muscle-bar-fill" style={{ width: `${(100 * m.volume_kg) / top}%` }} />
          </span>
          <strong>{thousands(m.volume_kg)} kg</strong>
        </div>
      ))}
    </div>
  )
}

/** "▲ +24% · 4 wks", "Same · 4 wks" or nothing without an earlier session. */
function Change({ pct, weeks }: { pct: number | null; weeks: number | null }) {
  if (pct === null || weeks === null) return null
  const when = ` · ${weeks} wk${weeks === 1 ? '' : 's'}`
  if (pct === 0) return <span className="muted">Same{when}</span>
  return (
    <span className={pct > 0 ? 'good' : 'bad'}>
      {pct > 0 ? `▲ +${pct}%` : `▼ ${pct}%`}
      <span className="muted">{when}</span>
    </span>
  )
}

/** Right-hand summary of an exercise: volume (or total reps) or best set, with change vs ~4 weeks ago. */
export function InsightSummary({ insight, mode }: { insight: ExerciseInsight | null; mode: InsightMode }) {
  if (!insight) return null
  const { best_set: best } = insight
  const main =
    mode === 'best' ? (
      best && (
        <>
          <strong>
            {kg(best.weight_kg)} × {best.reps}
          </strong>
          <span className="muted"> best set</span>
        </>
      )
    ) : insight.metric === 'reps' ? (
      <>
        <strong>{insight.total_reps} reps</strong>
        <span className="muted"> total</span>
      </>
    ) : (
      <>
        <strong>{thousands(insight.volume_kg)} kg</strong>
        <span className="muted"> volume</span>
      </>
    )
  const pct = mode === 'best' ? insight.best_change_pct : insight.volume_change_pct
  return (
    <div className="insight">
      <div>{main}</div>
      <Change pct={pct} weeks={insight.weeks_ago} />
    </div>
  )
}
