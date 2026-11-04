import { describe, expect, it } from 'vitest'
import { parseDecimal } from './decimal'

describe('parseDecimal', () => {
  it('parseDecimal accepts comma', () => {
    expect(parseDecimal('62,5')).toBe(62.5)
  })

  it('parseDecimal accepts dot', () => {
    expect(parseDecimal('62.5')).toBe(62.5)
  })

  it('parseDecimal returns null for empty or garbage', () => {
    expect(parseDecimal('')).toBeNull()
    expect(parseDecimal('abc')).toBeNull()
    expect(parseDecimal('-')).toBeNull()
  })
})
