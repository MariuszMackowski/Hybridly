import { describe, expect, it } from 'vitest'
import type { ExerciseContext, ExerciseOut, SlotOut, TemplateOut } from '../../api/types'
import {
  addSet,
  createDraft,
  displayOrder,
  swapExercise,
  toggleDone,
  toPayload,
  updateSet,
} from './draft'

const NOW = new Date('2026-11-04T07:00:00Z')

function exercise(id: number, name: string, extra: Partial<ExerciseOut> = {}): ExerciseOut {
  return {
    id, name, aliases: [], primary_muscles: ['chest'], secondary_muscles: [], measure: 'reps',
    load_factor: 1, increment_kg: 2.5, is_bodyweight: false, per_side: false, note: null,
    archived: false, ...extra,
  }
}

function slot(exerciseId: number, name: string, extra: Partial<SlotOut> = {}): SlotOut {
  return {
    block: 'main', exercise_id: exerciseId, alternative_exercise_ids: [], warmup_sets: 0, sets: 2,
    rep_min: 6, rep_max: 8, superset_group: null, note: null, position: 0, exercise_name: name,
    alternatives: [], ...extra,
  }
}

function template(slots: SlotOut[]): TemplateOut {
  return { id: 1, name: 'Upper A', note: null, warmup_items: ['Bike 3 min'], cooldown_items: [],
           archived: false, slots }
}

function ctx(ex: ExerciseOut, prev: [number, number, boolean?][] = [],
             sugg: [number, number][] = []): ExerciseContext {
  return {
    exercise: ex,
    previous: prev.length
      ? { workout_id: 9, started_at: '2026-11-01T07:00:00Z',
          sets: prev.map(([w, r, wu]) => ({ weight_kg: w, reps: r, seconds: null, is_warmup: !!wu })) }
      : null,
    suggestions: sugg.map(([w, r]) => ({ weight_kg: w, reps: r, kind: 'increase' as const })),
  }
}

const bench = exercise(1, 'Bench Press')
const row = exercise(2, 'Barbell Row')

describe('draft', () => {
  it('createDraft prefills from suggestion', () => {
    const d = createDraft(template([slot(1, 'Bench Press')]),
      { 1: ctx(bench, [[60, 8], [60, 8]], [[62.5, 6], [62.5, 6]]) }, NOW, 'c1')
    const rows = d.exercises[0].rows
    expect(rows.map((r) => [r.weightKg, r.reps, r.done])).toEqual([[62.5, 6, false], [62.5, 6, false]])
    expect(rows[0].previous).toEqual({ weightKg: 60, reps: 8, seconds: null })
    expect(d.warmup).toEqual([{ text: 'Bike 3 min', done: false }])
  })

  it('createDraft falls back to previous when no suggestion', () => {
    const d = createDraft(template([slot(1, 'Bench Press')]), { 1: ctx(bench, [[60, 8]]) }, NOW, 'c1')
    expect(d.exercises[0].rows.map((r) => [r.weightKg, r.reps])).toEqual([[60, 8], [null, null]])
  })

  it('createDraft leaves rows empty without history', () => {
    const d = createDraft(template([slot(1, 'Bench Press')]), { 1: ctx(bench) }, NOW, 'c1')
    expect(d.exercises[0].rows.every((r) => r.weightKg === null && r.previous === null)).toBe(true)
  })

  it('createDraft puts warmup rows first prefilled from previous warmups', () => {
    const d = createDraft(template([slot(1, 'Bench Press', { warmup_sets: 2 })]),
      { 1: ctx(bench, [[20, 10, true], [60, 8], [60, 8]], [[62.5, 6], [62.5, 6]]) }, NOW, 'c1')
    const rows = d.exercises[0].rows
    expect(rows.map((r) => r.isWarmup)).toEqual([true, true, false, false])
    expect([rows[0].weightKg, rows[0].reps, rows[1].weightKg]).toEqual([20, 10, null])
    expect(rows[2].previous).toEqual({ weightKg: 60, reps: 8, seconds: null })
    expect(rows[2].suggestion?.weightKg).toBe(62.5)
  })

  it('swapExercise replaces exercise and reapplies context', () => {
    const d = createDraft(template([slot(1, 'Bench Press')]), { 1: ctx(bench) }, NOW, 'c1')
    const key = d.exercises[0].key
    const swapped = swapExercise(d, key, ctx(row, [[50, 10]], [[52.5, 8]]))
    expect(swapped.exercises[0].exerciseId).toBe(2)
    expect(swapped.exercises[0].name).toBe('Barbell Row')
    expect(swapped.exercises[0].rows[0].weightKg).toBe(52.5)
    expect(swapped.exercises[0].sets).toBe(2)
  })

  it('addSet copies last row values not done', () => {
    let d = createDraft(template([slot(1, 'Bench Press')]), { 1: ctx(bench, [[60, 8]]) }, NOW, 'c1')
    const key = d.exercises[0].key
    d = updateSet(d, key, 1, { weightKg: 55, reps: 9 })
    d = toggleDone(d, key, 1)
    d = addSet(d, key)
    const last = d.exercises[0].rows[2]
    expect([last.weightKg, last.reps, last.done, last.isWarmup]).toEqual([55, 9, false, false])
  })

  it('addSet with warmup inserts after last warmup row', () => {
    let d = createDraft(template([slot(1, 'Bench Press', { warmup_sets: 1 })]), { 1: ctx(bench) }, NOW, 'c1')
    d = addSet(d, d.exercises[0].key, true)
    expect(d.exercises[0].rows.map((r) => r.isWarmup)).toEqual([true, true, false, false])
  })

  it('toPayload keeps only done rows and drops empty exercises', () => {
    let d = createDraft(template([slot(1, 'Bench Press'), slot(2, 'Barbell Row', { position: 1 })]),
      { 1: ctx(bench, [], [[60, 8], [60, 8]]), 2: ctx(row) }, NOW, 'c1')
    d = toggleDone(d, d.exercises[0].key, 0)
    const payload = toPayload(d, new Date('2026-11-04T08:00:00Z'))
    expect(payload.client_id).toBe('c1')
    expect(payload.template_id).toBe(1)
    expect(payload.exercises).toEqual([
      { exercise_id: 1, superset_group: null,
        sets: [{ weight_kg: 60, reps: 8, seconds: null, is_warmup: false }] },
    ])
  })

  it('toPayload omits done rows without reps', () => {
    let d = createDraft(template([slot(1, 'Bench Press')]), { 1: ctx(bench) }, NOW, 'c1')
    d = toggleDone(d, d.exercises[0].key, 0)
    expect(toPayload(d, NOW).exercises).toEqual([])
  })

  it('displayOrder groups consecutive superset members', () => {
    const d = createDraft(template([
      slot(1, 'Bench Press', { superset_group: 1 }),
      slot(2, 'Barbell Row', { superset_group: 1, position: 1 }),
      slot(1, 'Bench Press', { position: 2 }),
    ]), { 1: ctx(bench), 2: ctx(row) }, NOW, 'c1')
    expect(displayOrder(d).map((g) => g.group.length)).toEqual([2, 1])
  })
})
