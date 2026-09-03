import { describe, expect, it } from 'vitest'

import { convertUnits } from '@/core/projects/calculations'
import {
  normalizeProgressTotal,
  progressContributionPercent,
  progressDeltaSymbols,
} from './calculations'

describe('pure progress calculations', () => {
  it('matches legacy total normalization by unit', () => {
    expect(normalizeProgressTotal(10.01, 'symbols')).toBe(11)
    expect(normalizeProgressTotal(10.01, 'A4')).toBe(11)
    expect(normalizeProgressTotal(10.01, 'ficbook_pages')).toBe(11)
    expect(normalizeProgressTotal(10.01, 'author_list')).toBe(10.01)
  })

  it('uses Python-compatible ties-to-even conversion for author lists', () => {
    expect(convertUnits(10_000, 'symbols', 'author_list')).toBe(0.2)
    expect(convertUnits(30_000, 'symbols', 'author_list')).toBe(0.8)
    expect(convertUnits(-10_000, 'symbols', 'author_list')).toBe(-0.2)
  })

  it('keeps delta and percentage calculations side-effect free', () => {
    expect(progressDeltaSymbols(1, 2, 'A4')).toBe(1_800)
    expect(progressDeltaSymbols(2, 1, 'A4')).toBe(-1_800)
    expect(progressContributionPercent(250, 1_000)).toBe(25)
    expect(progressContributionPercent(250, null)).toBe(0)
  })

  it('rejects non-finite and negative submitted totals', () => {
    expect(() => normalizeProgressTotal(-1, 'symbols')).toThrow(RangeError)
    expect(() => normalizeProgressTotal(Number.NaN, 'symbols')).toThrow(RangeError)
    expect(() => normalizeProgressTotal(Number.POSITIVE_INFINITY, 'symbols')).toThrow(RangeError)
    expect(() => convertUnits(1, 'invalid' as never, 'symbols')).toThrow(RangeError)
  })
})
