import { Link } from 'react-router-dom'
import { useRecovery } from '../../api/hooks'
import BodyMap from './BodyMap'
import MuscleList from './MuscleList'
import RegionRows from './RegionRows'

/** Full recovery view for Today: %, big front/back map, legend and most fatigued muscles. */
export default function RecoveryCard() {
  const r = useRecovery().data
  if (!r) return null
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
      <RegionRows regions={r.regions} />
      <BodyMap levels={r.muscles} size={300} />
      <div className="legend-bar">
        <span className="muted">fresh</span>
        <i />
        <span className="muted">fatigued</span>
      </div>
      <MuscleList levels={r.muscles} />
    </div>
  )
}
