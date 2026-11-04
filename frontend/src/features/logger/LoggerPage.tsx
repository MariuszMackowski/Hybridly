import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { fetchContext, useSaveWorkout } from '../../api/hooks'
import {
  addExercise,
  addSet,
  displayOrder,
  hasLoggedSets,
  removeExercise,
  removeSet,
  swapExercise,
  toggleChecklist,
  toggleDone,
  toPayload,
  updateSet,
  type DraftExercise,
  type WorkoutDraft,
} from './draft'
import ExerciseCard, { type CardActions } from './ExerciseCard'
import ExercisePicker from './ExercisePicker'
import { useDraft } from './useDraft'

/** Elapsed "mm:ss" (or "h:mm:ss") since the workout started, ticking every second. */
function useElapsed(startedAt: string | undefined) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  if (!startedAt) return ''
  const total = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000))
  const h = Math.floor(total / 3600)
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const ss = String(total % 60).padStart(2, '0')
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

/** Collapsible checklist for warm-up / cool-down items. */
function Checklist(props: { title: string; items: WorkoutDraft['warmup']; onToggle: (i: number) => void }) {
  if (props.items.length === 0) return null
  const done = props.items.filter((i) => i.done).length
  return (
    <details className="card">
      <summary>
        {props.title} <span className="muted">({done}/{props.items.length})</span>
      </summary>
      <div className="stack checklist">
        {props.items.map((item, i) => (
          <label key={i} className="row check-item">
            <input type="checkbox" checked={item.done} onChange={() => props.onToggle(i)} />
            <span>{item.text}</span>
          </label>
        ))}
      </div>
    </details>
  )
}

type Picker = { mode: 'swap'; exercise: DraftExercise } | { mode: 'add' } | null

export default function LoggerPage() {
  const { draft, setDraft, updateDraft } = useDraft()
  const save = useSaveWorkout()
  const navigate = useNavigate()
  const elapsed = useElapsed(draft?.startedAt)
  const [picker, setPicker] = useState<Picker>(null)
  const [error, setError] = useState<string | null>(null)

  if (!draft) return <Navigate to="/" replace />

  const update = updateDraft
  const actions: CardActions = {
    onChange: (key, i, patch) => update((d) => updateSet(d, key, i, patch)),
    onToggle: (key, i) => update((d) => toggleDone(d, key, i)),
    onRemoveSet: (key, i) => update((d) => removeSet(d, key, i)),
    onAddSet: (key, warmup) => update((d) => addSet(d, key, warmup)),
    onSwap: (exercise) => {
      if (hasLoggedSets(exercise) && !window.confirm(`Replacing ${exercise.name} discards its logged sets. Continue?`)) return
      setPicker({ mode: 'swap', exercise })
    },
    onRemove: (key) => update((d) => removeExercise(d, key)),
  }

  /** Load context for the picked exercise and swap or append it. */
  async function pick(exerciseId: number) {
    const current = picker
    setPicker(null)
    try {
      if (current?.mode === 'swap') {
        const ex = current.exercise
        const ctx = await fetchContext(exerciseId, ex.sets, ex.repMin, ex.repMax)
        update((d) => swapExercise(d, ex.key, ctx))
      } else {
        const ctx = await fetchContext(exerciseId)
        update((d) => addExercise(d, ctx))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  /** Send the workout once; keep the draft if anything fails. */
  function onSave() {
    setError(null)
    save.mutate(toPayload(draft!, new Date()), {
      onSuccess: (workout) => {
        setDraft(null)
        navigate(`/history/${workout.id}`, { replace: true })
      },
      onError: (e) => setError(e.message),
    })
  }

  const groups = displayOrder(draft)
  const main = groups.filter((g) => g.group[0].block === 'main')
  const finishers = groups.filter((g) => g.group[0].block === 'finisher')
  const doneSets = draft.exercises.reduce((n, ex) => n + ex.rows.filter((r) => r.done).length, 0)

  return (
    <div className="page stack logger">
      <header className="logger-head row spread">
        <button className="btn-small" onClick={() => navigate('/')}>
          ‹ Today
        </button>
        <div className="logger-title">
          <strong>{draft.title ?? 'Workout'}</strong>
          <span className="muted"> · {elapsed}</span>
        </div>
        <button
          className="btn-small btn-danger"
          onClick={() => {
            if (window.confirm('Discard this workout? Logged sets will be lost.')) {
              setDraft(null)
              navigate('/')
            }
          }}
        >
          Discard
        </button>
      </header>

      {error && <div className="banner">{error}</div>}

      <Checklist title="Warm-up" items={draft.warmup} onToggle={(i) => update((d) => toggleChecklist(d, 'warmup', i))} />
      {main.map(({ group }) => (
        <ExerciseCard key={group[0].key} group={group} actions={actions} />
      ))}
      {finishers.length > 0 && <div className="muted section-label">Finishers</div>}
      {finishers.map(({ group }) => (
        <ExerciseCard key={group[0].key} group={group} actions={actions} />
      ))}
      <button className="btn-block" onClick={() => setPicker({ mode: 'add' })}>
        + Add exercise
      </button>
      <Checklist title="Cool-down" items={draft.cooldown} onToggle={(i) => update((d) => toggleChecklist(d, 'cooldown', i))} />

      <div className="save-bar">
        <button className="btn-primary btn-block" disabled={save.isPending || doneSets === 0} onClick={onSave}>
          {save.isPending ? 'Saving…' : `Save workout (${doneSets} sets)`}
        </button>
      </div>

      {picker && (
        <ExercisePicker
          title={picker.mode === 'swap' ? `Replace ${picker.exercise.name}` : 'Add exercise'}
          alternatives={picker.mode === 'swap' ? picker.exercise.alternatives : undefined}
          onPick={pick}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  )
}
