import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { contentApi } from '@/api/content'
import { projectsApi } from '@/api/projects'
import { settingsApi } from '@/api/settings'
import { announceDataChange } from '@/services/dataChanges'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'
import type { SettingsResponse } from '@/types/content'

import AppShell from './AppShell.vue'

const routerMock = vi.hoisted(() => ({
  route: { meta: { title: 'Проекты' }, fullPath: '/projects', name: 'projects' },
  push: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerMock.route,
  useRouter: () => ({ push: routerMock.push }),
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

vi.mock('@/api/projects', () => ({
  projectsApi: {
    globalStreak: vi.fn(),
    today: vi.fn(),
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
    Object.assign(routerMock.route, { meta: { title: 'Проекты' }, fullPath: '/projects', name: 'projects' })
    routerMock.push.mockClear()
    try {
      window.localStorage?.removeItem('nfprogress.theme')
      window.localStorage?.removeItem('nfprogress.language')
    } catch {
      // jsdom can run without an origin-backed local storage implementation.
    }
    vi.mocked(settingsApi.update).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(settingsApi.get).mockResolvedValue(response({
      developer_mode: false,
      global_streak: true,
    }))
    vi.mocked(projectsApi.globalStreak).mockReset()
    vi.mocked(projectsApi.globalStreak).mockResolvedValue({
      enabled: true,
      status: 'Active',
      length: 4,
      max_length: 9,
    })
    vi.mocked(projectsApi.today).mockReset()
    vi.mocked(projectsApi.today).mockResolvedValue({
      date: '2026-08-25',
      symbols: 0,
      projects: [],
    })
    vi.mocked(contentApi.locale).mockReset()
    vi.mocked(contentApi.locale).mockResolvedValue({})
  })

  it('shows global project map and note workspaces in navigation', () => {
    const { wrapper } = mountShell()
    const navigation = wrapper.get('.primary-navigation').text()
    expect(navigation).toContain('Карты')
    expect(navigation).toContain('Заметки')
  })

  it('returns to the section home when its active navigation item is pressed again', async () => {
    routerMock.route.fullPath = '/projects/project-42'
    const { wrapper } = mountShell()

    await wrapper.findAll('.navigation-link')[0]?.trigger('click')

    expect(routerMock.push).toHaveBeenCalledWith('/projects')
  })

  it('refreshes the global streak after a project freeze is applied in game mode', async () => {
    const { wrapper } = mountShell()
    await flushPromises()
    vi.mocked(projectsApi.globalStreak).mockResolvedValue({
      enabled: true,
      status: 'Freeze',
      length: 4,
      max_length: 9,
    })
    const callsBeforeRefresh = vi.mocked(projectsApi.globalStreak).mock.calls.length

    announceDataChange('game')
    await flushPromises()

    expect(vi.mocked(projectsApi.globalStreak).mock.calls.length)
      .toBeGreaterThan(callsBeforeRefresh)
    expect(wrapper.get('.sidebar-global-streak').text()).toContain('заморожен')
    wrapper.unmount()
  })

  it('refreshes open workspaces after the backend reports a new writing day', async () => {
    vi.useFakeTimers()
    vi.mocked(projectsApi.today)
      .mockResolvedValueOnce({ date: '2026-08-25', symbols: 0, projects: [] })
      .mockResolvedValueOnce({ date: '2026-08-26', symbols: 0, projects: [] })
    const { wrapper } = mountShell()
    await flushPromises()
    const callsBeforeRefresh = vi.mocked(projectsApi.globalStreak).mock.calls.length

    await vi.advanceTimersByTimeAsync(5 * 60 * 1000)
    await flushPromises()

    expect(projectsApi.today).toHaveBeenCalledTimes(2)
    expect(vi.mocked(projectsApi.globalStreak).mock.calls.length)
      .toBeGreaterThan(callsBeforeRefresh)
    wrapper.unmount()
    vi.useRealTimers()
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
