import { formatPace } from './format'

/** "5:40–6:20 /km" or "4:58 /km"; null without a target. */
export function paceRangeLabel(minS: number | null, maxS: number | null): string | null {
  if (minS === null || maxS === null) return null
  return minS === maxS ? `${formatPace(minS)} /km` : `${formatPace(minS)}–${formatPace(maxS)} /km`
}

/** Segments for the HR-zone bar; null without HR data. */
export function zoneBar(below: number | null, inside: number | null, above: number | null) {
  if (below === null || inside === null || above === null) return null
  return [
    { key: 'below', pct: below },
    { key: 'in', pct: inside },
    { key: 'above', pct: above },
  ]
}

/** Status of a planned session relative to today (ISO dates compare as strings). */
export function sessionStatus(
  session: { date: string; activity_id: number | null },
  today: string,
): 'done' | 'missed' | 'today' | 'upcoming' {
  if (session.activity_id !== null) return 'done'
  if (session.date === today) return 'today'
  return session.date < today ? 'missed' : 'upcoming'
}
