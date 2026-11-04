import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useBodyweight, useSaveBodyweight, useToday } from '../../api/hooks'
import { parseDecimal } from '../../lib/decimal'
import { kg } from '../../lib/format'
import CorosCard from './CorosCard'

export default function SettingsPage() {
  const today = useToday().data?.date ?? new Date().toISOString().slice(0, 10)
  const entries = useBodyweight()
  const save = useSaveBodyweight()
  const [day, setDay] = useState<string | null>(null)
  const [value, setValue] = useState('')
  const parsed = parseDecimal(value)
  const [params] = useSearchParams()
  const corosError = params.get('coros_error')

  return (
    <div className="page stack">
      <h1>Settings</h1>
      {params.get('coros') === 'connected' && <div className="card good">COROS connected — first sync started.</div>}
      {corosError && <div className="banner">COROS: {corosError}</div>}
      <CorosCard />
      <div className="card stack">
        <strong>Bodyweight</strong>
        <span className="muted">Used for bodyweight exercises (pull-ups: logged kg = added weight).</span>
        {save.isError && <div className="banner">{save.error.message}</div>}
        <div className="row">
          <input type="date" value={day ?? today} onChange={(e) => setDay(e.target.value)} />
          <input inputMode="decimal" placeholder="kg" value={value} onChange={(e) => setValue(e.target.value)} />
          <button
            className="btn-primary"
            disabled={parsed === null || save.isPending}
            onClick={() => save.mutate({ day: day ?? today, kg: parsed! }, { onSuccess: () => setValue('') })}
          >
            Save
          </button>
        </div>
        {(entries.data ?? []).slice(0, 10).map((e) => (
          <div key={e.day} className="row spread muted">
            <span>{e.day}</span>
            <span>{kg(e.kg)} kg</span>
          </div>
        ))}
      </div>
    </div>
  )
}
