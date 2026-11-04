import { useState } from 'react'
import { useMuscles, useSaveExercise } from '../../api/hooks'
import type { ExerciseIn, ExerciseOut } from '../../api/types'
import { parseDecimal } from '../../lib/decimal'

const EMPTY: ExerciseIn = {
  name: '', aliases: [], primary_muscles: [], secondary_muscles: [], measure: 'reps', load_factor: 1,
  increment_kg: 2.5, is_bodyweight: false, per_side: false, note: null,
}

/** Toggleable chips for picking muscles. */
function MuscleChips(props: { all: string[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="chips">
      {props.all.map((m) => {
        const on = props.value.includes(m)
        return (
          <button
            key={m}
            type="button"
            className={`chip${on ? ' on' : ''}`}
            onClick={() => props.onChange(on ? props.value.filter((x) => x !== m) : [...props.value, m])}
          >
            {m.replace('_', ' ')}
          </button>
        )
      })}
    </div>
  )
}

export default function ExerciseForm(props: { exercise: ExerciseOut | null; onDone: () => void }) {
  const [form, setForm] = useState<ExerciseIn>(props.exercise ?? EMPTY)
  const [increment, setIncrement] = useState(String(form.increment_kg))
  const [loadFactor, setLoadFactor] = useState(String(form.load_factor))
  const muscles = useMuscles().data ?? []
  const save = useSaveExercise()
  const set = <K extends keyof ExerciseIn>(key: K, value: ExerciseIn[K]) => setForm((f) => ({ ...f, [key]: value }))

  /** Validate numbers and send. */
  const submit = () => {
    const body = {
      ...form,
      increment_kg: parseDecimal(increment) ?? 0,
      load_factor: parseDecimal(loadFactor) ?? 1,
    }
    save.mutate({ id: props.exercise?.id ?? null, body }, { onSuccess: props.onDone })
  }

  return (
    <div className="card stack">
      {save.isError && <div className="banner">{save.error.message}</div>}
      <label>
        Name
        <input value={form.name} onChange={(e) => set('name', e.target.value)} />
      </label>
      <div className="field">
        <span>Primary muscles</span>
        <MuscleChips all={muscles} value={form.primary_muscles} onChange={(v) => set('primary_muscles', v)} />
      </div>
      <div className="field">
        <span>Secondary muscles</span>
        <MuscleChips all={muscles} value={form.secondary_muscles} onChange={(v) => set('secondary_muscles', v)} />
      </div>
      <div className="row">
        <label>
          Increment kg
          <input inputMode="decimal" value={increment} onChange={(e) => setIncrement(e.target.value)} />
        </label>
        <label>
          Load factor
          <input inputMode="decimal" value={loadFactor} onChange={(e) => setLoadFactor(e.target.value)} />
        </label>
        <label>
          Measure
          <select value={form.measure} onChange={(e) => set('measure', e.target.value as ExerciseIn['measure'])}>
            <option value="reps">reps</option>
            <option value="time">time</option>
          </select>
        </label>
      </div>
      <div className="row">
        <label className="row check-item">
          <input type="checkbox" checked={form.is_bodyweight} onChange={(e) => set('is_bodyweight', e.target.checked)} />
          Bodyweight (log added kg)
        </label>
        <label className="row check-item">
          <input type="checkbox" checked={form.per_side} onChange={(e) => set('per_side', e.target.checked)} />
          Per side
        </label>
      </div>
      <label>
        Aliases (comma separated)
        <input
          value={form.aliases.join(', ')}
          onChange={(e) => set('aliases', e.target.value.split(',').map((a) => a.trim()).filter(Boolean))}
        />
      </label>
      <label>
        Note
        <textarea value={form.note ?? ''} onChange={(e) => set('note', e.target.value || null)} />
      </label>
      <div className="row">
        <button className="btn-primary" disabled={save.isPending || !form.name.trim()} onClick={submit}>
          Save
        </button>
        <button onClick={props.onDone}>Cancel</button>
      </div>
    </div>
  )
}
