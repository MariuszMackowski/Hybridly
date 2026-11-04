import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useHistory } from '../../api/hooks'
import type { HistoryItem, HistoryKind } from '../../api/types'
import { dateTime, formatDistance, formatDuration, speedLabel } from '../../lib/format'
import UploadFit from '../runs/UploadFit'

const FILTERS: { label: string; kind: HistoryKind }[] = [
  { label: 'All', kind: 'all' },
  { label: 'Gym', kind: 'gym' },
  { label: 'Run', kind: 'run' },
  { label: 'Walk', kind: 'walk' },
  { label: 'Other', kind: 'other' },
]
const SPORT_ICON: Record<string, string> = { gym: '🏋️', run: '🏃', walk: '🚶', basketball: '🏀' }

/** Strength workout row. */
function WorkoutRow({ item }: { item: HistoryItem }) {
  return (
    <Link to={`/history/${item.id}`} className="card stack history-item">
      <div className="row spread">
        <strong>
          {SPORT_ICON.gym} {item.title ?? 'Workout'}
        </strong>
        {!!item.pr_count && <span className="badge badge-pr">{item.pr_count} PR</span>}
      </div>
      <span className="muted">
        {dateTime(item.started_at)}
        {item.duration_s !== null && ` · ${Math.round(item.duration_s / 60)} min`} · {item.exercise_count}{' '}
        exercises · {item.set_count} sets
      </span>
    </Link>
  )
}

/** Cardio activity row. */
function ActivityRow({ item }: { item: HistoryItem }) {
  return (
    <Link to={`/runs/${item.id}`} className="card stack history-item">
      <div className="row spread">
        <strong>
          {SPORT_ICON[item.sport] ?? '🏅'} {item.title ?? item.sport}
        </strong>
        {item.training_load !== null && <span className="badge badge-pr">TL {item.training_load}</span>}
      </div>
      <span className="muted">{dateTime(item.started_at)}</span>
      <span>
        {formatDistance(item.distance_m)} · {formatDuration(item.duration_s ?? 0)} · {speedLabel(item)}
        {item.avg_hr !== null && ` · ${item.avg_hr} bpm`}
      </span>
    </Link>
  )
}

export default function HistoryPage() {
  const [kind, setKind] = useState<HistoryKind>('all')
  const query = useHistory(kind)
  const items = query.data?.pages.flat() ?? []
  return (
    <div className="page stack">
      <div className="row spread">
        <h1>History</h1>
        <UploadFit />
      </div>
      <div className="chips">
        {FILTERS.map((f) => (
          <button key={f.kind} className={`chip${f.kind === kind ? ' on' : ''}`} onClick={() => setKind(f.kind)}>
            {f.label}
          </button>
        ))}
      </div>
      {query.isError && <div className="banner">{query.error.message}</div>}
      {items.map((item) =>
        item.kind === 'workout' ? (
          <WorkoutRow key={`w${item.id}`} item={item} />
        ) : (
          <ActivityRow key={`a${item.id}`} item={item} />
        ),
      )}
      {query.hasNextPage && (
        <button className="btn-block" disabled={query.isFetchingNextPage} onClick={() => query.fetchNextPage()}>
          {query.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
      {!query.isLoading && items.length === 0 && <p className="muted">Nothing here yet.</p>}
    </div>
  )
}
