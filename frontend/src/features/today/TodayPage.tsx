import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTemplates, useToday } from '../../api/hooks'
import type { TemplateOut } from '../../api/types'
import { startDraft, useDraft } from '../logger/useDraft'
import SessionCard from '../plan/SessionCard'
import TodayRoutines from '../plan/TodayRoutines'
import RecoveryCard from '../recovery/RecoveryCard'
import WeeklyLoadCard from '../recovery/WeeklyLoadCard'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function TodayPage() {
  const today = useToday()
  const templates = useTemplates()
  const { draft, setDraft } = useDraft()
  const navigate = useNavigate()
  const [starting, setStarting] = useState(false)
  const [picking, setPicking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Build a draft for the chosen template and open the logger. */
  async function start(template: TemplateOut | null) {
    setStarting(true)
    setError(null)
    try {
      await startDraft(template)
      navigate('/log')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setStarting(false)
    }
  }

  const t = today.data
  const planned = today.data?.template ?? null
  /** Close the chooser and start the selected template. */
  const choose = (template: TemplateOut | null) => {
    setPicking(false)
    start(template)
  }
  const others = (templates.data ?? []).filter((t) => t.id !== planned?.id)
  const startedAt = draft
    ? new Date(draft.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className="page stack">
      <div className="row spread">
        <div>
          <h1>{today.data ? DAY_NAMES[today.data.weekday] : 'Today'}</h1>
          <div className="muted">{today.data?.date}</div>
        </div>
      </div>
      {t?.week && (
        <div className="card week-card">
          <div className="row spread">
            <strong>
              Week {t.week.week}
              {t.week.phase ? ` · ${t.week.phase}` : ''}
            </strong>
            <span>
              {t.week.done_km} / {t.week.target_km ?? '–'} km
            </span>
          </div>
          {t.week.flags.length > 0 && (
            <div className="chips">
              {t.week.flags.map((f) => (
                <span key={f} className="badge badge-pr">
                  {f}
                </span>
              ))}
            </div>
          )}
          {t.week.target_km ? (
            <div className="progress">
              <i style={{ width: `${Math.min(100, (100 * t.week.done_km) / t.week.target_km)}%` }} />
            </div>
          ) : null}
        </div>
      )}
      {error && <div className="banner">{error}</div>}
      {(t?.day_notes ?? []).map((note) => (
        <div key={note} className="card muted">
          📝 {note}
        </div>
      ))}
      {(t?.runs ?? []).map((run) => (
        <SessionCard key={run.id} session={run} />
      ))}
      {planned && (
        <div className="card stack">
          <strong>🏋️ {planned.name}</strong>
          <span className="muted">{planned.slots.map((s) => s.exercise_name).join(' · ') || 'No exercises'}</span>
        </div>
      )}
      {t?.strength_hint && <div className="card hint">🏋️ {t.strength_hint}</div>}

      {draft ? (
        <div className="card stack">
          <strong>Workout in progress</strong>
          <span className="muted">
            {draft.title ?? 'Workout'} · started {startedAt}
          </span>
          <button className="btn-primary btn-block" onClick={() => navigate('/log')}>
            Resume workout
          </button>
          <button
            className="btn-danger btn-block"
            onClick={() => window.confirm('Discard the workout in progress?') && setDraft(null)}
          >
            Discard
          </button>
        </div>
      ) : (
        <>
          <button className="btn-primary btn-block start-btn" disabled={starting} onClick={() => setPicking(true)}>
            {starting ? 'Starting…' : 'Start workout'}
          </button>
          {picking && (
            <div className="sheet-backdrop" onClick={() => setPicking(false)}>
              <div className="sheet stack" onClick={(e) => e.stopPropagation()}>
                <div className="row spread">
                  <strong>Start workout</strong>
                  <button className="btn-small" onClick={() => setPicking(false)}>
                    Close
                  </button>
                </div>
                <div className="sheet-list">
                  {planned && (
                    <button className="btn-primary btn-block list-item" onClick={() => choose(planned)}>
                      {planned.name} <span className="planned-tag">· planned today</span>
                    </button>
                  )}
                  {others.map((tpl) => (
                    <button key={tpl.id} className="btn-block list-item" onClick={() => choose(tpl)}>
                      {tpl.name}
                    </button>
                  ))}
                  <button className="btn-block list-item" onClick={() => choose(null)}>
                    Empty workout
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      <WeeklyLoadCard />

      {t && t.routines.length > 0 && <TodayRoutines day={t.date} planned={t.routines} />}
      <RecoveryCard />
    </div>
  )
}
