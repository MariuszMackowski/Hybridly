import type { WorkoutDraft } from './draft'

export const DRAFT_KEY = 'hybridly.draft.v1'

/** Persist the in-progress workout. */
export function saveDraft(d: WorkoutDraft, s: Storage = localStorage): void {
  s.setItem(DRAFT_KEY, JSON.stringify(d))
}

/** Restore the in-progress workout; null if missing, corrupt or from another version. */
export function loadDraft(s: Storage = localStorage): WorkoutDraft | null {
  const raw = s.getItem(DRAFT_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    return parsed?.version === 1 && Array.isArray(parsed.exercises) ? (parsed as WorkoutDraft) : null
  } catch {
    return null
  }
}

/** Forget the in-progress workout. */
export function clearDraft(s: Storage = localStorage): void {
  s.removeItem(DRAFT_KEY)
}
