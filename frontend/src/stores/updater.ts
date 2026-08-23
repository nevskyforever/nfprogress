import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Update } from '@tauri-apps/plugin-updater'

import { supportsNativeUpdates } from '@/platform/runtime'
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

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error ?? '')
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
    if (!supportsNativeUpdates() || busy.value) return false
    status.value = 'checking'
    errorMessage.value = ''
    if (manual) dismissed.value = false

    try {
      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check({ timeout: CHECK_TIMEOUT_MS })
      pendingUpdate = update
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
