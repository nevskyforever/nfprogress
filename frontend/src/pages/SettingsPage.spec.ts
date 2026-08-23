import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { settingsApi } from '@/api/settings'
import type { SettingsResponse } from '@/types/content'

import SettingsPage from './SettingsPage.vue'

vi.mock('@/api/settings', () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

const webSettings: SettingsResponse = {
  values: {
    language: 'ru',
    frontend_theme: 'system',
    frontend_motion: 'full',
    start_day_time: '00:00:00',
    notification_display_time: 10,
    game_mode: false,
    inf_project: false,
    global_streak: false,
    show_written_today_in_all_projects: false,
  },
  platform: 'web',
  capabilities: {
    local_file_sync: false,
    background_file_sync: false,
    native_updates: false,
    remote_api: true,
  },
  editable_keys: [
    'language',
    'frontend_theme',
    'frontend_motion',
    'start_day_time',
    'notification_display_time',
    'game_mode',
    'inf_project',
    'global_streak',
    'show_written_today_in_all_projects',
  ],
}

const desktopSettings: SettingsResponse = {
  ...webSettings,
  values: { ...webSettings.values, background_synch: true },
  platform: 'desktop',
  capabilities: {
    local_file_sync: true,
    background_file_sync: true,
    native_updates: false,
    remote_api: false,
  },
  editable_keys: [...webSettings.editable_keys, 'background_synch'],
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(settingsApi.update).mockReset()
    vi.mocked(settingsApi.get).mockResolvedValue(webSettings)
    vi.mocked(settingsApi.update).mockResolvedValue({
      ...webSettings,
      values: { ...webSettings.values, game_mode: true },
    })
  })

  it('shows platform-editable controls only and persists a backend-authoritative patch', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonSpinner: true,
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('#settings-background-sync').exists()).toBe(false)
    expect(wrapper.find('#settings-infinite-project').exists()).toBe(true)
    expect(wrapper.find('#settings-written-today').exists()).toBe(true)
    expect(wrapper.find('#settings-notification-time').exists()).toBe(true)
    expect(wrapper.find('#settings-motion').exists()).toBe(true)
    await wrapper.get('#settings-game-mode').setValue(true)
    await wrapper.get('#settings-notification-time').setValue(20)
    await wrapper.get('#settings-motion').setValue('reduced')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(settingsApi.update).toHaveBeenCalledWith({
      game_mode: true,
      frontend_motion: 'reduced',
      notification_display_time: 20,
    })
    expect(wrapper.get('[role="status"]').text()).toContain('Настройки сохранены')
  })

  it('shows real background sync on desktop without offering the unavailable legacy updater', async () => {
    vi.mocked(settingsApi.get).mockResolvedValue(desktopSettings)
    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonSpinner: true,
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('#settings-background-sync').exists()).toBe(true)
    expect(wrapper.find('#settings-check-updates').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Проверять обновления')
  })
})
