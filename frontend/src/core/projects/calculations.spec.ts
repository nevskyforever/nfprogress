import { describe, expect, it } from 'vitest'

import {
  automaticDailyGoal,
  automaticDeadline,
  convertUnits,
  progressPercentage,
  remainingToGoal,
  writingDayIsoDate,
} from './calculations'
import type { ProgressUnit } from './types'

describe('pure project calculations parity', () => {
  it.each([
    ['symbols', 'A4', 3_600, 2],
    ['author_list', 'symbols', 1, 40_000],
    ['symbols', 'author_list', 20_000, 0.5],
    ['symbols', 'author_list', 2_000, 0.1],
    ['symbols', 'ficbook_pages', 4_501, 2],
  ] as const)('converts %s to %s with legacy rounding', (from, to, value, expected) => {
    expect(convertUnits(value, from as ProgressUnit, to as ProgressUnit)).toBe(expected)
  })

  it.each([
    [{ goal: 10_000, total: 2_500, infinite: false }, 25],
    [{ goal: 10_000, total: 12_500, infinite: false }, 125],
    [{ goal: null, total: 12_500, infinite: true }, 0],
  ] as const)('calculates percentage from a finite/infinite goal', (input, expected) => {
    expect(progressPercentage(input)).toBe(expected)
  })

  it.each([
    [{ goal: 10_000, total: 2_500, infinite: false }, 7_500],
    [{ goal: 10_000, total: 12_500, infinite: false }, 0],
    [{ goal: null, total: 12_500, infinite: true }, null],
  ] as const)('calculates remaining work without using Infinity in API data', (input, expected) => {
    expect(remainingToGoal(input)).toBe(expected)
  })

  it('uses inclusive dates and legacy ceil for daily preview goals', () => {
    const today = new Date(2026, 7, 26, 12)
    expect(automaticDailyGoal(1_000, 400, '2026-08-28', 'symbols', today, 100)).toBe(234)
    expect(automaticDailyGoal(1, 0, '2026-08-28', 'author_list', today)).toBe(0.3)
    expect(automaticDeadline(1_000, 100, 300, today)).toBe('2026-08-28')
  })

  it('rejects malformed dates and keeps writing-day boundaries explicit', () => {
    const today = new Date(2026, 1, 28, 2, 30)
    expect(automaticDailyGoal(1_000, 0, '2026-02-30', 'symbols', today)).toBeNull()
    expect(writingDayIsoDate('04:00:00', today)).toBe('2026-02-27')
    expect(writingDayIsoDate('04:00:00', new Date(2026, 1, 28, 5))).toBe('2026-02-28')
  })
})
