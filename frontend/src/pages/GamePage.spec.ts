import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import { settingsApi } from '@/api/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { gameStateFixture } from '@/test/gameFixtures'
import type { SettingsResponse } from '@/types/content'

import GamePage from './GamePage.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    state: vi.fn(),
    applyStreakFreeze: vi.fn(),
  },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

const settingsFixture: SettingsResponse = {
  values: { inventory_filter: 'Зелья' },
  platform: 'web',
  capabilities: {
    local_file_sync: false,
    background_file_sync: false,
    native_updates: false,
    remote_api: true,
  },
  editable_keys: ['inventory_filter'],
}

describe('GamePage', () => {
  beforeEach(() => {
    vi.mocked(gameApi.state).mockReset()
    vi.mocked(gameApi.applyStreakFreeze).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(settingsApi.update).mockReset()
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture())
    vi.mocked(settingsApi.get).mockResolvedValue(settingsFixture)
    vi.mocked(gameApi.applyStreakFreeze).mockResolvedValue({
      ok: true,
      message: 'Заморозка применена.',
      messages: ['Заморозка применена.'],
      result: null,
      state: gameStateFixture({
        streak_freezes: {
          ...gameStateFixture().streak_freezes,
          inventory_count: 1,
          global_available: false,
        },
      }),
    })
  })

  it('loads real state and re-reads it after an authoritative command', async () => {
    const pinia = createPinia()
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture({
      notifications: {
        unread: [{
          id: 'streak-event',
          text: 'Стрик сохранён.',
          tag: 'streak',
          created_at: '2026-08-15T12:00:00',
          status: 'new',
        }],
        read: [],
        unread_count: 1,
      },
    }))
    const wrapper = mount(GamePage, {
      global: {
        plugins: [pinia],
        stubs: { IonIcon: true },
      },
    })
    await flushPromises()

    expect(gameApi.state).toHaveBeenCalledTimes(1)
    expect(settingsApi.get).toHaveBeenCalledTimes(1)
    expect(useNotificationsStore(pinia).gameHistory.unread_count).toBe(1)
    expect(wrapper.text()).toContain('Игровой режим')
    expect(wrapper.text()).toContain('Дом у моря')

    const freezeButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Применить заморозку'))
    expect(freezeButton).toBeDefined()
    await freezeButton?.trigger('click')
    await flushPromises()

    expect(gameApi.applyStreakFreeze).toHaveBeenCalledWith('global', undefined)
    expect(gameApi.state).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Заморозка применена.')
  })
})
