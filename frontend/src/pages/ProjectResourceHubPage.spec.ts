import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { openWorkspaceWindow } from '@/platform/workspaceWindows'
import { projectFixture } from '@/test/fixtures'

import ProjectResourceHubPage from './ProjectResourceHubPage.vue'

const pushRoute = vi.fn()
const resolveRoute = vi.fn(() => ({ href: '/maps/project-id' }))
let routeName = 'maps'

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: routeName }),
  useRouter: () => ({ push: pushRoute, resolve: resolveRoute }),
}))
vi.mock('@/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}))
vi.mock('@/platform/workspaceWindows', () => ({
  openWorkspaceWindow: vi.fn(),
}))

describe('ProjectResourceHubPage', () => {
  beforeEach(() => {
    routeName = 'maps'
    pushRoute.mockReset()
    resolveRoute.mockClear()
    vi.mocked(openWorkspaceWindow).mockReset()
    vi.mocked(projectsApi.list).mockResolvedValue([projectFixture({ id: 'project-id' })])
  })

  it('opens a project map inside the section or in a separate window', async () => {
    const wrapper = mount(ProjectResourceHubPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonPage: { template: '<div><slot /></div>' },
        },
      },
    })
    await flushPromises()

    const buttons = wrapper.findAll('.resource-tile button')
    await buttons[0]?.trigger('click')
    await buttons[1]?.trigger('click')

    expect(pushRoute).toHaveBeenCalledWith({
      name: 'global-project-map', params: { projectId: 'project-id' },
    })
    expect(openWorkspaceWindow).toHaveBeenCalledWith(
      '/maps/project-id', expect.stringContaining('Дом у моря'),
    )
  })

  it('sorts maps and notes by the latest resource change', async () => {
    const older = projectFixture({
      id: 'project-old', name: 'Старая история',
      mindmap_updated_at: '2026-08-31T09:00:00Z',
      notes_updated_at: '2026-08-31T11:00:00Z',
    })
    const newer = projectFixture({
      id: 'project-new', name: 'Новая история',
      mindmap_updated_at: '2026-08-31T12:00:00Z',
      notes_updated_at: '2026-08-31T10:00:00Z',
    })
    vi.mocked(projectsApi.list).mockResolvedValue([older, newer])

    const mapsWrapper = mount(ProjectResourceHubPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonPage: { template: '<div><slot /></div>' },
        },
      },
    })
    await flushPromises()
    expect(mapsWrapper.findAll('h2').map((heading) => heading.text())).toEqual([
      'Новая история', 'Старая история',
    ])
    mapsWrapper.unmount()

    routeName = 'notes'
    const notesWrapper = mount(ProjectResourceHubPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonPage: { template: '<div><slot /></div>' },
        },
      },
    })
    await flushPromises()
    expect(notesWrapper.findAll('h2').map((heading) => heading.text())).toEqual([
      'Старая история', 'Новая история',
    ])
    notesWrapper.unmount()
  })
})
