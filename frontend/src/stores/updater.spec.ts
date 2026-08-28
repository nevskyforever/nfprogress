import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { check } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'
import { getVersion } from '@tauri-apps/api/app'

import { supportsMacUpdateChecks, supportsNativeUpdates } from '@/platform/runtime'
import { useNotificationsStore } from '@/stores/notifications'

import { useUpdaterStore } from './updater'

vi.mock('@tauri-apps/plugin-updater', () => ({
  check: vi.fn(),
}))

vi.mock('@tauri-apps/plugin-process', () => ({
  relaunch: vi.fn(),
}))

vi.mock('@tauri-apps/api/app', () => ({
  getVersion: vi.fn(),
}))

vi.mock('@/platform/runtime', () => ({
  supportsNativeUpdates: vi.fn(() => true),
  supportsMacUpdateChecks: vi.fn(() => false),
  openExternalUrl: vi.fn(),
}))

describe('updater store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(check).mockReset()
    vi.mocked(relaunch).mockReset()
    vi.mocked(getVersion).mockReset()
    vi.mocked(supportsNativeUpdates).mockReset()
    vi.mocked(supportsMacUpdateChecks).mockReset()
    vi.mocked(supportsNativeUpdates).mockReturnValue(true)
    vi.mocked(supportsMacUpdateChecks).mockReturnValue(false)
  })

  it('reports the current version after an explicit check', async () => {
    vi.mocked(check).mockResolvedValue(null)
    const updater = useUpdaterStore()

    await updater.checkForUpdates(true)

    expect(updater.status).toBe('current')
    expect(useNotificationsStore().notifications.at(-1)?.message)
      .toBe('Установлена актуальная версия приложения.')
  })

  it('downloads, installs and relaunches only an update returned by Tauri', async () => {
    const downloadAndInstall = vi.fn(async (onEvent: (event: unknown) => void) => {
      onEvent({ event: 'Started', data: { contentLength: 100 } })
      onEvent({ event: 'Progress', data: { chunkLength: 60 } })
      onEvent({ event: 'Progress', data: { chunkLength: 40 } })
      onEvent({ event: 'Finished' })
    })
    vi.mocked(check).mockResolvedValue({
      version: '4.15.0',
      body: 'Улучшения',
      downloadAndInstall,
    } as never)
    const updater = useUpdaterStore()

    await updater.checkForUpdates()
    expect(updater.status).toBe('available')
    expect(updater.availableVersion).toBe('4.15.0')

    await updater.installUpdate()

    expect(downloadAndInstall).toHaveBeenCalledOnce()
    expect(updater.progressPercent).toBe(100)
    expect(relaunch).toHaveBeenCalledOnce()
    expect(updater.status).toBe('restarting')
  })

  it('does not load the updater API in a local or web build', async () => {
    vi.mocked(supportsNativeUpdates).mockReturnValue(false)
    const updater = useUpdaterStore()

    await updater.checkForUpdates(true)

    expect(check).not.toHaveBeenCalled()
    expect(updater.status).toBe('idle')
  })

  it('offers a newer macOS archive from the compatibility manifest', async () => {
    vi.mocked(supportsNativeUpdates).mockReturnValue(false)
    vi.mocked(supportsMacUpdateChecks).mockReturnValue(true)
    vi.mocked(getVersion).mockResolvedValue('5.0.1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        notes: 'Исправления',
        macos_intel: {
          version: '5.1.0',
          url: 'https://nfproject.ru/app/nfprogress-mac-intel-5.1.0.zip',
          sha256: 'a'.repeat(64),
          size: 100,
        },
      }),
    }))
    const updater = useUpdaterStore()

    await updater.checkForUpdates()

    expect(updater.status).toBe('available')
    expect(updater.availableVersion).toBe('5.1.0')
    vi.unstubAllGlobals()
  })
})
