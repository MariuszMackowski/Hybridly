import type {
  Block,
  ExerciseContext,
  Measure,
  SuggestionKind,
  TemplateOut,
  WorkoutCreate,
} from '../../api/types'

export type SetValues = {
  weightKg: number | null
  reps: number | null
  seconds: number | null
  /** Optional so drafts saved before distance logging still load. */
  distanceM?: number | null
}

export type DraftSet = SetValues & {
  done: boolean
  isWarmup: boolean
  previous: SetValues | null
  suggestion: { weightKg: number; reps: number; kind: SuggestionKind; reason?: string | null } | null
}

export type DraftExercise = {
  key: string
  exerciseId: number
  name: string
  measure: Measure
  perSide: boolean
  /** Grip options and the chosen one; optional so older saved drafts still load. */
  grips?: string[]
  grip?: string | null
  alternatives: { id: number; name: string }[]
  warmupSets: number
  sets: number
  repMin: number
  repMax: number
  supersetGroup: number | null
  block: Block
  rows: DraftSet[]
}

export type WorkoutDraft = {
  version: 1
  clientId: string
  templateId: number | null
  title: string | null
  startedAt: string
  /** When the last set was ticked; optional so drafts saved before this field still load. */
  restStartedAt?: string | null
  warmup: { text: string; done: boolean }[]
  cooldown: { text: string; done: boolean }[]
  exercises: DraftExercise[]
}

type Targets = Pick<DraftExercise, 'warmupSets' | 'sets' | 'repMin' | 'repMax'>

const DEFAULT_TARGETS: Targets = { warmupSets: 0, sets: 3, repMin: 8, repMax: 10 }
const EMPTY: SetValues = { weightKg: null, reps: null, seconds: null, distanceM: null }

let keyCounter = 0
/** Unique key for an exercise card within a draft. */
const nextKey = () => `ex-${Date.now().toString(36)}-${keyCounter++}`

/** Build rows: warm-ups from previous warm-ups, working rows from suggestion or previous. */
function buildRows(ctx: ExerciseContext, t: Targets): DraftSet[] {
  const prevSets = ctx.previous?.sets ?? []
  const toValues = (s: (typeof prevSets)[number]): SetValues => ({
    weightKg: s.weight_kg, reps: s.reps, seconds: s.seconds, distanceM: s.distance_m,
  })
  const prevWarmups = prevSets.filter((s) => s.is_warmup).map(toValues)
  const prevWorking = prevSets.filter((s) => !s.is_warmup).map(toValues)
  const warmups: DraftSet[] = Array.from({ length: t.warmupSets }, (_, i) => ({
    ...(prevWarmups[i] ?? EMPTY), done: false, isWarmup: true,
    previous: prevWarmups[i] ?? null, suggestion: null,
  }))
  const working: DraftSet[] = Array.from({ length: t.sets }, (_, i) => {
    const s = ctx.suggestions[i]
    const suggestion = s ? { weightKg: s.weight_kg, reps: s.reps, kind: s.kind, reason: s.reason ?? null } : null
    const previous = prevWorking[i] ?? null
    const values = suggestion
      ? { weightKg: suggestion.weightKg, reps: suggestion.reps, seconds: null, distanceM: null }
      : (previous ?? EMPTY)
    return { ...values, done: false, isWarmup: false, previous, suggestion }
  })
  return [...warmups, ...working]
}

/** Copy exercise identity from a context onto a card and rebuild its rows. */
export function withContext(ex: DraftExercise, ctx: ExerciseContext): DraftExercise {
  return {
    ...ex,
    exerciseId: ctx.exercise.id,
    name: ctx.exercise.name,
    measure: ctx.exercise.measure,
    perSide: ctx.exercise.per_side,
    grips: ctx.exercise.grips,
    grip: ctx.grip,
    rows: buildRows(ctx, ex),
  }
}

/** Fresh exercise card from a context and targets. */
function newExercise(ctx: ExerciseContext, t: Targets, extra: Partial<DraftExercise> = {}): DraftExercise {
  const base: DraftExercise = {
    key: nextKey(), exerciseId: ctx.exercise.id, name: ctx.exercise.name,
    measure: ctx.exercise.measure, perSide: ctx.exercise.per_side, alternatives: [],
    supersetGroup: null, block: 'main', rows: [], ...t, ...extra,
  }
  return withContext(base, ctx)
}

/** Create a draft from a template (or empty) and per-exercise contexts. */
export function createDraft(
  template: TemplateOut | null,
  contexts: Record<number, ExerciseContext>,
  now: Date,
  clientId: string,
): WorkoutDraft {
  return {
    version: 1,
    clientId,
    templateId: template?.id ?? null,
    title: template?.name ?? null,
    startedAt: now.toISOString(),
    warmup: (template?.warmup_items ?? []).map((text) => ({ text, done: false })),
    cooldown: (template?.cooldown_items ?? []).map((text) => ({ text, done: false })),
    exercises: (template?.slots ?? []).map((slot) =>
      newExercise(
        contexts[slot.exercise_id],
        { warmupSets: slot.warmup_sets, sets: slot.sets, repMin: slot.rep_min, repMax: slot.rep_max },
        {
          alternatives: [{ id: slot.exercise_id, name: slot.exercise_name }, ...slot.alternatives],
          supersetGroup: slot.superset_group,
          block: slot.block,
        },
      ),
    ),
  }
}

/** Apply a change to one exercise card. */
function mapExercise(d: WorkoutDraft, key: string, fn: (ex: DraftExercise) => DraftExercise): WorkoutDraft {
  return { ...d, exercises: d.exercises.map((ex) => (ex.key === key ? fn(ex) : ex)) }
}

/** Apply a change to one row of one exercise card. */
function mapRow(d: WorkoutDraft, key: string, index: number, fn: (row: DraftSet) => DraftSet): WorkoutDraft {
  return mapExercise(d, key, (ex) => ({ ...ex, rows: ex.rows.map((r, i) => (i === index ? fn(r) : r)) }))
}

/** Whether swapping/removing this card would discard sets the user already ticked. */
export const hasLoggedSets = (ex: DraftExercise) => ex.rows.some((r) => r.done)

export const swapExercise = (d: WorkoutDraft, key: string, ctx: ExerciseContext) =>
  mapExercise(d, key, (ex) => withContext(ex, ctx))

/** Change only the grip label, keeping rows (used once sets are already logged). */
export const setGrip = (d: WorkoutDraft, key: string, grip: string | null) =>
  mapExercise(d, key, (ex) => ({ ...ex, grip }))

export const addExercise = (d: WorkoutDraft, ctx: ExerciseContext): WorkoutDraft => ({
  ...d,
  exercises: [...d.exercises, newExercise(ctx, DEFAULT_TARGETS)],
})

export const removeExercise = (d: WorkoutDraft, key: string): WorkoutDraft =>
  normalizeGroups({ ...d, exercises: d.exercises.filter((ex) => ex.key !== key) })

/** Index just past the superset block containing `key` (just past the card when not in one). */
function blockEnd(exercises: DraftExercise[], key: string): number {
  const i = exercises.findIndex((e) => e.key === key)
  const group = exercises[i].supersetGroup
  let end = i + 1
  if (group !== null) while (end < exercises.length && exercises[end].supersetGroup === group) end++
  return end
}

/** A superset of one is just a normal card: clear groups left with a single exercise. */
function normalizeGroups(d: WorkoutDraft): WorkoutDraft {
  const sizes = new Map<number, number>()
  d.exercises.forEach((e) => e.supersetGroup !== null && sizes.set(e.supersetGroup, (sizes.get(e.supersetGroup) ?? 0) + 1))
  const lone = (e: DraftExercise) => e.supersetGroup !== null && sizes.get(e.supersetGroup) === 1
  return d.exercises.some(lone)
    ? { ...d, exercises: d.exercises.map((e) => (lone(e) ? { ...e, supersetGroup: null } : e)) }
    : d
}

/** Put `key` into a superset group (a new one if it has none) and return the group. */
function ensureGroup(d: WorkoutDraft, key: string): [WorkoutDraft, number, DraftExercise] | null {
  const anchor = d.exercises.find((e) => e.key === key)
  if (!anchor) return null // removed while the picker was loading
  if (anchor.supersetGroup !== null) return [d, anchor.supersetGroup, anchor]
  const group = Math.max(0, ...d.exercises.map((e) => e.supersetGroup ?? 0)) + 1
  return [mapExercise(d, key, (e) => ({ ...e, supersetGroup: group })), group, { ...anchor, supersetGroup: group }]
}

/** Insert an exercise right after the superset block of `key`. */
function insertAfterBlock(exercises: DraftExercise[], key: string, ex: DraftExercise): DraftExercise[] {
  const end = blockEnd(exercises, key)
  return [...exercises.slice(0, end), ex, ...exercises.slice(end)]
}

/** Superset `key` with a newly added exercise (same set/rep targets as the anchor). */
export function supersetWithNew(d: WorkoutDraft, key: string, ctx: ExerciseContext): WorkoutDraft {
  const grouped = ensureGroup(d, key)
  if (!grouped) return d
  const [base, group, anchor] = grouped
  const added = newExercise(
    ctx,
    { warmupSets: 0, sets: anchor.sets, repMin: anchor.repMin, repMax: anchor.repMax },
    { supersetGroup: group, block: anchor.block },
  )
  return { ...base, exercises: insertAfterBlock(base.exercises, key, added) }
}

/** Superset `key` with an exercise already in the workout, moving it next to the block. */
export function supersetWithExisting(d: WorkoutDraft, key: string, otherKey: string): WorkoutDraft {
  const grouped = key === otherKey ? null : ensureGroup(d, key)
  const other = d.exercises.find((e) => e.key === otherKey)
  if (!grouped || !other) return d
  const [base, group, anchor] = grouped
  const moved = { ...other, supersetGroup: group, block: anchor.block }
  const rest = base.exercises.filter((e) => e.key !== otherKey)
  return normalizeGroups({ ...base, exercises: insertAfterBlock(rest, key, moved) })
}

/** Take an exercise out of its superset and place it right after the block. */
export function unlinkSuperset(d: WorkoutDraft, key: string): WorkoutDraft {
  const ex = d.exercises.find((e) => e.key === key)
  if (!ex || ex.supersetGroup === null) return d
  const end = blockEnd(d.exercises, key) - 1 // block end once `ex` is taken out
  const rest = d.exercises.filter((e) => e.key !== key)
  return normalizeGroups({ ...d, exercises: [...rest.slice(0, end), { ...ex, supersetGroup: null }, ...rest.slice(end)] })
}

/** Add a working set (copy of the last row) or an empty warm-up after the last warm-up. */
export function addSet(d: WorkoutDraft, key: string, warmup = false): WorkoutDraft {
  return mapExercise(d, key, (ex) => {
    const rows = [...ex.rows]
    if (warmup) {
      const at = rows.filter((r) => r.isWarmup).length
      rows.splice(at, 0, { ...EMPTY, done: false, isWarmup: true, previous: null, suggestion: null })
    } else {
      const last = rows.filter((r) => !r.isWarmup).at(-1)
      const values = last
        ? { weightKg: last.weightKg, reps: last.reps, seconds: last.seconds, distanceM: last.distanceM ?? null }
        : EMPTY
      rows.push({ ...values, done: false, isWarmup: false, previous: null, suggestion: null })
    }
    return { ...ex, rows }
  })
}

export const removeSet = (d: WorkoutDraft, key: string, index: number) =>
  mapExercise(d, key, (ex) => ({ ...ex, rows: ex.rows.filter((_, i) => i !== index) }))

export const updateSet = (d: WorkoutDraft, key: string, index: number, patch: Partial<SetValues>) =>
  mapRow(d, key, index, (r) => ({ ...r, ...patch }))

/** Tick/untick a set; ticking (re)starts the rest timer. */
export function toggleDone(d: WorkoutDraft, key: string, index: number, now: Date = new Date()): WorkoutDraft {
  const row = d.exercises.find((ex) => ex.key === key)?.rows[index]
  const next = mapRow(d, key, index, (r) => ({ ...r, done: !r.done }))
  return row && !row.done ? { ...next, restStartedAt: now.toISOString() } : next
}

export function toggleChecklist(d: WorkoutDraft, list: 'warmup' | 'cooldown', index: number): WorkoutDraft {
  return { ...d, [list]: d[list].map((item, i) => (i === index ? { ...item, done: !item.done } : item)) }
}

/** Consecutive exercises sharing a superset group render as one card. */
export function displayOrder(d: WorkoutDraft): { group: DraftExercise[] }[] {
  const groups: { group: DraftExercise[] }[] = []
  for (const ex of d.exercises) {
    const last = groups.at(-1)?.group
    if (last && ex.supersetGroup !== null && last[0].supersetGroup === ex.supersetGroup) last.push(ex)
    else groups.push({ group: [ex] })
  }
  return groups
}

/** Whether a row holds a loggable result for its exercise. */
const isLoggable = (ex: DraftExercise, r: DraftSet) => {
  const value = { reps: r.reps, time: r.seconds, distance: r.distanceM ?? null }[ex.measure]
  return r.done && value !== null && value > 0
}

/** Payload for POST /api/workouts: only completed rows, empty exercises dropped. */
export function toPayload(d: WorkoutDraft, endedAt: Date): WorkoutCreate {
  return {
    client_id: d.clientId,
    started_at: d.startedAt,
    ended_at: endedAt.toISOString(),
    template_id: d.templateId,
    title: d.title,
    note: null,
    exercises: d.exercises
      .map((ex) => ({
        exercise_id: ex.exerciseId,
        superset_group: ex.supersetGroup,
        grip: ex.grip ?? null,
        sets: ex.rows
          .filter((r) => isLoggable(ex, r))
          .map((r) => ({
            weight_kg: r.weightKg,
            reps: ex.measure === 'reps' ? r.reps : null,
            seconds: ex.measure === 'time' ? r.seconds : null,
            distance_m: ex.measure === 'distance' ? (r.distanceM ?? null) : null,
            is_warmup: r.isWarmup,
          })),
      }))
      .filter((ex) => ex.sets.length > 0),
  }
}
