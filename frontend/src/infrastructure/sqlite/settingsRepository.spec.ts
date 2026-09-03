import { beforeEach, describe, expect, it, vi } from 'vitest'

import { invoke } from '@tauri-apps/api/core'
import { SQLiteSettingsRepository } from './settingsRepository'

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))

describe('SQLiteSettingsRepository', () => {
  beforeEach(() => vi.mocked(invoke).mockReset())

  it('uses typed Tauri commands for reads and atomic patches', async () => {
    vi.mocked(invoke).mockResolvedValueOnce({ language: 'ru' })
    const repository = new SQLiteSettingsRepository()

    await expect(repository.getAll()).resolves.toEqual({ language: 'ru' })
    await repository.setAll({ language: 'fr', enabled: true })

    expect(invoke).toHaveBeenNthCalledWith(1, 'get_settings')
    expect(invoke).toHaveBeenNthCalledWith(2, 'set_settings', {
      values: { language: 'fr', enabled: true },
    })
  })
})
