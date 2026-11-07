import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useRecovery } from '../../api/hooks'

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** This week's daily training load (gym + cardio, Mon–Sun) with the week total. */
export default function WeeklyLoadCard() {
  const week = useRecovery().data?.week
  if (!week) return null
  const today = new Date().toLocaleDateString('sv-SE') // local YYYY-MM-DD
  const total = Math.round(week.reduce((sum, d) => sum + d.strength + d.cardio, 0))
  const data = week.map((d, i) => ({ ...d, label: d.day === today ? 'Today' : DAY_LABELS[i] }))
  return (
    <div className="card">
      <div className="row spread">
        <strong>Weekly load</strong>
        <span>
          <span className="muted">Total </span>
          <strong>{total}</strong>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
          <XAxis dataKey="label" stroke="#8a90a0" fontSize={11} tickLine={false} />
          <YAxis stroke="#8a90a0" fontSize={10} tickLine={false} />
          <Tooltip contentStyle={{ background: '#181b22', border: '1px solid #2a2f3a' }} cursor={false} />
          <Bar dataKey="cardio" stackId="a" fill="#38bdf8" name="Cardio" isAnimationActive={false} />
          <Bar dataKey="strength" stackId="a" fill="#ff7a1a" name="Gym" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
