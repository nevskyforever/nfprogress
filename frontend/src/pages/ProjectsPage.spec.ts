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
    update: vi.fn(),
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

  it('reorders projects through pointer events in the web interface', async () => {
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

    const cards = wrapper.findAll('.project-card')
    expect(cards[0]?.find('.project-card__drag-handle').exists()).toBe(true)
    Object.defineProperty(document, 'elementFromPoint', {
      configurable: true,
      value: vi.fn(() => cards[1]?.element ?? null),
    })
    const pointerEvent = (type: string, x: number, y: number) => Object.defineProperties(
      new Event(type, { bubbles: true, cancelable: true }),
      { pointerId: { value: 1 }, button: { value: 0 }, clientX: { value: x }, clientY: { value: y } },
    )
    cards[0]?.get('.project-card__drag-handle').element.dispatchEvent(pointerEvent('pointerdown', 10, 10))
    window.dispatchEvent(pointerEvent('pointermove', 30, 30))
    window.dispatchEvent(pointerEvent('pointerup', 30, 30))
    window.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    await flushPromises()

    expect(projectsApi.reorder).toHaveBeenCalledWith(['project-b', 'project-a'])
    expect(cards[0]?.find('.project-card__open').exists()).toBe(false)
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

  it('opens a folder submenu in the project context menu when several folders are available', async () => {
    vi.mocked(projectsApi.folders).mockResolvedValue([
      { id: 'folder-a', name: 'Черновики' },
      { id: 'folder-b', name: 'Идеи' },
    ])
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

    const folderButton = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu > button')]
      .find((button) => button.textContent === 'В папку')
    expect(folderButton).toBeDefined()
    folderButton?.click()
    await wrapper.vm.$nextTick()

    const submenuButtons = [...document.body.querySelectorAll<HTMLButtonElement>('.context-action-menu__submenu button')]
    expect(submenuButtons.map((button) => button.textContent)).toEqual(['Черновики', 'Идеи'])
    submenuButtons[1]?.click()
    await flushPromises()
    expect(projectsApi.update).toHaveBeenCalledWith(expect.any(String), { folder_id: 'folder-b' })
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
    expect(wrapper.find('.project-card__drag-handle').exists()).toBe(true)
    expect(wrapper.get('.project-card').classes()).toContain('project-card--sortable')
    expect(wrapper.get('.project-card').attributes('draggable')).toBe('true')
    await wrapper.get('#project-status-filter').setValue('активен')
    await flushPromises()
    expect(wrapper.get('.project-card').classes()).toContain('project-card--sortable')
    wrapper.unmount()
  })

  it('moves a project into an empty folder immediately', async () => {
    const project = projectFixture({ id: 'project-a', folder_id: null })
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    vi.mocked(projectsApi.folders).mockResolvedValue([{ id: 'folder-a', name: 'Черновики' }])
    vi.mocked(projectsApi.update).mockResolvedValue({ ...project, folder_id: 'folder-a' })
    vi.mocked(projectsApi.reorder).mockResolvedValue([{ ...project, folder_id: 'folder-a' }])
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
    await wrapper.get('[data-folder-id="folder-a"]').trigger('drop', {
      dataTransfer: { getData: (type: string) => type === 'text/plain' ? 'project-a' : '' },
    })
    await flushPromises()

    expect(projectsApi.update).toHaveBeenCalledWith('project-a', { folder_id: 'folder-a' })
    wrapper.unmount()
  })

  it('moves a project into a folder without a separate editing mode', async () => {
    const project = projectFixture({ id: 'project-a', folder_id: null })
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    vi.mocked(projectsApi.folders).mockResolvedValue([{ id: 'folder-a', name: 'Черновики' }])
    vi.mocked(projectsApi.update).mockResolvedValue({ ...project, folder_id: 'folder-a' })
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
    vi.mocked(projectsApi.reorder).mockClear()
    await wrapper.get('[data-folder-id="folder-a"]').trigger('drop', {
      dataTransfer: { getData: (type: string) => type === 'text/plain' ? 'project-a' : '' },
    })
    await flushPromises()

    expect(projectsApi.update).toHaveBeenCalledWith('project-a', { folder_id: 'folder-a' })
    expect(projectsApi.reorder).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('moves a project into a folder with its drag handle', async () => {
    const project = projectFixture({ id: 'project-a', folder_id: null })
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    vi.mocked(projectsApi.folders).mockResolvedValue([{ id: 'folder-a', name: 'Черновики' }])
    vi.mocked(projectsApi.update).mockResolvedValue({ ...project, folder_id: 'folder-a' })
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
    const folder = wrapper.get('[data-folder-id="folder-a"]')
    Object.defineProperty(document, 'elementFromPoint', {
      configurable: true,
      value: vi.fn(() => folder.element),
    })
    const pointerEvent = (type: string, x: number, y: number) => Object.defineProperties(
      new Event(type, { bubbles: true, cancelable: true }),
      { pointerId: { value: 1 }, button: { value: 0 }, clientX: { value: x }, clientY: { value: y } },
    )
    const handle = wrapper.get('.project-card__drag-handle')
    handle.element.dispatchEvent(pointerEvent('pointerdown', 10, 10))
    window.dispatchEvent(pointerEvent('pointermove', 30, 30))
    window.dispatchEvent(pointerEvent('pointerup', 30, 30))
    await flushPromises()

    expect(projectsApi.update).toHaveBeenCalledWith('project-a', { folder_id: 'folder-a' })
    wrapper.unmount()
  })

  it('collapses and expands a project folder from its header', async () => {
    const project = projectFixture({ id: 'project-a', folder_id: 'folder-a' })
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    vi.mocked(projectsApi.folders).mockResolvedValue([{ id: 'folder-a', name: 'Черновики' }])
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
    const folder = wrapper.get('[data-folder-id="folder-a"]')

    expect(folder.get('.project-folder__title').text()).toContain('Черновики')
    expect(folder.find('.project-grid').exists()).toBe(true)
    await folder.get('[aria-label="Свернуть папку"]').trigger('click')
    expect(folder.find('.project-grid').exists()).toBe(false)
    await folder.get('[aria-label="Развернуть папку"]').trigger('click')
    expect(folder.find('.project-grid').exists()).toBe(true)
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
      message: 'Синхронизировано: 1 проектов, 0 этапов. Добавлено: 100 символов.',
    }))
    wrapper.unmount()
  })
})
