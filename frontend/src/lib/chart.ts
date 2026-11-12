type Series = (number | null)[]

/** Centered rolling median (odd window) that smooths GPS spikes; null stays null. */
export function rollingMedian(values: Series, window: number): Series {
  const half = Math.floor(window / 2)
  return values.map((v, i) => {
    if (v === null) return null
    const around = values
      .slice(Math.max(0, i - half), i + half + 1)
      .filter((x): x is number => x !== null)
      .sort((a, b) => a - b)
    return around[Math.floor(around.length / 2)]
  })
}

/** 5th–95th percentile range with padding, so outliers do not flatten the line. */
export function robustDomain(values: Series): [number, number] | undefined {
  const sorted = values.filter((v): v is number => v !== null).sort((a, b) => a - b)
  if (sorted.length < 10) return undefined
  const at = (q: number) => sorted[Math.floor(q * (sorted.length - 1))]
  const pad = (at(0.95) - at(0.05)) * 0.15 || 10
  return [Math.max(0, at(0.05) - pad), at(0.95) + pad]
}

/** Pin values to the domain so lines never leave the chart. */
export function clampTo(values: Series, [lo, hi]: [number, number]): Series {
  return values.map((v) => (v === null ? null : Math.min(hi, Math.max(lo, v))))
}

/** Shared look of recharts axes and tooltips on the dark theme. */
export const AXIS_PROPS = { stroke: '#8a90a0', fontSize: 10, tickLine: false } as const
export const TOOLTIP_STYLE = { background: '#181b22', border: '1px solid #2a2f3a' } as const

/** "YYYY-MM-DD" → "09.11" (or "09.11.25" when years differ across the chart). */
export const shortDay = (day: string, withYear = false) =>
  `${day.slice(8, 10)}.${day.slice(5, 7)}${withYear ? `.${day.slice(2, 4)}` : ''}`
