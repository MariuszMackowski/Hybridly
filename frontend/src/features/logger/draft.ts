import type {
  Block,
  ExerciseContext,
  Measure,
  SuggestionKind,
  TemplateOut,
  WorkoutCreate,
} from '../../api/types'

export type SetValues = { weightKg: number | null; reps: number | null; seconds: number | null }

export type DraftSet = SetValues & {
  done: boolean
  isWarmup: boolean
  previous: SetValues | null
  suggestion: { weightKg: number; reps: number; kind: SuggestionKind } | null
}

export type DraftExercise = {
  key: string
  exerciseId: number
  name: string
  measure: Measure
  perSide: boolean
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
  warmup: { text: string; done: boolean }[]
  cooldown: { text: string; done: boolean }[]
  exercises: DraftExercise[]
}

type Targets = Pick<DraftExercise, 'warmupSets' | 'sets' | 'repMin' | 'repMax'>

const DEFAULT_TARGETS: Targets = { warmupSets: 0, sets: 3, repMin: 8, repMax: 10 }
const EMPTY: SetValues = { weightKg: null, reps: null, seconds: null }

let keyCounter = 0
/** Unique key for an exercise card within a draft. */
const nextKey = () => `ex-${Date.now().toString(36)}-${keyCounter++}`

/** Build rows: warm-ups from previous warm-ups, working rows from suggestion or previous. */
function buildRows(ctx: ExerciseContext, t: Targets): DraftSet[] {
  const prevSets = ctx.previous?.sets ?? []
  const toValues = (s: (typeof prevSets)[number]): SetValues => ({
    weightKg: s.weight_kg, reps: s.reps, seconds: s.seconds,
  })
  const prevWarmups = prevSets.filter((s) => s.is_warmup).map(toValues)
  const prevWorking = prevSets.filter((s) => !s.is_warmup).map(toValues)
  const warmups: DraftSet[] = Array.from({ length: t.warmupSets }, (_, i) => ({
    ...(prevWarmups[i] ?? EMPTY), done: false, isWarmup: true,
    previous: prevWarmups[i] ?? null, suggestion: null,
  }))
  const working: DraftSet[] = Array.from({ length: t.sets }, (_, i) => {
    const s = ctx.suggestions[i]
    const suggestion = s ? { weightKg: s.weight_kg, reps: s.reps, kind: s.kind } : null
    const previous = prevWorking[i] ?? null
    const values = suggestion
      ? { weightKg: suggestion.weightKg, reps: suggestion.reps, seconds: null }
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

export const swapExercise = (d: WorkoutDraft, key: string, ctx: ExerciseContext) =>
  mapExercise(d, key, (ex) => withContext(ex, ctx))

export const addExercise = (d: WorkoutDraft, ctx: ExerciseContext): WorkoutDraft => ({
  ...d,
  exercises: [...d.exercises, newExercise(ctx, DEFAULT_TARGETS)],
})

export const removeExercise = (d: WorkoutDraft, key: string): WorkoutDraft => ({
  ...d,
  exercises: d.exercises.filter((ex) => ex.key !== key),
})

/** Add a working set (copy of the last row) or an empty warm-up after the last warm-up. */
export function addSet(d: WorkoutDraft, key: string, warmup = false): WorkoutDraft {
  return mapExercise(d, key, (ex) => {
    const rows = [...ex.rows]
    if (warmup) {
      const at = rows.filter((r) => r.isWarmup).length
      rows.splice(at, 0, { ...EMPTY, done: false, isWarmup: true, previous: null, suggestion: null })
    } else {
      const last = rows.filter((r) => !r.isWarmup).at(-1)
      const values = last ? { weightKg: last.weightKg, reps: last.reps, seconds: last.seconds } : EMPTY
      rows.push({ ...values, done: false, isWarmup: false, previous: null, suggestion: null })
    }
    return { ...ex, rows }
  })
}

export const removeSet = (d: WorkoutDraft, key: string, index: number) =>
  mapExercise(d, key, (ex) => ({ ...ex, rows: ex.rows.filter((_, i) => i !== index) }))

export const updateSet = (d: WorkoutDraft, key: string, index: number, patch: Partial<SetValues>) =>
  mapRow(d, key, index, (r) => ({ ...r, ...patch }))

export const toggleDone = (d: WorkoutDraft, key: string, index: number) =>
  mapRow(d, key, index, (r) => ({ ...r, done: !r.done }))

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
const isLoggable = (ex: DraftExercise, r: DraftSet) =>
  r.done && (ex.measure === 'time' ? r.seconds !== null && r.seconds > 0 : r.reps !== null && r.reps > 0)

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
        sets: ex.rows
          .filter((r) => isLoggable(ex, r))
          .map((r) => ({
            weight_kg: r.weightKg,
            reps: ex.measure === 'time' ? null : r.reps,
            seconds: ex.measure === 'time' ? r.seconds : null,
            is_warmup: r.isWarmup,
          })),
      }))
      .filter((ex) => ex.sets.length > 0),
  }
}
