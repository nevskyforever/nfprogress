import { describe, expect, it } from 'vitest'

import { calculatePureStatistics } from './calculations'
import type { StatisticsInput } from './types'

function input(overrides: Partial<StatisticsInput> = {}): StatisticsInput {
  return {
    entityId: 'project-1',
    unit: 'symbols',
    createdAt: '2024-02-28',
    planningDate: '2024-02-29',
    total: 0,
    progressEntries: [],
    ...overrides,
  }
}

describe('pure statistics parity', () => {
  it('handles an empty project and inclusive leap-year age', () => {
    const result = calculatePureStatistics(input({ entityId: 'Проект 🚀' }))
    expect(result.entity_id).toBe('Проект 🚀')
    expect(result.metrics).toMatchObject({
      entries_count: 0,
      total: 0,
      days_since_start: 2,
      active_days: 0,
      active_days_percent: 0,
    })
    expect(result.timeline).toEqual([])
  })

  it('groups multiple entries on one effective writing day', () => {
    const result = calculatePureStatistics(input({
      createdAt: '2026-08-01',
      planningDate: '2026-08-04',
      total: 350,
      progressEntries: [
        { addedSymbols: 100, createdAt: '2026-08-02T02:30:00' },
        { addedSymbols: 250, createdAt: '2026-08-02T23:59:00' },
        { addedSymbols: 0, createdAt: '2026-08-04T04:00:00' },
      ],
    }))
    expect(result.metrics).toMatchObject({
      entries_count: 3,
      average_symbols_per_active_day: 175,
      average_symbols_per_entry: 117,
      average_entries_per_active_day: 1.5,
      best_day: { date: '2026-08-02', symbols: 350, value: 350 },
      best_weekday: { weekday: 6, symbols: 350 },
      active_days: 2,
      active_days_percent: 50,
    })
    expect(result.timeline).toEqual([
      { date: '2026-08-02', symbols: 350, value: 350 },
      { date: '2026-08-04', symbols: 0, value: 0 },
    ])
  })

  it('uses Python ties-to-even rounding for averages', () => {
    const result = calculatePureStatistics(input({
      createdAt: '2026-01-01',
      planningDate: '2026-01-02',
      total: 1,
      progressEntries: [
        { addedSymbols: 0, createdAt: '2026-01-01T10:00:00' },
        { addedSymbols: 1, createdAt: '2026-01-02T10:00:00' },
      ],
    }))
    expect(result.metrics.average_symbols_per_active_day).toBe(0)
    expect(result.metrics.average_symbols_per_entry).toBe(0)
    expect(result.metrics.average_entries_per_active_day).toBe(1)
  })

  it.each([
    ['symbols', 40000, 40000],
    ['A4', 10, 18000],
    ['author_list', 0.5, 20000],
    ['ficbook_pages', 8, 36000],
  ] as const)('calculates totals and timeline in %s', (unit, total, expectedSymbols) => {
    const result = calculatePureStatistics(input({
      unit,
      total,
      progressEntries: [{ addedSymbols: expectedSymbols, createdAt: '2026-01-01T10:00:00' }],
    }))
    expect(result.metrics.total).toBe(total)
    expect(result.timeline[0]).toMatchObject({ symbols: expectedSymbols, value: total })
  })

  it('chooses the first date and weekday on equal maxima', () => {
    const result = calculatePureStatistics(input({
      createdAt: '2026-08-03',
      planningDate: '2026-08-04',
      total: 200,
      progressEntries: [
        { addedSymbols: 100, createdAt: '2026-08-03T10:00:00' },
        { addedSymbols: 100, createdAt: '2026-08-04T10:00:00' },
      ],
    }))
    expect(result.metrics.best_day?.date).toBe('2026-08-03')
    expect(result.metrics.best_weekday?.weekday).toBe(0)
  })

  it('uses the serialized effective writing-day date, not browser current time', () => {
    const result = calculatePureStatistics(input({
      createdAt: '2026-08-03',
      planningDate: '2026-08-04',
      total: 10,
      progressEntries: [{ addedSymbols: 10, createdAt: '2026-08-03T03:59:00' }],
    }))
    expect(result.timeline[0]?.date).toBe('2026-08-03')
  })
})
