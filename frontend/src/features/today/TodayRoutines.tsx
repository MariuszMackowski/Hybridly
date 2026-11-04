import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useRoutineDone, useRoutines, useToggleRoutineDone } from '../../api/hooks'
import type { Routine } from '../../api/types'

/** One routine with its videos and a done checkbox. */
function RoutineItem(props: { routine: Routine; done: boolean; onToggle: () => void }) {
  return (
    <div className="stack routine">
      <label className="row check-item">
        <input type="checkbox" checked={props.done} onChange={props.onToggle} />
        <strong>{props.routine.name}</strong>
      </label>
      <div className="videos">
        {props.routine.videos.map((v) => (
          <a key={v.id} href={v.url} target="_blank" rel="noopener" className="video">
            {v.thumbnail_url && <img src={v.thumbnail_url} alt="" />}
            <span>{v.title}</span>
          </a>
        ))}
      </div>
    </div>
  )
}

/** Today's home routines, plus any other routine picked ad hoc. */
export default function TodayRoutines(props: { day: string; planned: { routine: Routine; done: boolean }[] }) {
  const all = useRoutines().data ?? []
  const done = new Set(useRoutineDone(props.day).data ?? [])
  const toggle = useToggleRoutineDone()
  const [extraIds, setExtraIds] = useState<number[]>([])
  const [picking, setPicking] = useState(false)
  const plannedIds = new Set(props.planned.map((p) => p.routine.id))
  // Routines already ticked today show up even if they were not planned.
  const shown = [
    ...props.planned.map((p) => p.routine),
    ...all.filter((r) => !plannedIds.has(r.id) && (extraIds.includes(r.id) || done.has(r.id))),
  ]
  const others = all.filter((r) => !shown.some((s) => s.id === r.id))
  const flip = (r: Routine) => toggle.mutate({ routineId: r.id, day: props.day, done: !done.has(r.id) })

  return (
    <div className="card stack">
      <div className="row spread">
        <span className="muted">🏠 Home routines</span>
        <Link to="/routines" className="muted">
          Manage ›
        </Link>
      </div>
      {all.length === 0 ? (
        <Link to="/routines" className="btn btn-block row" style={{ justifyContent: 'center' }}>
          Set up home routines ›
        </Link>
      ) : (
        <>
          {shown.length === 0 && <span className="muted">Nothing planned today.</span>}
          {shown.map((r) => (
            <RoutineItem key={r.id} routine={r} done={done.has(r.id)} onToggle={() => flip(r)} />
          ))}
          {others.length > 0 && (
            <button className="btn-block" onClick={() => setPicking(true)}>
              + Other routine
            </button>
          )}
        </>
      )}
      {picking && (
        <div className="sheet-backdrop" onClick={() => setPicking(false)}>
          <div className="sheet stack" onClick={(e) => e.stopPropagation()}>
            <div className="row spread">
              <strong>Pick a routine</strong>
              <button className="btn-small" onClick={() => setPicking(false)}>
                Close
              </button>
            </div>
            <div className="sheet-list">
              {others.map((r) => (
                <button
                  key={r.id}
                  className="btn-block list-item"
                  onClick={() => {
                    setExtraIds((ids) => [...ids, r.id])
                    setPicking(false)
                  }}
                >
                  {r.name} <span className="muted">· {r.videos.length} videos</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
