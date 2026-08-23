import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { settingsApi } from '@/api/settings'
import { projectFixture } from '@/test/fixtures'

import ProjectsPage from './ProjectsPage.vue'

const replaceRoute = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: replaceRoute, push: vi.fn() }),
}))

vi.mock('@/api/projects', () => ({
  projectsApi: {
    list: vi.fn(),
    today: vi.fn(),
    globalStreak: vi.fn(),
    create: vi.fn(),
  },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: { get: vi.fn(), update: vi.fn() },
}))

describe('ProjectsPage streak summaries', () => {
  beforeEach(() => {
    replaceRoute.mockReset()
    vi.mocked(projectsApi.list).mockResolvedValue([
      projectFixture({ streak_length: 2, streak_status: 'Active' }),
    ])
    vi.mocked(projectsApi.globalStreak).mockResolvedValue({
      enabled: true,
      status: 'Go',
      length: 4,
      max_length: 9,
    })
    vi.mocked(settingsApi.get).mockResolvedValue({
      values: {
        global_streak: true,
        show_written_today_in_all_projects: false,
      },
      platform: 'web',
      capabilities: {
        local_file_sync: false,
        background_file_sync: false,
        native_updates: false,
        remote_api: true,
      },
      editable_keys: ['global_streak'],
    })
  })

  it('shows global and project streaks from authoritative API data', async () => {
    const wrapper = mount(ProjectsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonPage: { template: '<div><slot /></div>' },
          ProjectCreateDialog: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()

    expect(projectsApi.globalStreak).toHaveBeenCalledOnce()
    expect(wrapper.get('.global-streak-summary').text()).toContain('4 дн.')
    expect(wrapper.get('.global-streak-summary').text()).toContain('Максимум: 9')
    expect(wrapper.get('.project-card__streak').attributes('aria-label')).toContain('2 дн.')
    wrapper.unmount()
  })
})
