import { useState } from 'react'
import { useExercises } from '../../api/hooks'
import type { ExerciseOut } from '../../api/types'
import { muscleLabel } from '../../lib/muscles'

const SIMILAR_LIMIT = 8

/** Exercises sharing primary muscles with `current`, most overlap first. */
function similar(all: ExerciseOut[], current: ExerciseOut | undefined): ExerciseOut[] {
  if (!current) return []
  const score = (e: ExerciseOut) =>
    2 * e.primary_muscles.filter((m) => current.primary_muscles.includes(m)).length +
    e.secondary_muscles.filter((m) => current.secondary_muscles.includes(m)).length
  return all
    .filter((e) => e.id !== current.id && e.primary_muscles.some((m) => current.primary_muscles.includes(m)))
    .sort((a, b) => score(b) - score(a) || a.name.localeCompare(b.name))
    .slice(0, SIMILAR_LIMIT)
}

/** Row of chip buttons under a small label. */
function ChipRow<T>(props: {
  label: string
  items: T[]
  id: (t: T) => string | number
  name: (t: T) => string
  onPick: (t: T) => void
}) {
  if (props.items.length === 0) return null
  return (
    <div className="stack">
      <span className="muted section-label">{props.label}</span>
      <div className="chips">
        {props.items.map((t) => (
          <button key={props.id(t)} className="chip" onClick={() => props.onPick(t)}>
            {props.name(t)}
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * Bottom sheet to choose an exercise: suggestions first (template alternatives, then exercises
 * for the same muscles), exercises already in the workout, then a filterable list.
 */
export default function ExercisePicker(props: {
  title: string
  alternatives?: { id: number; name: string }[]
  /** Exercise being replaced or supersetted; drives the "similar" suggestions. */
  similarTo?: number
  inWorkout?: { key: string; name: string }[]
  onPick: (exerciseId: number) => void
  onPickExisting?: (key: string) => void
  onClose: () => void
}) {
  const exercises = useExercises()
  const [query, setQuery] = useState('')
  const [muscle, setMuscle] = useState<string | null>(null)
  const all = exercises.data ?? []
  const current = all.find((e) => e.id === props.similarTo)
  const seen = new Set<number>(props.similarTo === undefined ? [] : [props.similarTo])
  const suggestions = [...(props.alternatives ?? []), ...similar(all, current)].filter(
    (e) => !seen.has(e.id) && seen.add(e.id),
  )
  const muscles = [...new Set(all.flatMap((e) => e.primary_muscles))].sort((a, b) =>
    muscleLabel(a).localeCompare(muscleLabel(b)),
  )
  const needle = query.trim().toLowerCase()
  const matches = all
    .filter((e) => !muscle || e.primary_muscles.includes(muscle))
    .filter(
      (e) => !needle || e.name.toLowerCase().includes(needle) || e.aliases.some((a) => a.toLowerCase().includes(needle)),
    )
    .sort((a, b) => a.name.localeCompare(b.name))
  return (
    <div className="sheet-backdrop" onClick={props.onClose}>
      <div className="sheet stack" onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <strong>{props.title}</strong>
          <button className="btn-small" onClick={props.onClose}>
            Close
          </button>
        </div>
        <ChipRow label="Suggestions" items={suggestions} id={(e) => e.id} name={(e) => e.name} onPick={(e) => props.onPick(e.id)} />
        <ChipRow
          label="In this workout"
          items={props.inWorkout ?? []}
          id={(e) => e.key}
          name={(e) => e.name}
          onPick={(e) => props.onPickExisting?.(e.key)}
        />
        <div className="chips">
          {muscles.map((m) => (
            <button
              key={m}
              className={`chip${muscle === m ? ' on' : ''}`}
              onClick={() => setMuscle(muscle === m ? null : m)}
            >
              {muscleLabel(m)}
            </button>
          ))}
        </div>
        <input placeholder="Search exercises" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="sheet-list">
          {matches.map((e) => (
            <button key={e.id} className="btn-block list-item" onClick={() => props.onPick(e.id)}>
              {e.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
