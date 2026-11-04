import { useState } from 'react'
import { useCalendar } from '../../api/hooks'
import { localDay, monthGrid } from './weeks'

export const KIND_COLOR: Record<string, string> = {
  gym: '#ff7a1a',
  run: '#38bdf8',
  walk: '#22c55e',
  other: '#8a90a0',
}
const DAY_NAMES = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

/** Month view with a coloured dot per training kind; tap a day to select it. */
export default function Calendar(props: { selected: string | null; onSelect: (day: string | null) => void }) {
  const today = localDay(new Date().toISOString())
  const [month, setMonth] = useState(today.slice(0, 7))
  const [year, monthNo] = month.split('-').map(Number)
  const marks = new Map((useCalendar(month).data ?? []).map((d) => [d.day, d.kinds]))
  const move = (delta: number) => {
    const d = new Date(Date.UTC(year, monthNo - 1 + delta, 1))
    setMonth(d.toISOString().slice(0, 7))
  }
  const title = new Date(Date.UTC(year, monthNo - 1, 1)).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })

  return (
    <div className="card calendar">
      <div className="row spread">
        <button className="btn-small" onClick={() => move(-1)} aria-label="Previous month">
          ‹
        </button>
        <strong>{title}</strong>
        <button className="btn-small" onClick={() => move(1)} aria-label="Next month">
          ›
        </button>
      </div>
      <div className="cal-grid">
        {DAY_NAMES.map((d) => (
          <span key={d} className="cal-head muted">
            {d}
          </span>
        ))}
        {monthGrid(year, monthNo)
          .flat()
          .map((day, i) =>
            day ? (
              <button
                key={day}
                className={`cal-day${day === props.selected ? ' selected' : ''}${day === today ? ' today' : ''}`}
                onClick={() => props.onSelect(day === props.selected ? null : day)}
              >
                <span>{Number(day.slice(8))}</span>
                <span className="cal-dots">
                  {(marks.get(day) ?? []).map((k) => (
                    <i key={k} style={{ background: KIND_COLOR[k] }} />
                  ))}
                </span>
              </button>
            ) : (
              <span key={`pad${i}`} />
            ),
          )}
      </div>
      <div className="row cal-legend muted">
        {Object.entries(KIND_COLOR).map(([k, c]) => (
          <span key={k}>
            <i style={{ background: c }} /> {k}
          </span>
        ))}
      </div>
    </div>
  )
}
