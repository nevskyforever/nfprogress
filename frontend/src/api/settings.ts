import { apiRequest } from './client'
import { currentPlatform } from '@/platform/runtime'
import { SQLiteSettingsRepository } from '@/infrastructure/sqlite/settingsRepository'
import type { SettingsResponse, SettingsValues } from '@/types/content'

const sqliteSettings = new SQLiteSettingsRepository()
const DESKTOP_EDITABLE_KEYS = [
  'game_mode', 'inf_project', 'global_streak', 'show_written_today_in_all_projects',
  'notification_display_time', 'start_day_time', 'language', 'frontend_theme',
  'frontend_motion', 'background_synch', 'frontend_project_filter', 'frontend_project_sort',
  'frontend_stage_sort', 'inventory_filter', 'project_filter', 'project_sort',
] as SettingsResponse['editable_keys']

function desktopResponse(values: SettingsValues): SettingsResponse {
  return {
    values: { frontend_motion: 'full', background_synch: true, ...values },
    platform: 'desktop',
    capabilities: {
      local_file_sync: true,
      background_file_sync: true,
      native_updates: true,
      remote_api: false,
    },
    editable_keys: DESKTOP_EDITABLE_KEYS,
  }
}

export const settingsApi = {
  get(signal?: AbortSignal): Promise<SettingsResponse> {
    if (currentPlatform() === 'tauri') {
      if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'))
      return sqliteSettings.getAll().then(desktopResponse)
    }
    return apiRequest<SettingsResponse>('/api/settings', { signal })
  },

  update(values: SettingsValues): Promise<SettingsResponse> {
    if (currentPlatform() === 'tauri') {
      return sqliteSettings.setAll(values).then(() => settingsApi.get())
    }
    return apiRequest<SettingsResponse>('/api/settings', {
      method: 'PATCH',
      body: { values },
    })
  },

  acceptUserAgreement(agreementId: string): Promise<SettingsResponse> {
    if (currentPlatform() === 'tauri') {
      if (!agreementId.trim()) return Promise.reject(new Error('Не удалось сохранить принятие соглашения.'))
      return sqliteSettings.set('user_agreement', true).then(() => settingsApi.get())
    }
    return apiRequest<SettingsResponse>('/api/settings/user-agreement/accept', {
      method: 'POST',
      body: { agreement_id: agreementId },
    })
  },
}
