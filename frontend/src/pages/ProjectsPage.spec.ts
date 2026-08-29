import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { integrationsApi } from '@/api/integrations'
import { settingsApi } from '@/api/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { projectFixture } from '@/test/fixtures'

import ProjectsPage from './ProjectsPage.vue'

const replaceRoute = vi.fn()
const pushRoute = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: replaceRoute, push: pushRoute }),
}))

vi.mock('@/api/projects', () => ({
  projectsApi: {
    list: vi.fn(),
    today: vi.fn(),
    globalStreak: vi.fn(),
    folders: vi.fn(),
    create: vi.fn(),
    reorder: vi.fn(),
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
    pushRoute.mockReset()
    vi.mocked(projectsApi.list).mockResolvedValue([
      projectFixture({ streak_length: 2, streak_status: 'Active' }),
    ])
    vi.mocked(projectsApi.folders).mockResolvedValue([])
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

  it('uses browser drag data to reorder projects', async () => {
    const first = projectFixture({ id: 'project-a', name: 'Первая история' })
    const second = projectFixture({ id: 'project-b', name: 'Вторая история' })
    vi.mocked(projectsApi.list).mockResolvedValue([first, second])
    vi.mocked(projectsApi.reorder).mockResolvedValue([second, first])
    const wrapper = mount(ProjectsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' }, IonIcon: true,
          IonPage: { template: '<div><slot /></div>' }, ProjectCreateDialog: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()

    const data = new Map<string, string>()
    const dataTransfer = {
      effectAllowed: '',
      setData: (type: string, value: string) => data.set(type, value),
      getData: (type: string) => data.get(type) ?? '',
    }
    const cards = wrapper.findAll('.project-card')
    await cards[0]?.trigger('dragstart', { dataTransfer })
    await cards[1]?.trigger('drop', { dataTransfer })
    await flushPromises()

    expect(data.get('application/x-nfprogress-project-id')).toBe('project-a')
    expect(projectsApi.reorder).toHaveBeenCalledWith(['project-b', 'project-a'])
    wrapper.unmount()
  })

  it('opens only available project actions from the right-click menu', async () => {
    const wrapper = mount(ProjectsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' }, IonIcon: true,
          IonPage: { template: '<div><slot /></div>' }, ProjectCreateDialog: true,
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await flushPromises()
    await wrapper.get('.project-card').trigger('contextmenu', { clientX: 20, clientY: 20 })
    await wrapper.vm.$nextTick()

    const menuButtons = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu button')]
    expect(menuButtons.some((button) => button.textContent === 'Изменить')).toBe(true)
    expect(menuButtons.some((button) => button.textContent === 'Завершить')).toBe(false)
    menuButtons.find((button) => button.textContent === 'Изменить')?.click()
    await flushPromises()
    expect(pushRoute).toHaveBeenCalledWith(expect.objectContaining({ name: 'project-detail' }))
    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('keeps covered and uncovered projects in one freely reorderable grid', async () => {
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

    expect(wrapper.find('.project-mixed-grid').exists()).toBe(false)
    expect(wrapper.get('.project-grid').findAll('.project-card')).toHaveLength(2)
    expect(wrapper.get('.project-card').attributes('draggable')).toBe('true')
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
      items: [{
        project_id: 'f184de493a344752898ea43f2988dddb',
        stage_id: null,
        ok: true,
        changed: true,
        symbols: 100,
        progress: {
          project: projectFixture({ total: 100 }),
          entry: {
            id: 'entry-id',
            new_total: 100,
            new_total_symbols: 100,
            added: 100,
            added_symbols: 100,
            added_progress: 1,
            created_at: '2026-08-23T18:00:00',
          },
          added_symbols: 100,
          game: null,
          warning: null,
        },
        error: null,
      }],
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
    expect(useNotificationsStore().notifications).toContainEqual(expect.objectContaining({
      kind: 'success',
      message: 'В проект добавлено 100 символов',
    }))
    wrapper.unmount()
  })
})
