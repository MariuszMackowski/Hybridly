import { useState } from 'react'
import { useExercises } from '../../api/hooks'

/** Bottom sheet to choose an exercise: quick alternatives first, then searchable list. */
export default function ExercisePicker(props: {
  title: string
  alternatives?: { id: number; name: string }[]
  onPick: (exerciseId: number) => void
  onClose: () => void
}) {
  const exercises = useExercises()
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  const matches = (exercises.data ?? []).filter(
    (e) => !needle || e.name.toLowerCase().includes(needle) || e.aliases.some((a) => a.toLowerCase().includes(needle)),
  )
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
