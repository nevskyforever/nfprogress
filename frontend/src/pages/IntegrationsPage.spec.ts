import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { integrationsApi } from '@/api/integrations'
import { projectsApi } from '@/api/projects'
import { settingsApi } from '@/api/settings'
import { projectFixture } from '@/test/fixtures'

import IntegrationsPage from './IntegrationsPage.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    getSync: vi.fn(),
    configureSync: vi.fn(),
    removeSync: vi.fn(),
    runSync: vi.fn(),
    runAllSync: vi.fn(),
    inspectScrivener: vi.fn(),
  },
}))

vi.mock('@/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}))

vi.mock('@/api/settings', () => ({
  settingsApi: { get: vi.fn() },
}))

describe('IntegrationsPage', () => {
  beforeEach(() => {
    const stage = projectFixture({
      id: 'stage-id',
      name: 'Черновик',
      parent_project_id: 'project-id',
    })
    const project = projectFixture({
      id: 'project-id',
      stages: [stage],
      stages_enabled: true,
    })
    vi.mocked(projectsApi.list).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(integrationsApi.getSync).mockReset()
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    vi.mocked(settingsApi.get).mockResolvedValue({
      values: { background_synch: true },
      platform: 'desktop',
      capabilities: {
        local_file_sync: true,
        background_file_sync: true,
        native_updates: false,
        remote_api: false,
      },
      editable_keys: ['background_synch'],
    })
    vi.mocked(integrationsApi.getSync).mockResolvedValue({
      project_id: project.id,
      stage_id: stage.id,
      configured: false,
      type: null,
      path: null,
      item_id: null,
      last_synced_at: null,
      desktop_only: true,
    })
  })

  it('requires an explicit stage target for staged projects before local sync setup', async () => {
    const wrapper = mount(IntegrationsPage, {
      global: {
        plugins: [createPinia()],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonSpinner: true,
          StatePanel: true,
          WordUploadCard: true,
        },
      },
    })
    await flushPromises()

    expect(integrationsApi.getSync).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Источник подключается отдельно к каждому этапу')
    expect(wrapper.get('fieldset').attributes()).toHaveProperty('disabled')

    await wrapper.get('#sync-stage').setValue('stage-id')
    await flushPromises()

    expect(integrationsApi.getSync).toHaveBeenCalledWith('project-id', 'stage-id')
    expect(wrapper.get('fieldset').attributes()).not.toHaveProperty('disabled')
  })
})
