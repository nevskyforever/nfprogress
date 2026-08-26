import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { contentApi } from '@/api/content'
import { settingsApi } from '@/api/settings'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'
import type { SettingsResponse } from '@/types/content'

import AppShell from './AppShell.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: { title: 'Проекты' }, fullPath: '/projects', name: 'projects' }),
  useRouter: () => ({ push: vi.fn().mockResolvedValue(undefined) }),
}))

vi.mock('@/composables/useNetworkStatus', () => ({
  useNetworkStatus: () => ({ online: ref(true) }),
}))

vi.mock('@/api/content', () => ({
  contentApi: {
    locale: vi.fn(),
  },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

function response(values: SettingsResponse['values']): SettingsResponse {
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

function mountShell() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return {
    pinia,
    wrapper: mount(AppShell, {
      global: {
        plugins: [pinia],
        stubs: {
          IonIcon: true,
          IonRouterOutlet: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    }),
  }
}

describe('AppShell preferences', () => {
  beforeEach(() => {
    try {
      window.localStorage?.removeItem('nfprogress.theme')
      window.localStorage?.removeItem('nfprogress.language')
    } catch {
      // jsdom can run without an origin-backed local storage implementation.
    }
    vi.mocked(settingsApi.update).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(settingsApi.get).mockResolvedValue(response({ developer_mode: false }))
    vi.mocked(contentApi.locale).mockReset()
    vi.mocked(contentApi.locale).mockResolvedValue({})
  })

  it('waits for backend confirmation before changing the theme', async () => {
    let confirmUpdate: ((settings: SettingsResponse) => void) | undefined
    vi.mocked(settingsApi.update).mockReturnValue(
      new Promise((resolve) => {
        confirmUpdate = resolve
      }),
    )
    const { pinia, wrapper } = mountShell()
    const theme = useThemeStore(pinia)
    const themeSelect = wrapper.findAll('.compact-select select')[1]

    await themeSelect?.setValue('dark')
    expect(settingsApi.update).toHaveBeenCalledWith({ frontend_theme: 'dark' })
    expect(theme.preference).toBe('system')

    confirmUpdate?.(response({ language: 'ru', frontend_theme: 'dark' }))
    await flushPromises()
    expect(theme.preference).toBe('dark')
  })

  it('persists language changes and reports rejected preferences without an unhandled promise', async () => {
    vi.mocked(settingsApi.update)
      .mockResolvedValueOnce(response({ language: 'en', frontend_theme: 'system' }))
      .mockRejectedValueOnce(new Error('rejected'))
    const { pinia, wrapper } = mountShell()
    const locale = useLocaleStore(pinia)
    const theme = useThemeStore(pinia)
    const selects = wrapper.findAll('.compact-select select')
    await locale.setLanguage('ru')

    await selects[0]?.setValue('en')
    await flushPromises()
    expect(settingsApi.update).toHaveBeenCalledWith({ language: 'en' })
    expect(locale.language).toBe('en')

    await selects[1]?.setValue('dark')
    await flushPromises()
    expect(theme.preference).toBe('system')
    expect(wrapper.get('[role="alert"]').text()).toContain('Произошла непредвиденная ошибка')
  })
})
