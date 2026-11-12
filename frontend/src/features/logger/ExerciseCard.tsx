import { useState } from 'react'
import type { DraftExercise, DraftSet, SetValues } from './draft'
import { MEASURE_UNIT } from '../../lib/format'
import SetRow from './SetRow'

export type CardActions = {
  onChange: (key: string, index: number, patch: Partial<SetValues>) => void
  onToggle: (key: string, index: number) => void
  onRemoveSet: (key: string, index: number) => void
  onAddSet: (key: string, warmup: boolean) => void
  onSwap: (exercise: DraftExercise) => void
  onGrip: (exercise: DraftExercise, grip: string) => void
  onSuperset: (exercise: DraftExercise) => void
  onUnlink: (key: string) => void
  onRemove: (key: string) => void
}

type Line = { ex: DraftExercise; index: number; row: DraftSet; label: string }

/** Row labels: W for warm-ups, 1..n for working sets, prefixed A/B.. inside supersets. */
function lines(group: DraftExercise[]): Line[] {
  const perExercise = group.map((ex, g) => {
    let working = 0
    const prefix = group.length > 1 ? String.fromCharCode(65 + g) : ''
    return ex.rows.map((row, index) => ({
      ex, index, row, label: row.isWarmup ? 'W' : `${prefix}${++working}`,
    }))
  })
  if (group.length === 1) return perExercise[0]
  const longest = Math.max(...perExercise.map((l) => l.length))
  const interleaved: Line[] = []
  for (let i = 0; i < longest; i++) perExercise.forEach((l) => l[i] && interleaved.push(l[i]))
  return interleaved
}

export default function ExerciseCard(props: { group: DraftExercise[]; actions: CardActions }) {
  const { group, actions } = props
  const [menu, setMenu] = useState<string | null>(null)
  const menuEx = group.find((e) => e.key === menu)
  /** Close the ⋯ menu, then run the chosen action. */
  const close = (action: () => void) => () => {
    setMenu(null)
    action()
  }
  return (
    <div className="card exercise-card">
      {group.map((ex, g) => (
        <div key={ex.key} className="row spread exercise-head">
          <button className="exercise-name" onClick={() => actions.onSwap(ex)}>
            {group.length > 1 && <span className="muted">{String.fromCharCode(65 + g)} · </span>}
            {ex.name} {ex.perSide && <span className="badge">per side</span>}
          </button>
          <span className="muted target">
            {ex.sets} × {ex.repMin === ex.repMax ? ex.repMin : `${ex.repMin}–${ex.repMax}`}
          </span>
        </div>
      ))}
      {group.map((ex) =>
        ex.grips?.length ? (
          <div key={`${ex.key}-grip`} className="chips grip-chips">
            {group.length > 1 && <span className="muted">{ex.name}:</span>}
            {ex.grips.map((g) => (
              <button
                key={g}
                className={`chip${ex.grip === g ? ' on' : ''}`}
                onClick={() => ex.grip !== g && actions.onGrip(ex, g)}
              >
                {g}
              </button>
            ))}
          </div>
        ) : null,
      )}
      <div className="set-row set-head muted">
        <span>#</span>
        <span>Prev</span>
        <span>Suggested</span>
        <span>kg</span>
        <span>{MEASURE_UNIT[group[0].measure]}</span>
        <span />
        <span />
      </div>
      {lines(group).map(({ ex, index, row, label }) => (
        <SetRow
          key={`${ex.key}-${index}`}
          label={label}
          row={row}
          measure={ex.measure}
          onChange={(patch) => actions.onChange(ex.key, index, patch)}
          onToggle={() => actions.onToggle(ex.key, index)}
          onRemove={() => (!row.done || window.confirm('Remove this logged set?')) && actions.onRemoveSet(ex.key, index)}
        />
      ))}
      {group.map((ex) => (
        <div key={ex.key} className="row card-actions">
          {group.length > 1 && <span className="muted">{ex.name}:</span>}
          <button className="btn-small" onClick={() => actions.onAddSet(ex.key, false)}>
            + set
          </button>
          <button className="btn-small" onClick={() => actions.onAddSet(ex.key, true)}>
            + warm-up
          </button>
          <button
            className="btn-small btn-danger"
            onClick={() => window.confirm(`Remove ${ex.name} from this workout?`) && actions.onRemove(ex.key)}
          >
            Remove
          </button>
          <button className="btn-small" aria-label="More" onClick={() => setMenu(menu === ex.key ? null : ex.key)}>
            ⋯
          </button>
        </div>
      ))}
      {menuEx && (
        <div className="row card-actions card-menu">
          <button className="btn-small" onClick={close(() => actions.onSwap(menuEx))}>
            Replace
          </button>
          <button className="btn-small" onClick={close(() => actions.onSuperset(menuEx))}>
            Super set with…
          </button>
          {menuEx.supersetGroup !== null && group.length > 1 && (
            <button className="btn-small" onClick={close(() => actions.onUnlink(menuEx.key))}>
              Unlink superset
            </button>
          )}
        </div>
      )}
    </div>
  )
}
