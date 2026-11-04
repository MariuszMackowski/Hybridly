import { Link } from 'react-router-dom'
import type { Comparison, PlanSession } from '../../api/types'
import { formatPace } from '../../lib/format'
import { paceRangeLabel, zoneBar } from '../../lib/plan'

const STATUS_CLASS = { in: 'good', faster: 'bad', slower: 'bad' } as const
const ZONE_COLOR = { below: '#38bdf8', in: '#22c55e', above: '#ef4444' } as const

/** Target line: distance, pace range, HR range, intervals. */
export function targets(session: PlanSession): string[] {
  const parts: string[] = []
  if (session.distance_km) parts.push(`${session.distance_km} km`)
  const pace = paceRangeLabel(session.pace_min_s, session.pace_max_s)
  if (pace) parts.push(pace)
  if (session.hr_min && session.hr_max) parts.push(`HR ${session.hr_min}–${session.hr_max}`)
  const iv = session.intervals
  if (iv) {
    const dist = iv.distance_m ? (iv.distance_m >= 1000 ? `${iv.distance_m / 1000} km` : `${iv.distance_m} m`) : ''
    parts.push(`${iv.reps}× ${dist}${iv.pace ? ` @ ${iv.pace.min}–${iv.pace.max}` : ''}${iv.recovery ? `, ${iv.recovery}` : ''}`)
  }
  return parts
}

/** Planned vs. done numbers for a matched run. */
export function ComparisonView({ comparison }: { comparison: Comparison }) {
  const bar = zoneBar(comparison.hr_below_pct, comparison.hr_in_pct, comparison.hr_above_pct)
  return (
    <div className="stack comparison">
      <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
        {comparison.distance_pct !== null && <span>Distance {comparison.distance_pct}%</span>}
        {comparison.pace_s !== null && (
          <span className={comparison.pace_status ? STATUS_CLASS[comparison.pace_status] : ''}>
            Pace {formatPace(comparison.pace_s)} /km{comparison.pace_status ? ` (${comparison.pace_status})` : ''}
          </span>
        )}
      </div>
      {bar && (
        <div className="stack" style={{ gap: 4 }}>
          <div className="zone-bar">
            {bar.map((s) => (
              <i key={s.key} style={{ width: `${s.pct}%`, background: ZONE_COLOR[s.key as keyof typeof ZONE_COLOR] }} />
            ))}
          </div>
          <span className="muted" style={{ fontSize: 12 }}>
            HR: {comparison.hr_in_pct}% in zone · {comparison.hr_above_pct}% above · {comparison.hr_below_pct}% below
          </span>
        </div>
      )}
      {comparison.interval_laps.length > 0 && (
        <table className="sets">
          <thead>
            <tr>
              <th>Lap</th>
              <th>m</th>
              <th>Pace</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {comparison.interval_laps.map((lap) => (
              <tr key={lap.index}>
                <td>{lap.index + 1}</td>
                <td>{Math.round(lap.distance_m)}</td>
                <td>{formatPace(lap.pace_s)}</td>
                <td className={lap.in_range ? 'good' : lap.in_range === false ? 'bad' : ''}>
                  {lap.in_range ? '✓' : lap.in_range === false ? '✗' : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/** Planned run card used on Today. */
export default function SessionCard({ session }: { session: PlanSession }) {
  return (
    <div className="card stack">
      <div className="row spread">
        <strong>🏃 {session.title}</strong>
        {session.activity_id !== null ? (
          <Link to={`/runs/${session.activity_id}`} className="badge badge-pr">
            done ›
          </Link>
        ) : (
          <span className="badge">{session.type}</span>
        )}
      </div>
      <span className="muted">{targets(session).join(' · ')}</span>
      {session.comparison && <ComparisonView comparison={session.comparison} />}
    </div>
  )
}
