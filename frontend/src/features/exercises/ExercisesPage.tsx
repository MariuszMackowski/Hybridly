import { useState } from 'react'
import { useArchiveExercise, useExercises } from '../../api/hooks'
import type { ExerciseOut } from '../../api/types'
import BackButton from '../../components/BackButton'
import ExerciseForm from './ExerciseForm'

type Editing = { exercise: ExerciseOut | null } | null

export default function ExercisesPage() {
  const exercises = useExercises()
  const archive = useArchiveExercise()
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<Editing>(null)

  if (editing) return (
    <div className="page stack">
      <h1>{editing.exercise ? editing.exercise.name : 'New exercise'}</h1>
      <ExerciseForm exercise={editing.exercise} onDone={() => setEditing(null)} />
    </div>
  )

  const needle = query.trim().toLowerCase()
  const list = (exercises.data ?? []).filter((e) => !needle || e.name.toLowerCase().includes(needle))
  return (
    <div className="page stack">
      <BackButton to="/settings" label="Settings" />
      <div className="row spread">
        <h1>Exercises</h1>
        <button className="btn-small btn-primary" onClick={() => setEditing({ exercise: null })}>
          + New
        </button>
      </div>
      <input placeholder="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
      {list.map((e) => (
        <div key={e.id} className="card row spread">
          <button className="list-item exercise-link" onClick={() => setEditing({ exercise: e })}>
            <strong>{e.name}</strong>
            <span className="muted">
              {' '}
              {[...e.primary_muscles, ...e.secondary_muscles].map((m) => m.replace('_', ' ')).join(', ') || 'no muscles set'}
            </span>
          </button>
          <button
            className="btn-small btn-danger"
            onClick={() => window.confirm(`Archive ${e.name}? History stays.`) && archive.mutate(e.id)}
          >
            Archive
          </button>
        </div>
      ))}
    </div>
  )
}
