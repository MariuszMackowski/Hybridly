import { describe, expect, it } from 'vitest'
import { DRAFT_KEY, clearDraft, loadDraft, saveDraft } from './storage'
import type { WorkoutDraft } from './draft'

/** Minimal in-memory Storage implementation. */
function memoryStorage(): Storage {
  const data = new Map<string, string>()
  return {
    get length() { return data.size },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => { data.delete(k) },
    setItem: (k, v) => { data.set(k, v) },
  }
}

const draft: WorkoutDraft = {
  version: 1, clientId: 'c1', templateId: null, title: null, startedAt: '2026-11-04T07:00:00Z',
  warmup: [], cooldown: [], exercises: [],
}

describe('storage', () => {
  it('loadDraft restores saved draft', () => {
    const s = memoryStorage()
    saveDraft(draft, s)
    expect(loadDraft(s)).toEqual(draft)
  })

  it('loadDraft returns null for wrong version or corrupt JSON', () => {
    const s = memoryStorage()
    s.setItem(DRAFT_KEY, JSON.stringify({ ...draft, version: 0 }))
    expect(loadDraft(s)).toBeNull()
    s.setItem(DRAFT_KEY, '{not json')
    expect(loadDraft(s)).toBeNull()
  })

  it('clearDraft removes it', () => {
    const s = memoryStorage()
    saveDraft(draft, s)
    clearDraft(s)
    expect(loadDraft(s)).toBeNull()
  })
})
