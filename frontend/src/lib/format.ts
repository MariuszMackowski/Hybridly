/** Format a weight without trailing zeros (62.5, 60). */
export const kg = (value: number | null) => (value === null ? '–' : `${Number(value.toFixed(2))}`)

/** Unit label of an exercise measure. */
export const MEASURE_UNIT = { reps: 'reps', time: 's', distance: 'm' } as const

/** Compact "60 × 8", "45 s" or "40 m" representation of a set. */
export function setLabel(
  weightKg: number | null,
  reps: number | null,
  seconds: number | null,
  distanceM: number | null = null,
): string {
  const amount = seconds !== null ? `${seconds} s` : distanceM !== null ? `${kg(distanceM)} m` : null
  if (amount !== null && reps === null) return weightKg ? `${kg(weightKg)} kg · ${amount}` : amount
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

/** "h:mm:ss" or "mm:ss" from seconds. */
export function formatDuration(seconds: number): string {
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const ss = String(total % 60).padStart(2, '0')
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

/** Pace "m:ss" (per km) from seconds per km. */
export function formatPace(secondsPerKm: number | null): string {
  if (secondsPerKm === null || !Number.isFinite(secondsPerKm)) return '–'
  const total = Math.round(secondsPerKm)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** Distance in km with two decimals. */
export function formatDistance(meters: number | null): string {
  return meters === null ? '–' : `${(meters / 1000).toFixed(2)} km`
}

/** Pace for runs, km/h for everything else. */
export function speedLabel(a: { sport: string; avg_pace_s_per_km: number | null; avg_speed: number | null }): string {
  if (a.sport === 'run') return `${formatPace(a.avg_pace_s_per_km)} /km`
  return a.avg_speed ? `${(a.avg_speed * 3.6).toFixed(1)} km/h` : '–'
}
