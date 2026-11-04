import { useEffect, useState } from 'react'
import {
  useAddVideo,
  useArchiveRoutine,
  useDeleteVideo,
  useRoutines,
  useRoutineWeek,
  useSaveRoutine,
  useSaveRoutineWeek,
  useVideos,
} from '../../api/hooks'
import type { Routine } from '../../api/types'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** Name + ordered video picks for one routine. */
function RoutineForm({ routine, onDone }: { routine: Routine | null; onDone: () => void }) {
  const videos = useVideos().data ?? []
  const save = useSaveRoutine()
  const [name, setName] = useState(routine?.name ?? '')
  const [ids, setIds] = useState<number[]>(routine?.video_ids ?? [])
  const toggle = (id: number) => setIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  return (
    <div className="stack">
      <input placeholder="Routine name (e.g. Core)" value={name} onChange={(e) => setName(e.target.value)} />
      <span className="muted">Videos (alternatives — doing one counts):</span>
      <div className="chips">
        {videos.map((v) => (
          <button key={v.id} className={`chip${ids.includes(v.id) ? ' on' : ''}`} onClick={() => toggle(v.id)}>
            {v.title}
          </button>
        ))}
      </div>
      {save.isError && <div className="banner">{save.error.message}</div>}
      <div className="row">
        <button
          className="btn-primary"
          disabled={!name.trim() || save.isPending}
          onClick={() =>
            save.mutate({ id: routine?.id ?? null, body: { name: name.trim(), note: null, video_ids: ids } }, { onSuccess: onDone })
          }
        >
          Save
        </button>
        <button onClick={onDone}>Cancel</button>
      </div>
    </div>
  )
}

/** Weekday → routines checkboxes. */
function RoutineWeek({ routines }: { routines: Routine[] }) {
  const week = useRoutineWeek().data
  const save = useSaveRoutineWeek()
  const [items, setItems] = useState<{ weekday: number; routine_ids: number[] }[]>([])
  useEffect(() => {
    if (week) setItems(week)
  }, [week])
  const toggle = (day: number, id: number) =>
    setItems((cur) =>
      cur.map((i) =>
        i.weekday === day
          ? { ...i, routine_ids: i.routine_ids.includes(id) ? i.routine_ids.filter((x) => x !== id) : [...i.routine_ids, id] }
          : i,
      ),
    )
  return (
    <div className="stack">
      <span className="muted">Week plan</span>
      {items.map((item) => (
        <div key={item.weekday} className="row" style={{ flexWrap: 'wrap' }}>
          <span style={{ width: 40 }}>{DAYS[item.weekday]}</span>
          {routines.map((r) => (
            <button
              key={r.id}
              className={`chip${item.routine_ids.includes(r.id) ? ' on' : ''}`}
              onClick={() => toggle(item.weekday, r.id)}
            >
              {r.name}
            </button>
          ))}
        </div>
      ))}
      <button disabled={save.isPending} onClick={() => save.mutate(items)}>
        {save.isSuccess && !save.isPending ? 'Saved ✓' : 'Save week'}
      </button>
    </div>
  )
}

/** Video library, routines and their weekday plan. */
export default function RoutinesEditor() {
  const videos = useVideos().data ?? []
  const routines = useRoutines().data ?? []
  const addVideo = useAddVideo()
  const deleteVideo = useDeleteVideo()
  const archive = useArchiveRoutine()
  const [url, setUrl] = useState('')
  const [editing, setEditing] = useState<Routine | null | 'new'>(null)
  return (
    <details className="card">
      <summary>
        <strong>Home routines</strong>
        <span className="muted">
          {routines.length} routines · {videos.length} videos
        </span>
      </summary>
      <div className="stack">
        <span className="muted">Video library</span>
        <div className="row">
          <input placeholder="YouTube link" value={url} onChange={(e) => setUrl(e.target.value)} />
          <button disabled={!url.trim() || addVideo.isPending} onClick={() => addVideo.mutate(url.trim(), { onSuccess: () => setUrl('') })}>
            Add
          </button>
        </div>
        {addVideo.isError && <div className="banner">{addVideo.error.message}</div>}
        {videos.map((v) => (
          <div key={v.id} className="row spread">
            <a href={v.url} target="_blank" rel="noopener" className="video" style={{ flex: 1 }}>
              {v.thumbnail_url && <img src={v.thumbnail_url} alt="" />}
              <span>{v.title}</span>
            </a>
            <button className="btn-small btn-danger" onClick={() => window.confirm(`Delete "${v.title}"?`) && deleteVideo.mutate(v.id)}>
              ✕
            </button>
          </div>
        ))}

        <span className="muted">Routines</span>
        {editing !== null ? (
          <RoutineForm routine={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />
        ) : (
          <>
            {routines.map((r) => (
              <div key={r.id} className="row spread">
                <button className="list-item exercise-link" onClick={() => setEditing(r)}>
                  <strong>{r.name}</strong> <span className="muted">· {r.videos.length} videos</span>
                </button>
                <button className="btn-small btn-danger" onClick={() => window.confirm(`Archive ${r.name}?`) && archive.mutate(r.id)}>
                  Archive
                </button>
              </div>
            ))}
            <button onClick={() => setEditing('new')}>+ New routine</button>
          </>
        )}
        {routines.length > 0 && <RoutineWeek routines={routines} />}
      </div>
    </details>
  )
}
