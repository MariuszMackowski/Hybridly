import { Link } from 'react-router-dom'
import { useRecords } from '../../api/hooks'
import { formatDuration, formatPace } from '../../lib/format'
import BodyweightCard from '../progress/BodyweightCard'

const LABELS: Record<string, string> = {
  '100m': '100 m',
  '400m': '400 m',
  '1k': '1 km',
  '5k': '5 km',
  '10k': '10 km',
  half: 'Half marathon',
  marathon: 'Marathon',
}
const PREDICTED = ['5k', '10k', 'half', 'marathon']

/** Race predictor from COROS and best efforts across all runs. */
export default function RecordsPage() {
  const query = useRecords()
  const r = query.data
  if (query.isError) return <div className="page banner">{query.error.message}</div>
  if (!r) return <div className="page muted">Loading…</div>
  const p = r.predictor
  const distance = Object.fromEntries(r.bests.map((b) => [b.key, b.distance_m]))
  return (
    <div className="page stack">
      <h1>Records</h1>
      <div className="card stack">
        <div className="row spread">
          <strong>Race predictor</strong>
          {p && <span className="muted">COROS · {p.day}</span>}
        </div>
        {p ? (
          <>
            <table className="sets">
              <tbody>
                {PREDICTED.filter((k) => p.predictions[k]).map((k) => (
                  <tr key={k}>
                    <td>{LABELS[k]}</td>
                    <td>
                      <strong>{formatDuration(p.predictions[k])}</strong>
                    </td>
                    <td className="muted">{formatPace((p.predictions[k] * 1000) / distance[k])} /km</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <span className="muted">
              {[
                p.vo2max && `VO2max ${p.vo2max}`,
                p.threshold_pace_s && `Threshold ${formatPace(p.threshold_pace_s)} /km`,
                p.running_level && `Running level ${p.running_level}`,
              ]
                .filter(Boolean)
                .join(' · ')}
            </span>
          </>
        ) : (
          <span className="muted">No prediction yet — it comes with the next COROS sync.</span>
        )}
      </div>
      <div className="card stack">
        <strong>Best efforts</strong>
        <table className="sets">
          <tbody>
            {r.bests.map((b) => (
              <tr key={b.key}>
                <td>{LABELS[b.key] ?? b.key}</td>
                <td>
                  <strong>{b.seconds === null ? '–' : formatDuration(b.seconds)}</strong>
                </td>
                <td className="muted">
                  {b.seconds === null ? '' : `${formatPace((b.seconds * 1000) / b.distance_m)} /km`}
                </td>
                <td>{b.activity_id !== null && <Link to={`/runs/${b.activity_id}`}>{b.day}</Link>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <BodyweightCard />
    </div>
  )
}
