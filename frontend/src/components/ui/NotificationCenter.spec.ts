import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import type { GameNotifications } from '@/types/game'

import NotificationCenter from './NotificationCenter.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    notifications: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
  },
}))

const history: GameNotifications = {
  unread: [{
    id: 'unread-notice',
    text: 'Стрик проекта сохранён.',
    tag: 'streak',
    created_at: '2026-08-15T09:30:00',
    status: 'new',
  }],
  read: [{
    id: 'read-notice',
    text: 'Банк начислил проценты.',
    tag: 'bank',
    created_at: '2026-08-14T09:30:00',
    status: 'read',
  }],
  unread_count: 1,
}

const emptyHistory: GameNotifications = {
  unread: [],
  read: [history.unread[0]!, history.read[0]!].map((notice) => ({
    ...notice,
    status: 'read' as const,
  })),
  unread_count: 0,
}

function mountCenter() {
  return mount(NotificationCenter, {
    global: {
      plugins: [createPinia()],
      stubs: {
        IonModal: {
          props: ['isOpen'],
          template: '<div v-if="isOpen"><slot /></div>',
        },
        IonHeader: { template: '<header><slot /></header>' },
        IonContent: { template: '<main><slot /></main>' },
        IonIcon: true,
        IonSpinner: true,
      },
    },
  })
}

describe('NotificationCenter', () => {
  beforeEach(() => {
    vi.mocked(gameApi.notifications).mockReset()
    vi.mocked(gameApi.markNotificationRead).mockReset()
    vi.mocked(gameApi.markAllNotificationsRead).mockReset()
    vi.mocked(gameApi.notifications).mockResolvedValue(history)
  })

  it('shows a persisted unread count and marks all events read through the API', async () => {
    vi.mocked(gameApi.markAllNotificationsRead).mockResolvedValue(emptyHistory)
    const wrapper = mountCenter()
    await flushPromises()

    expect(wrapper.get('.notification-center__count').text()).toBe('1')
    await wrapper.get('[data-testid="notification-trigger"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('#unread-notifications-title').text()).toContain('Непрочитанные')
    expect(wrapper.text()).toContain('Стрик проекта сохранён.')

    await wrapper.get('[data-testid="mark-all-notifications"]').trigger('click')
    await flushPromises()

    expect(gameApi.markAllNotificationsRead).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.notification-center__count').exists()).toBe(false)
    expect(wrapper.text()).toContain('Новых уведомлений нет.')
  })

  it('moves one selected event into the read history returned by the backend', async () => {
    vi.mocked(gameApi.markNotificationRead).mockResolvedValue(emptyHistory)
    const wrapper = mountCenter()
    await flushPromises()
    await wrapper.get('[data-testid="notification-trigger"]').trigger('click')
    await flushPromises()

    await wrapper.get('[aria-label="Отметить как прочитанное"]').trigger('click')
    await flushPromises()

    expect(gameApi.markNotificationRead).toHaveBeenCalledWith('unread-notice')
    expect(wrapper.text()).toContain('Банк начислил проценты.')
    expect(wrapper.get('#read-notifications-title').text()).toContain('Прочитанные')
  })
})
