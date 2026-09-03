import { invoke } from '@tauri-apps/api/core'

import type { SettingsValues } from '@/types/content'

export interface SettingsRepository {
  getAll(): Promise<SettingsValues>
  set<K extends keyof SettingsValues>(key: K, value: SettingsValues[K]): Promise<void>
  setAll(values: SettingsValues): Promise<void>
}

export class SQLiteSettingsRepository implements SettingsRepository {
  getAll(): Promise<SettingsValues> {
    return invoke<SettingsValues>('get_settings')
  }

  set<K extends keyof SettingsValues>(key: K, value: SettingsValues[K]): Promise<void> {
    return this.setAll({ [key]: value })
  }

  setAll(values: SettingsValues): Promise<void> {
    return invoke('set_settings', { values })
  }
}
