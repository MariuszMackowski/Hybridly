import type { HistoryItem } from '../../api/types'

const WARSAW_DAY = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Warsaw' })

/** "YYYY-MM-DD" of an instant in Europe/Warsaw. */
export const localDay = (iso: string) => WARSAW_DAY.format(new Date(iso))

/** Calendar arithmetic on "YYYY-MM-DD" strings (UTC noon avoids DST edges). */
function shift(day: string, days: number): string {
  const d = new Date(`${day}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

const weekday = (day: string) => (new Date(`${day}T12:00:00Z`).getUTCDay() + 6) % 7 // Mon = 0

/** ISO-8601 week number, its year and Monday of a local day. */
export function isoWeek(day: string): { year: number; week: number; monday: string } {
  const monday = shift(day, -weekday(day))
  const thursday = shift(monday, 3)
  const year = Number(thursday.slice(0, 4))
  const jan4 = `${year}-01-04`
  const week1Monday = shift(jan4, -weekday(jan4))
  const diffDays = (Date.parse(`${monday}T12:00:00Z`) - Date.parse(`${week1Monday}T12:00:00Z`)) / 86_400_000
  return { year, week: diffDays / 7 + 1, monday }
}

export type WeekGroup = {
  key: string
  week: number
  monday: string
  sunday: string
  gym: number
  run: number
  walk: number
  other: number
  km: number
  items: HistoryItem[]
}

/** Split a newest-first list into ISO weeks with per-week counts and distance. */
export function groupByWeek(items: HistoryItem[]): WeekGroup[] {
  const groups: WeekGroup[] = []
  for (const item of items) {
    const { year, week, monday } = isoWeek(localDay(item.started_at))
    const key = `${year}-${week}`
    let group = groups.at(-1)
    if (!group || group.key !== key) {
      group = { key, week, monday, sunday: shift(monday, 6), gym: 0, run: 0, walk: 0, other: 0, km: 0, items: [] }
      groups.push(group)
    }
    group.items.push(item)
    const bucket = item.sport === 'gym' || item.sport === 'run' || item.sport === 'walk' ? item.sport : 'other'
    group[bucket] += 1
    group.km = Math.round((group.km + (item.distance_m ?? 0) / 1000) * 10) / 10
  }
  return groups
}

/** Monday-first weeks of a month; days outside the month are null. */
export function monthGrid(year: number, month: number): (string | null)[][] {
  const first = `${year}-${String(month).padStart(2, '0')}-01`
  const days: (string | null)[] = Array(weekday(first)).fill(null)
  for (let day = first; day.slice(5, 7) === first.slice(5, 7); day = shift(day, 1)) days.push(day)
  while (days.length % 7) days.push(null)
  return Array.from({ length: days.length / 7 }, (_, i) => days.slice(i * 7, i * 7 + 7))
}
