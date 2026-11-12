import { Link } from 'react-router-dom'
import type { ExerciseProgress, ProgressSession, RecordValue } from '../../api/types'
import { dayDate, kg } from '../../lib/format'

/** "Wed 04.11.26" of an instant. */
const day = (iso: string) => dayDate(iso, true)

/** "To beat 57 kg, try 46 kg × 9 or 48.5 kg × 7" — based on the last session's best e1RM. */
export function ToBeat({ toBeat }: { toBeat: ExerciseProgress['to_beat'] }) {
  if (!toBeat) return null
  return (
    <div>
      <span className="muted">To beat {kg(Math.round(toBeat.target_e1rm_kg))} kg, try </span>
      {toBeat.options.map((o, i) => (
        <span key={i}>
          {i > 0 && <span className="muted"> or </span>}
          <strong className="accent">
            {kg(o.weight_kg)} kg × {o.reps}
          </strong>
        </span>
      ))}
    </div>
  )
}

/** Last few sessions with their working sets, each linking to the workout. */
export function RecentSessions({ sessions }: { sessions: ProgressSession[] }) {
  if (sessions.length === 0) return null
  return (
    <div className="card stack">
      <strong>Recent sessions</strong>
      {sessions.map((s) => (
        <Link key={s.workout_id} to={`/history/${s.workout_id}`} className="row spread">
          <span>
            <div>{day(s.started_at)}</div>
            <div className="muted">{s.sets.map((p) => `${kg(p.weight_kg)} × ${p.reps}`).join(' · ')}</div>
          </span>
          <span className="muted">{s.sets.length} sets ›</span>
        </Link>
      ))}
    </div>
  )
}

/** One record tile: label, value and the set/date it came from. */
function Tile({ label, record, value }: { label: string; record: RecordValue | null; value: (r: RecordValue) => string }) {
  if (!record) return null
  return (
    <Link to={`/history/${record.workout_id}`}>
      <div className="muted label">{label}</div>
      <strong>{value(record)}</strong>
      <div className="muted">
        {record.reps !== null && `${kg(record.weight_kg)} × ${record.reps} · `}
        {day(record.started_at)}
      </div>
    </Link>
  )
}

/** Best e1RM, heaviest set, biggest set and best session. */
export function RecordsCard({ records }: { records: ExerciseProgress['records'] }) {
  if (!records.heaviest) return null
  return (
    <div className="card stack">
      <strong>Records</strong>
      <div className="record-grid">
        <Tile label="Best est. 1RM" record={records.best_e1rm} value={(r) => `${kg(Math.round(r.value_kg))} kg`} />
        <Tile label="Heaviest" record={records.heaviest} value={(r) => `${kg(r.value_kg)} kg`} />
        <Tile label="Biggest set" record={records.biggest_set} value={(r) => `${Math.round(r.value_kg)} kg`} />
        <Tile label="Best session" record={records.best_session} value={(r) => `${Math.round(r.value_kg)} kg`} />
      </div>
    </div>
  )
}

/** Weight you should manage for 1/3/5/8/10/12 reps, from the best e1RM. */
export function MaxesCard({ maxes }: { maxes: ExerciseProgress['maxes'] }) {
  if (maxes.length === 0) return null
  return (
    <div className="card stack">
      <strong>Estimated maxes</strong>
      <table className="sets">
        <thead>
          <tr>
            <th>reps</th>
            {maxes.map((m) => (
              <th key={m.reps}>{m.reps}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="muted">kg</td>
            {maxes.map((m) => (
              <td key={m.reps}>{kg(m.weight_kg)}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
