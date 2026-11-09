import { useState } from 'react'
import { useExercises } from '../../api/hooks'
import { muscleLabel } from '../../lib/muscles'

/** Bottom sheet to choose an exercise: quick alternatives first, then a list filterable by target muscle and search. */
export default function ExercisePicker(props: {
  title: string
  alternatives?: { id: number; name: string }[]
  onPick: (exerciseId: number) => void
  onClose: () => void
}) {
  const exercises = useExercises()
  const [query, setQuery] = useState('')
  const [muscle, setMuscle] = useState<string | null>(null)
  const all = exercises.data ?? []
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
        {props.alternatives && props.alternatives.length > 1 && (
          <div className="chips">
            {props.alternatives.map((a) => (
              <button key={a.id} className="chip" onClick={() => props.onPick(a.id)}>
                {a.name}
              </button>
            ))}
          </div>
        )}
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
