import { describe, expect, it } from 'vitest'

import { adaptStatistics } from './statisticsAdapter'
import type { Project, Statistics } from '@/types/api'

const entry = (added_symbols: number, created_at: string) => ({
  id: `${added_symbols}-${created_at}`,
  new_total: added_symbols,
  new_total_symbols: added_symbols,
  added: added_symbols,
  added_symbols,
  added_progress: 0,
  created_at,
})

const serverStatistics = (entity_id: string): Statistics => ({
  entity_id,
  unit: 'symbols',
  metrics: {
    entries_count: 0, total: 0, average_symbols_per_active_day: 0,
    average_symbols_per_entry: 0, average_entries_per_active_day: 0,
    freezes_used: 2, best_day: null, best_weekday: null,
    current_streak: 4, max_streak: 7, days_since_start: 0,
    active_days: 0, active_days_percent: 0,
  },
  timeline: [],
})

describe('statistics migration adapter', () => {
  it('aggregates stage entries for a project while preserving Python state', () => {
    const project = {
      id: 'project-1', unit: 'symbols', total: 300,
      created_at: '2026-08-01', planning_date: '2026-08-03',
      progress_entries: [entry(999, '2026-08-01T10:00:00')],
      stages: [
        { id: 'stage-1', unit: 'symbols', total: 100, created_at: '2026-08-01', progress_entries: [entry(100, '2026-08-02T10:00:00')] },
        { id: 'stage-2', unit: 'symbols', total: 200, created_at: '2026-08-01', progress_entries: [entry(200, '2026-08-03T10:00:00')] },
      ],
    } as unknown as Project
    const result = adaptStatistics(project, serverStatistics(project.id))
    expect(result.metrics.entries_count).toBe(2)
    expect(result.metrics.total).toBe(300)
    expect(result.timeline.map((item) => item.symbols)).toEqual([100, 200])
    expect(result.metrics.freezes_used).toBe(2)
    expect(result.metrics.current_streak).toBe(4)
  })

  it('uses only the selected stage entries', () => {
    const project = {
      id: 'project-1', unit: 'symbols', total: 300,
      created_at: '2026-08-01', planning_date: '2026-08-03', progress_entries: [],
      stages: [
        { id: 'stage-1', unit: 'symbols', total: 100, created_at: '2026-08-01', progress_entries: [entry(100, '2026-08-02T10:00:00')] },
        { id: 'stage-2', unit: 'symbols', total: 200, created_at: '2026-08-01', progress_entries: [entry(200, '2026-08-03T10:00:00')] },
      ],
    } as unknown as Project
    const result = adaptStatistics(project, serverStatistics('stage-1'), 'stage-1')
    expect(result.entity_id).toBe('stage-1')
    expect(result.metrics.entries_count).toBe(1)
    expect(result.metrics.total).toBe(100)
  })
})
