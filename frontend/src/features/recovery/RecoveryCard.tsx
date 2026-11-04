import { Link } from 'react-router-dom'
import { useRecovery } from '../../api/hooks'
import { fatigueColor, muscleLabel, topMuscles } from '../../lib/muscles'
import BodyMap from './BodyMap'

/** Full recovery view for Today: %, big front/back map, legend and most fatigued muscles. */
export default function RecoveryCard() {
  const r = useRecovery().data
  if (!r) return null
  const top = topMuscles(r.muscles, 6)
  return (
    <div className="card stack">
      <div className="row spread">
        <div>
          <span className="muted">Recovery</span>
          <div className="big-number">{r.recovery_pct}%</div>
          <span className="muted" style={{ fontSize: 12 }}>
            {r.hours_to_full ? `${r.hours_to_full} h to full recovery` : 'Fully recovered'}
          </span>
        </div>
        <div className="stack" style={{ alignItems: 'flex-end', gap: 6 }}>
          {r.coros_pct !== null && <span className="muted">COROS {r.coros_pct}%</span>}
          <Link to="/recovery" className="btn btn-small row">
            Load chart ›
          </Link>
        </div>
      </div>
      <BodyMap levels={r.muscles} size={300} />
      <div className="legend-bar">
        <span className="muted">fresh</span>
        <i />
        <span className="muted">fatigued</span>
      </div>
      {top.length === 0 && <span className="muted">All muscles fresh.</span>}
      {top.map(([m, v]) => (
        <div key={m} className="row spread">
          <span>{muscleLabel(m)}</span>
          <span style={{ color: fatigueColor(v) }}>{Math.round(v * 100)}%</span>
        </div>
      ))}
    </div>
  )
}
