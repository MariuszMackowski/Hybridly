import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useArchiveTemplate, useExercises, useSaveTemplate, useTemplate } from '../../api/hooks'
import type { SlotIn, TemplateIn } from '../../api/types'
import ExercisePicker from '../logger/ExercisePicker'

const EMPTY: TemplateIn = { name: '', note: null, warmup_items: [], cooldown_items: [], slots: [] }

/** Editable list of checklist lines. */
function ItemList(props: { title: string; items: string[]; onChange: (items: string[]) => void }) {
  return (
    <div className="stack">
      <span className="muted">{props.title}</span>
      {props.items.map((item, i) => (
        <div key={i} className="row">
          <input value={item} onChange={(e) => props.onChange(props.items.map((x, j) => (j === i ? e.target.value : x)))} />
          <button className="btn-small" onClick={() => props.onChange(props.items.filter((_, j) => j !== i))}>
            ✕
          </button>
        </div>
      ))}
      <button className="btn-small" onClick={() => props.onChange([...props.items, ''])}>
        + item
      </button>
    </div>
  )
}

/** Integer input bound to a slot field. */
function IntField(props: { label: string; value: number | null; min?: number; onChange: (v: number | null) => void }) {
  return (
    <label>
      {props.label}
      <input
        inputMode="numeric"
        value={props.value ?? ''}
        onChange={(e) => {
          const v = e.target.value.trim()
          props.onChange(v === '' ? null : Math.max(props.min ?? 0, Number.parseInt(v, 10) || 0))
        }}
      />
    </label>
  )
}

type PickerTarget = { kind: 'add' } | { kind: 'main'; index: number } | { kind: 'alt'; index: number } | null

export default function TemplateEditor() {
  const param = useParams().id
  const id = param === 'new' ? null : Number(param)
  const loaded = useTemplate(id)
  const exercises = useExercises(true).data ?? []
  const save = useSaveTemplate()
  const archive = useArchiveTemplate()
  const navigate = useNavigate()
  const [form, setForm] = useState<TemplateIn>(EMPTY)
  const [picker, setPicker] = useState<PickerTarget>(null)

  useEffect(() => {
    if (loaded.data) {
      const { name, note, warmup_items, cooldown_items, slots } = loaded.data
      setForm({
        name, note, warmup_items, cooldown_items,
        slots: slots.map(({ position: _p, exercise_name: _n, alternatives: _a, ...slot }) => slot),
      })
    }
  }, [loaded.data])

  const nameOf = (exerciseId: number) => exercises.find((e) => e.id === exerciseId)?.name ?? `#${exerciseId}`
  const setSlot = (index: number, patch: Partial<SlotIn>) =>
    setForm((f) => ({ ...f, slots: f.slots.map((s, i) => (i === index ? { ...s, ...patch } : s)) }))
  const moveSlot = (index: number, delta: number) =>
    setForm((f) => {
      const slots = [...f.slots]
      const target = index + delta
      if (target < 0 || target >= slots.length) return f
      ;[slots[index], slots[target]] = [slots[target], slots[index]]
      return { ...f, slots }
    })

  /** Apply the exercise chosen in the picker to the current target. */
  const onPick = (exerciseId: number) => {
    const target = picker
    setPicker(null)
    if (!target) return
    if (target.kind === 'add') {
      const slot: SlotIn = {
        block: 'main', exercise_id: exerciseId, alternative_exercise_ids: [], warmup_sets: 0, sets: 3,
        rep_min: 8, rep_max: 10, superset_group: null, note: null,
      }
      setForm((f) => ({ ...f, slots: [...f.slots, slot] }))
    } else if (target.kind === 'main') {
      setSlot(target.index, { exercise_id: exerciseId })
    } else {
      const current = form.slots[target.index].alternative_exercise_ids
      if (!current.includes(exerciseId)) setSlot(target.index, { alternative_exercise_ids: [...current, exerciseId] })
    }
  }

  /** Persist and return to the list. */
  const onSave = () =>
    save.mutate(
      { id, body: { ...form, warmup_items: form.warmup_items.filter(Boolean), cooldown_items: form.cooldown_items.filter(Boolean) } },
      { onSuccess: () => navigate('/templates') },
    )

  return (
    <div className="page stack">
      <button className="btn-small" style={{ alignSelf: 'flex-start' }} onClick={() => navigate('/templates')}>
        ‹ Templates
      </button>
      {save.isError && <div className="banner">{save.error.message}</div>}
      <div className="card stack">
        <label>
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          Note
          <input value={form.note ?? ''} onChange={(e) => setForm({ ...form, note: e.target.value || null })} />
        </label>
      </div>

      <div className="card stack">
        <ItemList title="Warm-up checklist" items={form.warmup_items} onChange={(v) => setForm({ ...form, warmup_items: v })} />
      </div>

      {form.slots.map((slot, i) => (
        <div key={i} className="card stack">
          <div className="row spread">
            <button className="exercise-name" onClick={() => setPicker({ kind: 'main', index: i })}>
              {i + 1}. {nameOf(slot.exercise_id)}
            </button>
            <div className="row">
              <button className="btn-small" onClick={() => moveSlot(i, -1)}>↑</button>
              <button className="btn-small" onClick={() => moveSlot(i, 1)}>↓</button>
              <button
                className="btn-small btn-danger"
                onClick={() => setForm((f) => ({ ...f, slots: f.slots.filter((_, j) => j !== i) }))}
              >
                ✕
              </button>
            </div>
          </div>
          <div className="row">
            <IntField label="Warm-up" value={slot.warmup_sets} onChange={(v) => setSlot(i, { warmup_sets: v ?? 0 })} />
            <IntField label="Sets" value={slot.sets} min={1} onChange={(v) => setSlot(i, { sets: v ?? 1 })} />
            <IntField label="Reps min" value={slot.rep_min} min={1} onChange={(v) => setSlot(i, { rep_min: v ?? 1 })} />
            <IntField label="Reps max" value={slot.rep_max} min={1} onChange={(v) => setSlot(i, { rep_max: v ?? 1 })} />
          </div>
          <div className="row">
            <label>
              Block
              <select value={slot.block} onChange={(e) => setSlot(i, { block: e.target.value as SlotIn['block'] })}>
                <option value="main">main</option>
                <option value="finisher">finisher</option>
              </select>
            </label>
            <IntField label="Superset #" value={slot.superset_group} onChange={(v) => setSlot(i, { superset_group: v })} />
          </div>
          <div className="chips">
            {slot.alternative_exercise_ids.map((a) => (
              <button
                key={a}
                className="chip on"
                onClick={() => setSlot(i, { alternative_exercise_ids: slot.alternative_exercise_ids.filter((x) => x !== a) })}
              >
                {nameOf(a)} ✕
              </button>
            ))}
            <button className="chip" onClick={() => setPicker({ kind: 'alt', index: i })}>
              + alternative
            </button>
          </div>
          <input placeholder="Note" value={slot.note ?? ''} onChange={(e) => setSlot(i, { note: e.target.value || null })} />
        </div>
      ))}
      <button className="btn-block" onClick={() => setPicker({ kind: 'add' })}>
        + Add exercise
      </button>

      <div className="card stack">
        <ItemList title="Cool-down checklist" items={form.cooldown_items} onChange={(v) => setForm({ ...form, cooldown_items: v })} />
      </div>

      <button className="btn-primary btn-block" disabled={save.isPending || !form.name.trim()} onClick={onSave}>
        Save template
      </button>
      {id !== null && (
        <button
          className="btn-danger btn-block"
          onClick={() =>
            window.confirm('Archive this template?') &&
            archive.mutate(id, { onSuccess: () => navigate('/templates') })
          }
        >
          Archive template
        </button>
      )}

      {picker && (
        <ExercisePicker
          title={picker.kind === 'alt' ? 'Add alternative' : 'Choose exercise'}
          onPick={onPick}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  )
}
