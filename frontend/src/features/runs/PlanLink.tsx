import { useState } from 'react'
import { useLinkSession, useSessionsBetween } from '../../api/hooks'
import type { ActivityDetail } from '../../api/types'
import { ComparisonView, targets } from '../plan/SessionCard'
import { localDay } from '../history/weeks'

/** ISO day ± n. */
function shift(day: string, n: number): string {
  const d = new Date(`${day}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** Planned session of a run, with manual link / change / unlink. */
export default function PlanLink({ activity }: { activity: ActivityDetail }) {
  const [choosing, setChoosing] = useState(false)
  const day = localDay(activity.started_at)
  const candidates = useSessionsBetween(shift(day, -2), shift(day, 2), choosing)
  const link = useLinkSession()
  const plan = activity.plan
  if (activity.sport !== 'run') return null

  /** Attach this run to a session (or detach from the current one). */
  const choose = (sessionId: number, activityId: number | null) =>
    link.mutate({ sessionId, activityId }, { onSuccess: () => setChoosing(false) })

  return (
    <div className="card stack">
      {plan ? (
        <>
          <div className="row spread">
            <strong>Plan: {plan.title}</strong>
            <span className="muted">{plan.date}</span>
          </div>
          <span className="muted">{targets(plan).join(' · ')}</span>
          {plan.comparison && <ComparisonView comparison={plan.comparison} />}
        </>
      ) : (
        <span className="muted">Not linked to a planned run.</span>
      )}
      {link.isError && <div className="banner">{link.error.message}</div>}
      {!choosing ? (
        <div className="row">
          <button className="btn-small" onClick={() => setChoosing(true)}>
            {plan ? 'Change planned run' : 'Link to planned run'}
          </button>
          {plan && (
            <button className="btn-small btn-danger" onClick={() => choose(plan.id, null)}>
              Unlink
            </button>
          )}
        </div>
      ) : (
        <div className="stack">
          {(candidates.data ?? []).map((s) => (
            <button
              key={s.id}
              className={`btn-block list-item${s.id === plan?.id ? ' btn-primary' : ''}`}
              onClick={() => choose(s.id, activity.id)}
            >
              {s.date} · {s.title}
              {s.activity_id !== null && s.activity_id !== activity.id ? ' (has another run)' : ''}
            </button>
          ))}
          {candidates.data?.length === 0 && <span className="muted">No planned runs within ±2 days.</span>}
          <button className="btn-small" onClick={() => setChoosing(false)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}
