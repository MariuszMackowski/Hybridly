import { Link } from 'react-router-dom'
import { useWorkouts } from '../../api/hooks'
import { dateTime, durationMin } from '../../lib/format'

export default function HistoryPage() {
  const query = useWorkouts()
  const items = query.data?.pages.flat() ?? []
  return (
    <div className="page stack">
      <h1>History</h1>
      {query.isError && <div className="banner">{query.error.message}</div>}
      {items.map((w) => {
        const minutes = durationMin(w.started_at, w.ended_at)
        return (
          <Link key={w.id} to={`/history/${w.id}`} className="card stack history-item">
            <div className="row spread">
              <strong>{w.title ?? w.template_name ?? 'Workout'}</strong>
              {w.pr_count > 0 && <span className="badge badge-pr">{w.pr_count} PR</span>}
            </div>
            <span className="muted">
              {dateTime(w.started_at)}
              {minutes !== null && ` · ${minutes} min`} · {w.exercise_count} exercises · {w.set_count} sets
            </span>
          </Link>
        )
      })}
      {query.hasNextPage && (
        <button className="btn-block" disabled={query.isFetchingNextPage} onClick={() => query.fetchNextPage()}>
          {query.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
      {!query.isLoading && items.length === 0 && <p className="muted">No workouts yet.</p>}
    </div>
  )
}
