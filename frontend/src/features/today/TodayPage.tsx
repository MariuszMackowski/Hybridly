import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTemplates, useToday } from '../../api/hooks'
import type { TemplateOut } from '../../api/types'
import { startDraft, useDraft } from '../logger/useDraft'

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function TodayPage() {
  const today = useToday()
  const templates = useTemplates()
  const { draft, setDraft } = useDraft()
  const navigate = useNavigate()
  const [starting, setStarting] = useState(false)
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

  const planned = today.data?.template ?? null
  const others = (templates.data ?? []).filter((t) => t.id !== planned?.id)
  const startedAt = draft
    ? new Date(draft.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className="page stack">
      <div>
        <h1>{today.data ? DAY_NAMES[today.data.weekday] : 'Today'}</h1>
        <div className="muted">{today.data?.date}</div>
      </div>
      {error && <div className="banner">{error}</div>}

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
          {planned && (
            <div className="card stack">
              <span className="muted">Planned today</span>
              <button className="btn-primary btn-block" disabled={starting} onClick={() => start(planned)}>
                Start {planned.name}
              </button>
            </div>
          )}
          <div className="card stack">
            <span className="muted">{planned ? 'Other templates' : 'Templates'}</span>
            {others.map((t) => (
              <button key={t.id} className="btn-block" disabled={starting} onClick={() => start(t)}>
                {t.name}
              </button>
            ))}
            <button className="btn-block" disabled={starting} onClick={() => start(null)}>
              Empty workout
            </button>
          </div>
        </>
      )}
    </div>
  )
}
