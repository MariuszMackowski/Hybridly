import { useEffect, useState } from 'react'
import { useSaveWeek, useWeek } from '../../api/hooks'
import type { TemplateOut, WeekItem } from '../../api/types'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** Seven selects mapping weekdays to suggested templates. */
export default function WeekEditor(props: { templates: TemplateOut[] }) {
  const week = useWeek()
  const save = useSaveWeek()
  const [items, setItems] = useState<WeekItem[]>([])
  useEffect(() => {
    if (week.data) setItems(week.data)
  }, [week.data])

  const setDay = (weekday: number, templateId: number | null) =>
    setItems((list) => list.map((i) => (i.weekday === weekday ? { ...i, template_id: templateId } : i)))

  return (
    <div className="card stack">
      <strong>Week plan</strong>
      <span className="muted">Suggestion shown on Today — you can start any template any day.</span>
      {items.map((item) => (
        <div key={item.weekday} className="row">
          <span style={{ width: 44 }}>{DAYS[item.weekday]}</span>
          <select
            value={item.template_id ?? ''}
            onChange={(e) => setDay(item.weekday, e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {props.templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      ))}
      <button
        className="btn-primary"
        disabled={save.isPending}
        onClick={() => save.mutate(items.map(({ weekday, template_id }) => ({ weekday, template_id })))}
      >
        {save.isSuccess && !save.isPending ? 'Saved ✓' : 'Save week'}
      </button>
    </div>
  )
}
