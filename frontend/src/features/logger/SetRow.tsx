import { useEffect, useRef, useState } from 'react'
import type { Measure } from '../../api/types'
import { parseDecimal } from '../../lib/decimal'
import { kg, MEASURE_UNIT, setLabel } from '../../lib/format'
import type { DraftSet, SetValues } from './draft'

const ARROWS = { increase: '↑', hold: '=', reduce: '↓' } as const
const KIND_CLASS = { increase: 'good', hold: 'muted', reduce: 'bad' } as const

const show = (value: number | null) => (value === null ? '' : kg(value))

/**
 * Text input that keeps what the user types but reports the parsed number.
 * Focusing clears the field (old value stays as placeholder) so a new number can be typed
 * straight away; leaving it untouched restores the old value.
 */
function NumberInput(props: {
  value: number | null
  decimal?: boolean
  placeholder?: string
  onChange: (value: number | null) => void
}) {
  const [text, setText] = useState(show(props.value))
  const [editing, setEditing] = useState(false)
  const typed = useRef(false)
  useEffect(() => {
    if (!editing && parseDecimal(text) !== props.value) setText(show(props.value))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.value])
  return (
    <input
      className="set-input"
      inputMode={props.decimal ? 'decimal' : 'numeric'}
      placeholder={editing && props.value !== null ? show(props.value) : props.placeholder}
      value={text}
      onFocus={() => {
        typed.current = false
        setEditing(true)
        setText('')
      }}
      onBlur={() => {
        setEditing(false)
        if (!typed.current) setText(show(props.value))
      }}
      onChange={(e) => {
        typed.current = true
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
  const prev = row.previous ? setLabel(row.previous.weightKg, row.previous.reps, row.previous.seconds, row.previous.distanceM) : '–'
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
      {measure === 'time' && (
        <NumberInput value={row.seconds} placeholder={MEASURE_UNIT.time} onChange={(v) => props.onChange({ seconds: v })} />
      )}
      {measure === 'distance' && (
        <NumberInput
          value={row.distanceM ?? null}
          decimal
          placeholder={MEASURE_UNIT.distance}
          onChange={(v) => props.onChange({ distanceM: v })}
        />
      )}
      {measure === 'reps' && (
        <NumberInput value={row.reps} placeholder={MEASURE_UNIT.reps} onChange={(v) => props.onChange({ reps: v })} />
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
