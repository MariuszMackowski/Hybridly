import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useActivePlan, useImportPlan, usePlanInstructions, useToday } from '../../api/hooks'
import type { PlanWeek } from '../../api/types'
import { sessionStatus } from '../../lib/plan'
import { targets } from './SessionCard'
import RoutinesEditor from './RoutinesEditor'

const STATUS_ICON = { done: '✓', missed: '✗', today: '•', upcoming: '' } as const
const weekday = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'numeric' })

/** One plan week; the current week starts expanded. */
function WeekBlock({ week, today, open }: { week: PlanWeek; today: string; open: boolean }) {
  const done = week.sessions.filter((s) => s.activity_id !== null).length
  return (
    <details className="card" open={open}>
      <summary>
        <strong>Week {week.week}</strong>
        <span className="muted">
          {weekday(week.start)} · {week.phase} · {done}/{week.sessions.length}
          {week.target_km ? ` · ${week.target_km} km` : ''}
        </span>
        {week.flags.map((f) => (
          <span key={f} className="badge badge-pr">
            {f}
          </span>
        ))}
      </summary>
      {week.note && <p className="muted">{week.note}</p>}
      {week.sessions.map((s) => {
        const status = sessionStatus(s, today)
        return (
          <div key={s.id} className="session-row">
            <span className="when">{weekday(s.date)}</span>
            <div>
              <div>{s.title}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {targets(s).join(' · ')}
              </div>
            </div>
            {s.activity_id !== null ? (
              <Link to={`/runs/${s.activity_id}`} className={`st-${status}`}>
                {STATUS_ICON[status]} ›
              </Link>
            ) : (
              <span className={`st-${status}`}>{STATUS_ICON[status]}</span>
            )}
          </div>
        )
      })}
      {week.day_notes.map((n) => (
        <p key={n.date + n.text} className="muted">
          📝 {weekday(n.date)}: {n.text}
        </p>
      ))}
    </details>
  )
}

/** Import from file or pasted YAML. */
function ImportPlan() {
  const importPlan = useImportPlan()
  const [text, setText] = useState('')
  const file = useRef<HTMLInputElement>(null)
  return (
    <div className="card stack">
      <strong>Import plan</strong>
      <input
        ref={file}
        type="file"
        accept=".yaml,.yml,.txt"
        hidden
        onChange={async (e) => {
          const f = e.target.files?.[0]
          if (f) importPlan.mutate(await f.text())
          e.target.value = ''
        }}
      />
      <button onClick={() => file.current?.click()} disabled={importPlan.isPending}>
        Choose YAML file
      </button>
      <textarea className="mono" placeholder="…or paste the YAML from your coach" value={text} onChange={(e) => setText(e.target.value)} />
      <button className="btn-primary" disabled={!text.trim() || importPlan.isPending} onClick={() => importPlan.mutate(text)}>
        Import pasted plan
      </button>
      {importPlan.isError && <div className="banner">{importPlan.error.message}</div>}
      {importPlan.data && (
        <span className="good">
          Imported {importPlan.data.name}: {importPlan.data.weeks} weeks, {importPlan.data.sessions} runs, active from{' '}
          {importPlan.data.effective_from}
        </span>
      )}
    </div>
  )
}

/** Copyable format description for the AI coach (textarea fallback on plain http). */
function CoachInstructions() {
  const text = usePlanInstructions().data?.text ?? ''
  const area = useRef<HTMLTextAreaElement>(null)
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      area.current?.select()
      document.execCommand('copy')
    }
    setCopied(true)
  }
  return (
    <details className="card">
      <summary>
        <strong>Instructions for your AI coach</strong>
      </summary>
      <div className="stack">
        <span className="muted">Paste this to the coach so the plan comes back in a format Hybridly can import.</span>
        <textarea ref={area} className="mono" readOnly value={text} onFocus={(e) => e.target.select()} />
        <button onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button>
      </div>
    </details>
  )
}

export default function PlanPage() {
  const plan = useActivePlan()
  const today = useToday().data?.date ?? new Date().toISOString().slice(0, 10)
  const p = plan.data
  const current = p?.weeks.find((w) => w.start <= today && today < addDays(w.start, 7))
  return (
    <div className="page stack">
      <h1>Plan</h1>
      {p ? (
        <div className="card stack">
          <strong>{p.name}</strong>
          {p.goal && (
            <span className="muted">
              🎯 {p.goal.race} · {p.goal.date} · {p.goal.target_time}
            </span>
          )}
          <span className="muted">Active from {p.effective_from}</span>
        </div>
      ) : (
        !plan.isLoading && <p className="muted">No running plan yet — import one below.</p>
      )}
      {p?.weeks.map((w) => (
        <WeekBlock key={w.week} week={w} today={today} open={w === current} />
      ))}
      <ImportPlan />
      <CoachInstructions />
      <RoutinesEditor />
    </div>
  )
}

/** ISO date + n days. */
function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}
