import type { SupportedLanguage } from './api'

export type BackendPlatform = 'desktop' | 'web' | 'ios' | 'android'
export type FrontendTheme = 'system' | 'light' | 'dark'

export type SettingKey =
  | 'game_mode'
  | 'inf_project'
  | 'global_streak'
  | 'show_written_today_in_all_projects'
  | 'notification_display_time'
  | 'start_day_time'
  | 'language'
  | 'frontend_theme'
  | 'frontend_project_filter'
  | 'frontend_project_sort'
  | 'background_synch'
  | 'check_updates'
  | 'inventory_filter'
  | 'project_filter'
  | 'project_sort'

export interface SettingsValues {
  game_mode?: boolean
  inf_project?: boolean
  global_streak?: boolean
  show_written_today_in_all_projects?: boolean
  notification_display_time?: number
  start_day_time?: string
  language?: SupportedLanguage
  frontend_theme?: FrontendTheme
  frontend_project_filter?: 'all' | 'активен' | 'в архиве' | 'завершен'
  frontend_project_sort?: 'name' | 'deadline' | 'progress' | 'updated'
  background_synch?: boolean
  check_updates?: boolean
  inventory_filter?: string
  project_filter?: string
  project_sort?: string
  user_agreement?: boolean
  [key: string]: unknown
}

export interface PlatformCapabilities {
  local_file_sync: boolean
  background_file_sync: boolean
  native_updates: boolean
  remote_api: boolean
}

export interface SettingsResponse {
  values: SettingsValues
  platform: BackendPlatform
  capabilities: PlatformCapabilities
  editable_keys: SettingKey[]
}

export interface HelpSection {
  key: string
  title: string
  content: string
  children: HelpSection[]
}

export interface AgreementContent {
  id: string
  language: SupportedLanguage
  html: string
}
