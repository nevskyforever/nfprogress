import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useNotificationsStore } from './notifications'

describe('notifications store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('uses the persisted duration and removes timed notifications', () => {
    const store = useNotificationsStore()
    store.setDurationSeconds(2)
    store.success('Готово')

    expect(store.notifications).toHaveLength(1)
    expect(store.durationSeconds).toBe(2)

    vi.advanceTimersByTime(2_000)

    expect(store.notifications).toHaveLength(0)
  })

  it('normalizes invalid duration values and supports manual dismissal', () => {
    const store = useNotificationsStore()
    store.setDurationSeconds(9_000)
    const id = store.error('Ошибка')

    expect(store.durationSeconds).toBe(3600)
    expect(id).not.toBeNull()
    store.dismiss(id ?? '')
    expect(store.notifications).toHaveLength(0)
  })

  it('keeps five simultaneous notifications like the legacy stack', () => {
    const store = useNotificationsStore()
    for (let index = 1; index <= 5; index += 1) {
      store.show(`Событие ${index}`, 'info')
    }

    expect(store.notifications).toHaveLength(5)
  })

  it('shares authoritative persistent game history with all UI surfaces', () => {
    const store = useNotificationsStore()
    store.setGameHistory({
      unread: [{
        id: 'streak-notice',
        text: 'Стрик сохранён.',
        tag: 'streak',
        created_at: '2026-08-15T09:30:00',
        status: 'new',
      }],
      read: [],
      unread_count: 1,
    })

    expect(store.gameHistory.unread_count).toBe(1)
    expect(store.gameHistory.unread[0]?.id).toBe('streak-notice')
  })
})
