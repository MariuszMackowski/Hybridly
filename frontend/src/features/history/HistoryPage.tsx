import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useHistory } from '../../api/hooks'
import type { HistoryItem, HistoryKind } from '../../api/types'
import { dateTime, formatDistance, formatDuration, speedLabel } from '../../lib/format'
import UploadFit from '../runs/UploadFit'
import Calendar from './Calendar'
import { groupByWeek, type WeekGroup } from './weeks'

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
        <span className="row">
          {!!item.pr_count && <span className="badge badge-pr">{item.pr_count} PR</span>}
          {item.training_load !== null && <span className="badge badge-pr">TL {item.training_load}</span>}
        </span>
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

/** "2–8 Nov" range label of a week. */
function range(group: WeekGroup): string {
  const fmt = (d: string, month: boolean) =>
    new Date(`${d}T12:00:00Z`).toLocaleDateString('en-GB', month ? { day: 'numeric', month: 'short' } : { day: 'numeric' })
  const sameMonth = group.monday.slice(5, 7) === group.sunday.slice(5, 7)
  return `${fmt(group.monday, !sameMonth)}–${fmt(group.sunday, true)}`
}

/** Divider with the week's totals. */
function WeekHeader({ group }: { group: WeekGroup }) {
  const parts = [
    group.gym && `${group.gym}× gym`,
    group.run && `${group.run}× run`,
    group.walk && `${group.walk}× walk`,
    group.other && `${group.other}× other`,
    group.km && `${group.km.toFixed(1)} km`,
  ].filter(Boolean)
  return (
    <div className="week-header">
      <strong>Week {group.week}</strong> <span className="muted">· {range(group)}</span>
      <div className="muted">{parts.join(' · ')}</div>
    </div>
  )
}

/** One history row of either kind. */
function Row({ item }: { item: HistoryItem }) {
  return item.kind === 'workout' ? <WorkoutRow item={item} /> : <ActivityRow item={item} />
}

export default function HistoryPage() {
  const [kind, setKind] = useState<HistoryKind>('all')
  const [day, setDay] = useState<string | null>(null)
  const query = useHistory(kind, day)
  const items = query.data?.pages.flat() ?? []
  return (
    <div className="page stack">
      <div className="row spread">
        <h1>History</h1>
        <UploadFit />
      </div>
      <Calendar selected={day} onSelect={setDay} />
      {day && (
        <div className="row spread">
          <strong>
            {new Date(`${day}T12:00:00Z`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}
          </strong>
          <button className="btn-small" onClick={() => setDay(null)}>
            Show all
          </button>
        </div>
      )}
      <div className="chips">
        {FILTERS.map((f) => (
          <button key={f.kind} className={`chip${f.kind === kind ? ' on' : ''}`} onClick={() => setKind(f.kind)}>
            {f.label}
          </button>
        ))}
      </div>
      {query.isError && <div className="banner">{query.error.message}</div>}
      {day
        ? items.map((item) => <Row key={`${item.kind}${item.id}`} item={item} />)
        : groupByWeek(items).map((group) => (
            <div key={group.key} className="stack">
              <WeekHeader group={group} />
              {group.items.map((item) => (
                <Row key={`${item.kind}${item.id}`} item={item} />
              ))}
            </div>
          ))}
      {query.hasNextPage && (
        <button className="btn-block" disabled={query.isFetchingNextPage} onClick={() => query.fetchNextPage()}>
          {query.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
      {!query.isLoading && items.length === 0 && <p className="muted">{day ? 'No training this day.' : 'Nothing here yet.'}</p>}
    </div>
  )
}
