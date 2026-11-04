const WHITE = [230, 232, 236]
const YELLOW = [250, 204, 21]
const RED = [239, 68, 68]

/** Linear mix of two RGB colours. */
const mix = (a: number[], b: number[], t: number) => a.map((v, i) => Math.round(v + (b[i] - v) * t))

/** Fatigue level 0..1 → white (fresh) → yellow → red (just hammered). */
export function fatigueColor(level: number): string {
  const l = Math.min(1, Math.max(0, level))
  const [r, g, b] = l <= 0.5 ? mix(WHITE, YELLOW, l / 0.5) : mix(YELLOW, RED, (l - 0.5) / 0.5)
  return `rgb(${r}, ${g}, ${b})`
}

/** Every muscle, most fatigued first. */
export function byFatigue(levels: Record<string, number>): [string, number][] {
  return Object.entries(levels).sort((a, b) => b[1] - a[1])
}

/** Most fatigued muscles first, ignoring ones below 5 %. */
export function topMuscles(levels: Record<string, number>, n: number): [string, number][] {
  return byFatigue(levels)
    .filter(([, v]) => v >= 0.05)
    .slice(0, n)
}

/** "front_delts" → "front delts". */
export const muscleLabel = (m: string) => m.replace('_', ' ')
