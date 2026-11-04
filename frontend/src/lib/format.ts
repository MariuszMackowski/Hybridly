/** Format a weight without trailing zeros (62.5, 60). */
export const kg = (value: number | null) => (value === null ? '–' : `${Number(value.toFixed(2))}`)

/** Compact "60 × 8" or "45 s" representation of a set. */
export function setLabel(weightKg: number | null, reps: number | null, seconds: number | null): string {
  if (seconds !== null && reps === null) return weightKg ? `${kg(weightKg)} kg · ${seconds} s` : `${seconds} s`
  if (reps === null) return '–'
  return `${kg(weightKg ?? 0)} × ${reps}`
}

/** Local date-time like "Mon 03.11.2026 07:30". */
export function dateTime(iso: string): string {
  const d = new Date(iso)
  const day = d.toLocaleDateString('en-GB', { weekday: 'short' })
  const date = d.toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const time = d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })
  return `${day} ${date} ${time}`
}

/** Minutes between two ISO timestamps, or null. */
export function durationMin(start: string, end: string | null): number | null {
  return end ? Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000) : null
}
