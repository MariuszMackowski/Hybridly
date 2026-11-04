import { Link } from 'react-router-dom'
import { useRecovery } from '../../api/hooks'
import BodyMap from './BodyMap'

/** Today card: recovery % with a small muscle map; opens the Recovery page. */
export default function RecoveryCard() {
  const r = useRecovery().data
  if (!r) return null
  return (
    <Link to="/recovery" className="card row spread recovery-card">
      <div className="stack" style={{ gap: 4 }}>
        <span className="muted">Recovery</span>
        <span className="big-number">{r.recovery_pct}%</span>
        <span className="muted" style={{ fontSize: 12 }}>
          {r.hours_to_full ? `${r.hours_to_full} h to full` : 'Fully recovered'}
          {r.coros_pct !== null ? ` · COROS ${r.coros_pct}%` : ''}
        </span>
      </div>
      <BodyMap levels={r.muscles} size={120} />
    </Link>
  )
}
