import { beforeEach, describe, expect, it, vi } from 'vitest'

import { invoke } from '@tauri-apps/api/core'

import { gameApi } from './game'

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}))

vi.mock('@/platform/runtime', () => ({
  currentPlatform: () => 'tauri',
}))

describe('native Game repository adapter', () => {
  beforeEach(() => {
    vi.mocked(invoke).mockReset()
    vi.mocked(invoke).mockResolvedValue({})
  })

  it('reads and mutates Game through typed Tauri commands without HTTP', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    await gameApi.state()
    await gameApi.buyItem({ category: 'Предметы', item_id: 'Лотерейный билет', count: 1 })

    expect(fetchSpy).not.toHaveBeenCalled()
    expect(invoke).toHaveBeenNthCalledWith(1, 'game_state', undefined)
    expect(invoke).toHaveBeenNthCalledWith(2, 'game_buy_item', {
      category: 'Предметы',
      itemId: 'Лотерейный билет',
      count: 1,
    })
    fetchSpy.mockRestore()
  })
})
