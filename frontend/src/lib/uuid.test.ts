import { afterEach, describe, expect, it, vi } from 'vitest'
import { uuid } from './uuid'

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('uuid', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uuid works without crypto.randomUUID (plain http)', () => {
    vi.stubGlobal('crypto', { getRandomValues: globalThis.crypto.getRandomValues.bind(globalThis.crypto) })
    expect(uuid()).toMatch(V4)
  })

  it('uuid returns distinct values', () => {
    expect(uuid()).not.toBe(uuid())
  })
})
