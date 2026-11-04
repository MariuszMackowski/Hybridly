import { useState } from 'react'
import { byFatigue, fatigueColor, muscleLabel, topMuscles } from '../../lib/muscles'

const TOP = 6

/** Most fatigued muscles, expandable to the full breakdown. */
export default function MuscleList({ levels }: { levels: Record<string, number> }) {
  const [all, setAll] = useState(false)
  const top = topMuscles(levels, TOP)
  const everything = byFatigue(levels)
  const shown = all ? everything : top
  return (
    <>
      {top.length === 0 && !all && <span className="muted">All muscles fresh.</span>}
      {shown.map(([m, v]) => (
        <div key={m} className="row spread">
          <span>{muscleLabel(m)}</span>
          <span style={{ color: fatigueColor(v) }}>{Math.round(v * 100)}%</span>
        </div>
      ))}
      {everything.length > top.length && (
        <button className="btn-small" onClick={() => setAll(!all)}>
          {all ? 'Show less' : `Show all (${everything.length})`}
        </button>
      )}
    </>
  )
}
