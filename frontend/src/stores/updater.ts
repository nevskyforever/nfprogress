import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Update } from '@tauri-apps/plugin-updater'

import { supportsMacUpdateChecks, supportsNativeUpdates } from '@/platform/runtime'
import { useLocaleStore } from '@/stores/locale'
import { useNotificationsStore } from '@/stores/notifications'

export type UpdaterStatus =
  | 'idle'
  | 'checking'
  | 'current'
  | 'available'
  | 'downloading'
  | 'installing'
  | 'restarting'
  | 'error'

const CHECK_TIMEOUT_MS = 15_000
const LEGACY_MANIFEST_URL = 'https://nfproject.ru/app/update_manifest.json'

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error ?? '')
}

function isNewerVersion(latest: string, current: string): boolean {
  const parts = (value: string) => value.split('.').map((part) => Number.parseInt(part, 10) || 0)
  const latestParts = parts(latest)
  const currentParts = parts(current)
  const length = Math.max(latestParts.length, currentParts.length)
  for (let index = 0; index < length; index += 1) {
    const latestPart = latestParts[index] ?? 0
    const currentPart = currentParts[index] ?? 0
    if (latestPart !== currentPart) return latestPart > currentPart
  }
  return false
}

export const useUpdaterStore = defineStore('updater', () => {
  const locale = useLocaleStore()
  const notifications = useNotificationsStore()
  const status = ref<UpdaterStatus>('idle')
  const availableVersion = ref('')
  const releaseNotes = ref('')
  const downloadedBytes = ref(0)
  const totalBytes = ref<number | null>(null)
  const errorMessage = ref('')
  const dismissed = ref(false)
  let pendingUpdate: Update | null = null
  let pendingMacUrl = ''
  let pendingMacSha256 = ''
  let pendingMacSize = 0

  const supported = computed(() => supportsNativeUpdates())
  const busy = computed(() => (
    ['checking', 'downloading', 'installing', 'restarting'] as UpdaterStatus[]
  ).includes(status.value))
  const promptVisible = computed(() => (
    !dismissed.value
    && (['available', 'downloading', 'installing', 'restarting'] as UpdaterStatus[])
      .includes(status.value)
  ))
  const progressPercent = computed<number | null>(() => {
    if (!totalBytes.value || totalBytes.value <= 0) return null
    return Math.min(100, Math.round((downloadedBytes.value / totalBytes.value) * 100))
  })

  async function checkForUpdates(manual = false): Promise<boolean> {
    if ((!supportsNativeUpdates() && !supportsMacUpdateChecks()) || busy.value) return false
    status.value = 'checking'
    errorMessage.value = ''
    if (manual) dismissed.value = false

    try {
      if (supportsMacUpdateChecks()) {
        const { getVersion } = await import('@tauri-apps/api/app')
        const currentVersion = await getVersion()
        const response = await fetch(`${LEGACY_MANIFEST_URL}?_=${Date.now()}`, {
          cache: 'no-store',
          signal: AbortSignal.timeout(CHECK_TIMEOUT_MS),
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const manifest = await response.json() as {
          version?: string
          notes?: string
          macos_arm?: { version?: string; url?: string; sha256?: string; size?: number }
          macos_intel?: { version?: string; url?: string; sha256?: string; size?: number }
        }
        const platformSection = /arm64|aarch64/i.test(
          window.__NFPROGRESS_RUNTIME__?.architecture ?? '',
        )
          ? manifest.macos_arm
          : manifest.macos_intel
        const updateVersion = platformSection?.version ?? manifest.version ?? ''
        pendingMacUrl = platformSection?.url ?? ''
        pendingMacSha256 = platformSection?.sha256 ?? ''
        pendingMacSize = platformSection?.size ?? 0
        if (!updateVersion || !pendingMacUrl || !pendingMacSha256 || !pendingMacSize
          || !isNewerVersion(updateVersion, currentVersion)) {
          availableVersion.value = ''
          releaseNotes.value = ''
          status.value = 'current'
          if (manual) notifications.success(locale.translate('Установлена актуальная версия приложения.'))
          return false
        }
        pendingUpdate = null
        availableVersion.value = updateVersion
        releaseNotes.value = manifest.notes?.trim() ?? ''
        status.value = 'available'
        return true
      }

      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check({ timeout: CHECK_TIMEOUT_MS })
      pendingUpdate = update
      pendingMacUrl = ''
      if (!update) {
        availableVersion.value = ''
        releaseNotes.value = ''
        status.value = 'current'
        if (manual) {
          notifications.success(locale.translate('Установлена актуальная версия приложения.'))
        }
        return false
      }

      availableVersion.value = update.version
      releaseNotes.value = update.body?.trim() ?? ''
      status.value = 'available'
      return true
    } catch (error) {
      errorMessage.value = errorText(error)
      status.value = 'error'
      if (manual) notifications.error(locale.translate('Не удалось проверить обновления.'))
      return false
    }
  }

  async function installUpdate(): Promise<void> {
    if (pendingMacUrl) {
      try {
        const { invoke } = await import('@tauri-apps/api/core')
        await invoke('install_macos_update', {
          url: pendingMacUrl,
          sha256: pendingMacSha256,
          size: pendingMacSize,
        })
        const { exit } = await import('@tauri-apps/plugin-process')
        await exit(0)
      } catch (error) {
        errorMessage.value = errorText(error)
        status.value = 'error'
        notifications.error(locale.translate('Не удалось установить обновление.'))
      }
      return
    }
    if (!pendingUpdate || busy.value) return
    status.value = 'downloading'
    downloadedBytes.value = 0
    totalBytes.value = null
    errorMessage.value = ''

    try {
      await pendingUpdate.downloadAndInstall((event) => {
        if (event.event === 'Started') {
          totalBytes.value = event.data.contentLength ?? null
          return
        }
        if (event.event === 'Progress') {
          downloadedBytes.value += event.data.chunkLength
          return
        }
        status.value = 'installing'
      })
      status.value = 'restarting'
      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    } catch (error) {
      errorMessage.value = errorText(error)
      status.value = 'error'
      notifications.error(locale.translate('Не удалось установить обновление.'))
    }
  }

  function dismissPrompt(): void {
    dismissed.value = true
  }

  return {
    status,
    availableVersion,
    releaseNotes,
    downloadedBytes,
    totalBytes,
    errorMessage,
    supported,
    busy,
    promptVisible,
    progressPercent,
    checkForUpdates,
    installUpdate,
    dismissPrompt,
  }
})
