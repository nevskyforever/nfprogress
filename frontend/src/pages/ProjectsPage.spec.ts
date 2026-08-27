import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { integrationsApi } from '@/api/integrations'
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

vi.mock('@/api/integrations', () => ({
  integrationsApi: { runAllSync: vi.fn() },
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
    vi.mocked(projectsApi.today).mockResolvedValue({
      date: '2026-08-23',
      symbols: 1530,
      projects: [],
    })
    vi.mocked(settingsApi.get).mockResolvedValue({
      values: {
        global_streak: true,
        show_written_today_in_all_projects: true,
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
    expect(wrapper.find('.workspace-summaries').exists()).toBe(true)
    expect(wrapper.findAll('.workspace-summary')).toHaveLength(2)
    expect(wrapper.get('.workspace-summary--today').text()).toContain('1,530 символов')
    expect(wrapper.get('.workspace-summary--streak').text()).toContain('4 дн.')
    expect(wrapper.get('.workspace-summary--streak').text()).toContain('Максимум: 9')
    expect(wrapper.get('.project-card__streak').attributes('aria-label')).toContain('2 дн.')
    wrapper.unmount()
  })

  it('uses compact columns only when the list mixes covered and uncovered projects', async () => {
    vi.mocked(projectsApi.list).mockResolvedValue([
      projectFixture({ id: 'covered', cover_image: 'data:image/jpeg;base64,/9j/2Q==' }),
      projectFixture({ id: 'plain', cover_image: null }),
    ])
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

    expect(wrapper.get('.project-grid').classes()).toContain('project-grid--mixed-covers')
    wrapper.unmount()
  })

  it('offers all-source synchronization on desktop and refreshes the workspace', async () => {
    vi.mocked(settingsApi.get).mockResolvedValue({
      values: { global_streak: true, show_written_today_in_all_projects: true },
      platform: 'desktop',
      capabilities: {
        local_file_sync: true,
        background_file_sync: true,
        native_updates: true,
        remote_api: false,
      },
      editable_keys: ['global_streak'],
    })
    vi.mocked(integrationsApi.runAllSync).mockResolvedValue({
      checked: 1,
      changed: 1,
      failed: 0,
      items: [],
    })
    const wrapper = mount(ProjectsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonPage: { template: '<div><slot /></div>' },
          IonSpinner: true,
          ProjectCreateDialog: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()

    const button = wrapper.get('.sync-all-button')
    vi.mocked(projectsApi.list).mockClear()
    await button.trigger('click')
    await flushPromises()
    expect(integrationsApi.runAllSync).toHaveBeenCalledOnce()
    expect(projectsApi.list).toHaveBeenCalledOnce()
    wrapper.unmount()
  })
})
