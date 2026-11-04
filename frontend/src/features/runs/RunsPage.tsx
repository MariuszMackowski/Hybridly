import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useActivities } from '../../api/hooks'
import type { ActivitySummary } from '../../api/types'
import { dateTime, formatDistance, formatDuration, formatPace } from '../../lib/format'
import UploadFit from './UploadFit'

const FILTERS: { label: string; sport: string | null }[] = [
  { label: 'All', sport: null },
  { label: 'Run', sport: 'run' },
  { label: 'Walk', sport: 'walk' },
  { label: 'Other', sport: 'other' },
]

/** Pace for runs, km/h for everything else. */
export function speedLabel(a: Pick<ActivitySummary, 'sport' | 'avg_pace_s_per_km' | 'avg_speed'>): string {
  if (a.sport === 'run') return `${formatPace(a.avg_pace_s_per_km)} /km`
  return a.avg_speed ? `${(a.avg_speed * 3.6).toFixed(1)} km/h` : '–'
}

export default function RunsPage() {
  const [sport, setSport] = useState<string | null>(null)
  const activities = useActivities(sport)
  return (
    <div className="page stack">
      <div className="row spread">
        <h1>Runs</h1>
        <UploadFit />
      </div>
      <div className="chips">
        {FILTERS.map((f) => (
          <button key={f.label} className={`chip${f.sport === sport ? ' on' : ''}`} onClick={() => setSport(f.sport)}>
            {f.label}
          </button>
        ))}
      </div>
      {activities.isError && <div className="banner">{activities.error.message}</div>}
      {(activities.data ?? []).map((a) => (
        <Link key={a.id} to={`/runs/${a.id}`} className="card stack">
          <div className="row spread">
            <strong>{a.name ?? a.sport}</strong>
            {a.training_load !== null && <span className="badge badge-pr">TL {a.training_load}</span>}
          </div>
          <span className="muted">{dateTime(a.started_at)}</span>
          <span>
            {formatDistance(a.distance_m)} · {formatDuration(a.duration_s)} · {speedLabel(a)}
            {a.avg_hr !== null && ` · ${a.avg_hr} bpm`}
          </span>
        </Link>
      ))}
      {!activities.isLoading && activities.data?.length === 0 && (
        <p className="muted">No activities yet — connect COROS in Settings or upload a FIT file.</p>
      )}
    </div>
  )
}
