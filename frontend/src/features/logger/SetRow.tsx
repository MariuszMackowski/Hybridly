import { useEffect, useState } from 'react'
import type { Measure } from '../../api/types'
import { parseDecimal } from '../../lib/decimal'
import { kg, setLabel } from '../../lib/format'
import type { DraftSet, SetValues } from './draft'

const ARROWS = { increase: '↑', hold: '=', reduce: '↓' } as const
const KIND_CLASS = { increase: 'good', hold: 'muted', reduce: 'bad' } as const

/** Text input that keeps what the user types but reports the parsed number. */
function NumberInput(props: {
  value: number | null
  decimal?: boolean
  placeholder?: string
  onChange: (value: number | null) => void
}) {
  const [text, setText] = useState(props.value === null ? '' : kg(props.value))
  useEffect(() => {
    if (parseDecimal(text) !== props.value) setText(props.value === null ? '' : kg(props.value))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.value])
  return (
    <input
      className="set-input"
      inputMode={props.decimal ? 'decimal' : 'numeric'}
      placeholder={props.placeholder}
      value={text}
      onChange={(e) => {
        setText(e.target.value)
        props.onChange(parseDecimal(e.target.value))
      }}
    />
  )
}

export default function SetRow(props: {
  label: string
  row: DraftSet
  measure: Measure
  onChange: (patch: Partial<SetValues>) => void
  onToggle: () => void
  onRemove: () => void
}) {
  const { row, measure } = props
  const prev = row.previous ? setLabel(row.previous.weightKg, row.previous.reps, row.previous.seconds) : '–'
  return (
    <div className={`set-row${row.done ? ' done' : ''}${row.isWarmup ? ' warmup' : ''}`}>
      <span className="set-label">{props.label}</span>
      <span className="set-prev muted">{prev}</span>
      <span className={`set-sugg ${row.suggestion ? KIND_CLASS[row.suggestion.kind] : 'muted'}`}>
        {row.suggestion
          ? `${row.suggestion.reason === 'fatigued' ? '💤' : ARROWS[row.suggestion.kind]} ${kg(row.suggestion.weightKg)}×${row.suggestion.reps}`
          : ''}
      </span>
      <NumberInput value={row.weightKg} decimal placeholder="kg" onChange={(v) => props.onChange({ weightKg: v })} />
      {measure === 'time' ? (
        <NumberInput value={row.seconds} placeholder="s" onChange={(v) => props.onChange({ seconds: v })} />
      ) : (
        <NumberInput value={row.reps} placeholder="reps" onChange={(v) => props.onChange({ reps: v })} />
      )}
      <button className={`set-done${row.done ? ' on' : ''}`} onClick={props.onToggle} aria-label="Done">
        ✓
      </button>
      <button className="set-remove" onClick={props.onRemove} aria-label="Remove set">
        ✕
      </button>
    </div>
  )
}
