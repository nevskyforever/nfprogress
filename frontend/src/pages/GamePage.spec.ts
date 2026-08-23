import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { gameApi } from '@/api/game'
import { gameStateFixture } from '@/test/gameFixtures'

import GamePage from './GamePage.vue'

vi.mock('@/api/game', () => ({
  gameApi: {
    state: vi.fn(),
    applyStreakFreeze: vi.fn(),
  },
}))

describe('GamePage', () => {
  beforeEach(() => {
    vi.mocked(gameApi.state).mockReset()
    vi.mocked(gameApi.applyStreakFreeze).mockReset()
    vi.mocked(gameApi.state).mockResolvedValue(gameStateFixture())
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
    const wrapper = mount(GamePage, {
      global: {
        plugins: [createPinia()],
        stubs: { IonIcon: true },
      },
    })
    await flushPromises()

    expect(gameApi.state).toHaveBeenCalledTimes(1)
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
