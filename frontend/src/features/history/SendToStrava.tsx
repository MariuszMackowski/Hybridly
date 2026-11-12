import { Link } from 'react-router-dom'
import { useSendToStrava, useStravaStatus } from '../../api/hooks'

const activityUrl = (id: number) => `https://www.strava.com/activities/${id}`

/** "Send to Strava" (or "Update on Strava" once sent) with the outcome and a link to the activity. */
export default function SendToStrava({ workoutId, sentTo }: { workoutId: number; sentTo: number | null }) {
  const status = useStravaStatus().data
  const send = useSendToStrava(workoutId)
  if (!status) return null
  if (!status.connected)
    return (
      <Link to="/settings" className="muted">
        Connect Strava in Settings to send this workout.
      </Link>
    )
  const result = send.data
  return (
    <div className="stack">
      {send.isError && <div className="banner">{send.error.message}</div>}
      <button className="btn-block" disabled={send.isPending} onClick={() => send.mutate()}>
        {send.isPending ? 'Sending…' : sentTo ? 'Update on Strava' : 'Send to Strava'}
      </button>
      {result ? (
        <a className="muted" href={result.url} target="_blank" rel="noopener">
          {result.action === 'updated' ? 'Added to your watch activity' : 'Created a Weight Training activity'} · open on
          Strava ›
        </a>
      ) : (
        sentTo && (
          <a className="muted" href={activityUrl(sentTo)} target="_blank" rel="noopener">
            Sent ✓ · open on Strava ›
          </a>
        )
      )}
    </div>
  )
}
