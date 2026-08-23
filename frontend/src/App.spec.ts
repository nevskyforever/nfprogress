import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { contentApi } from '@/api/content'
import { settingsApi } from '@/api/settings'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'
import type { SettingsResponse } from '@/types/content'

import App from './App.vue'

vi.mock('@/api/content', () => ({
  contentApi: {
    locale: vi.fn(),
  },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: {
    get: vi.fn(),
  },
}))

function settingsResponse(
  values: SettingsResponse['values'],
): SettingsResponse {
  return {
    values,
    platform: 'web',
    capabilities: {
      local_file_sync: false,
      background_file_sync: false,
      native_updates: false,
      remote_api: true,
    },
    editable_keys: ['language', 'frontend_theme'],
  }
}

function mountApp() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return {
    pinia,
    wrapper: mount(App, {
      global: {
        plugins: [pinia],
        stubs: {
          IonApp: { template: '<div><slot /></div>' },
          AppShell: { template: '<div data-testid="app-shell">workspace</div>' },
          UserAgreementGate: { template: '<div data-testid="agreement-gate">agreement</div>' },
        },
      },
    }),
  }
}

describe('App bootstrap', () => {
  beforeEach(() => {
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(contentApi.locale).mockReset()
    vi.mocked(contentApi.locale).mockResolvedValue({ Проекты: 'Projects' })
  })

  it('applies authoritative preferences and skips the gate for an accepted legacy flag', async () => {
    vi.mocked(settingsApi.get).mockResolvedValue(
      settingsResponse({
        language: 'en',
        frontend_theme: 'dark',
        user_agreement: true,
      }),
    )
    const { pinia, wrapper } = mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="agreement-gate"]').exists()).toBe(false)
    expect(useLocaleStore(pinia).language).toBe('en')
    expect(useThemeStore(pinia).preference).toBe('dark')
  })

  it('does not mount router content before an unaccepted agreement', async () => {
    vi.mocked(settingsApi.get).mockResolvedValue(
      settingsResponse({ language: 'ru', frontend_theme: 'system', user_agreement: false }),
    )
    const { wrapper } = mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="agreement-gate"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(false)
  })

  it('keeps the app blocked after a bootstrap error and retries safely', async () => {
    vi.mocked(settingsApi.get)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(
        settingsResponse({ language: 'ru', frontend_theme: 'system', user_agreement: true }),
      )
    const { wrapper } = mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(false)
    expect(wrapper.get('[role="alert"]').text()).toContain('Не удалось открыть nfprogress')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(settingsApi.get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="app-shell"]').exists()).toBe(true)
  })
})
