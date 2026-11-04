import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useRecovery } from '../../api/hooks'
import BodyMap from './BodyMap'
import MuscleList from './MuscleList'

/** Recovery %, muscle map and two weeks of load. */
export default function RecoveryPage() {
  const query = useRecovery()
  const r = query.data
  if (query.isError) return <div className="page banner">{query.error.message}</div>
  if (!r) return <div className="page muted">Loading…</div>
  return (
    <div className="page stack">
      <h1>Recovery</h1>
      <div className="card row spread">
        <div>
          <div className="big-number">{r.recovery_pct}%</div>
          <span className="muted">{r.hours_to_full ? `${r.hours_to_full} h to full recovery` : 'Fully recovered'}</span>
        </div>
        {r.coros_pct !== null && <span className="muted">COROS {r.coros_pct}%</span>}
      </div>
      <div className="card stack">
        <BodyMap levels={r.muscles} size={300} />
        <div className="legend-bar">
          <span className="muted">fresh</span>
          <i />
          <span className="muted">fatigued</span>
        </div>
        <MuscleList levels={r.muscles} />
      </div>
      <div className="card">
        <strong>Load · last 14 days</strong>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={r.daily.map((d) => ({ ...d, label: d.day.slice(8) }))} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="label" stroke="#8a90a0" fontSize={10} />
            <YAxis stroke="#8a90a0" fontSize={10} />
            <Tooltip contentStyle={{ background: '#181b22', border: '1px solid #2a2f3a' }} />
            <Bar dataKey="strength" stackId="a" fill="#ff7a1a" name="Gym" isAnimationActive={false} />
            <Bar dataKey="cardio" stackId="a" fill="#38bdf8" name="Cardio" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
