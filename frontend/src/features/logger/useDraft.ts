import { useCallback, useState } from 'react'
import { fetchContext } from '../../api/hooks'
import type { TemplateOut } from '../../api/types'
import { createDraft, type WorkoutDraft } from './draft'
import { clearDraft, loadDraft, saveDraft } from './storage'

/** Draft state mirrored to localStorage on every change. */
export function useDraft() {
  const [draft, setDraftState] = useState<WorkoutDraft | null>(() => loadDraft())
  const setDraft = useCallback((next: WorkoutDraft | null) => {
    if (next) saveDraft(next)
    else clearDraft()
    setDraftState(next)
  }, [])
  const updateDraft = useCallback((fn: (d: WorkoutDraft) => WorkoutDraft) => {
    setDraftState((prev) => {
      if (!prev) return prev
      const next = fn(prev)
      saveDraft(next)
      return next
    })
  }, [])
  return { draft, setDraft, updateDraft }
}

/** Fetch contexts for every slot exercise and build a new draft. */
export async function startDraft(template: TemplateOut | null): Promise<WorkoutDraft> {
  const slots = template?.slots ?? []
  const contexts = await Promise.all(
    slots.map((s) => fetchContext(s.exercise_id, s.sets, s.rep_min, s.rep_max)),
  )
  const byId = Object.fromEntries(contexts.map((c) => [c.exercise.id, c]))
  const draft = createDraft(template, byId, new Date(), crypto.randomUUID())
  saveDraft(draft)
  return draft
}
