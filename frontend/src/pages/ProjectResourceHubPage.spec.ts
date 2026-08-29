import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { openWorkspaceWindow } from '@/platform/workspaceWindows'
import { projectFixture } from '@/test/fixtures'

import ProjectResourceHubPage from './ProjectResourceHubPage.vue'

const pushRoute = vi.fn()
const resolveRoute = vi.fn(() => ({ href: '/maps/project-id' }))

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'maps' }),
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
})
