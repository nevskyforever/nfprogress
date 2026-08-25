import { describe, expect, it, vi } from 'vitest'

import { automaticDailyGoal, automaticDeadline } from './projectPlanning'

describe('project planning calculations', () => {
  it('derives a daily goal from the deadline and remaining work', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T12:00:00'))
    expect(automaticDailyGoal(1_000, 100, '2026-08-28', 'symbols')).toBe(300)
    expect(automaticDailyGoal(1, 0, '2026-08-28', 'author_list')).toBe(0.3)
    vi.useRealTimers()
  })

  it('derives an inclusive deadline from a daily goal', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T12:00:00'))
    expect(automaticDeadline(1_000, 100, 300)).toBe('2026-08-28')
    vi.useRealTimers()
  })
})
