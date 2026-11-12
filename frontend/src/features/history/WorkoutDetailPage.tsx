import { useNavigate, useParams } from 'react-router-dom'
import { useDeleteWorkout, useWorkout } from '../../api/hooks'
import { dateTime, durationMin, kg } from '../../lib/format'

export default function WorkoutDetailPage() {
  const id = Number(useParams().id)
  const query = useWorkout(id)
  const remove = useDeleteWorkout()
  const navigate = useNavigate()
  const w = query.data

  if (query.isError) return <div className="page banner">{query.error.message}</div>
  if (!w) return <div className="page muted">Loading…</div>

  const minutes = durationMin(w.started_at, w.ended_at)
  /** Delete after confirmation and go back to the list. */
  const onDelete = () => {
    if (!window.confirm('Delete this workout?')) return
    remove.mutate(w.id, { onSuccess: () => navigate('/history', { replace: true }) })
  }

  return (
    <div className="page stack">
      <button className="btn-small" style={{ alignSelf: 'flex-start' }} onClick={() => navigate('/history')}>
        ‹ History
      </button>
      <div>
        <h1>{w.title ?? 'Workout'}</h1>
        <div className="muted">
          {dateTime(w.started_at)}
          {minutes !== null && ` · ${minutes} min`}
          {w.source === 'gravitus' && ' · imported from Gravitus'}
        </div>
      </div>
      {w.exercises.map((ex, i) => {
        let working = 0
        return (
          <div key={`${ex.exercise_id}-${i}`} className="card">
            <div className="row spread">
              <strong>{ex.exercise_name}</strong>
              {ex.grip && <span className="muted"> · {ex.grip}</span>}
              {ex.per_side && <span className="badge">per side</span>}
            </div>
            <table className="sets">
              <thead>
                <tr>
                  <th>#</th>
                  <th>kg</th>
                  <th>{ex.sets.some((s) => s.distance_m !== null) ? 'm' : ex.sets.some((s) => s.seconds !== null) ? 's' : 'reps'}</th>
                  <th>e1RM</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {ex.sets.map((s) => (
                  <tr key={s.set_index} className={s.is_warmup ? 'muted' : ''}>
                    <td>{s.is_warmup ? 'W' : ++working}</td>
                    <td>{kg(s.weight_kg)}</td>
                    <td>{s.reps ?? s.seconds ?? (s.distance_m !== null ? kg(s.distance_m) : '–')}</td>
                    <td>{s.e1rm_kg === null ? '–' : kg(s.e1rm_kg)}</td>
                    <td>{s.is_pr && <span className="badge badge-pr">PR</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
      <button className="btn-danger btn-block" disabled={remove.isPending} onClick={onDelete}>
        Delete workout
      </button>
    </div>
  )
}
