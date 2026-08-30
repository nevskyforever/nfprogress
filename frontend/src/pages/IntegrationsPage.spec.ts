import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'

import { integrationsApi } from '@/api/integrations'
import { projectsApi } from '@/api/projects'
import { settingsApi } from '@/api/settings'
import { useNotificationsStore } from '@/stores/notifications'
import { gameStateFixture } from '@/test/gameFixtures'
import { projectFixture } from '@/test/fixtures'
import type { WordImportResult } from '@/types/integrations'

import IntegrationsPage from './IntegrationsPage.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    getProjectSyncs: vi.fn(),
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
      work_method: 'sync',
    })
    const project = projectFixture({
      id: 'project-id',
      stages: [stage],
      stages_enabled: true,
    })
    vi.mocked(projectsApi.list).mockReset()
    vi.mocked(settingsApi.get).mockReset()
    vi.mocked(integrationsApi.getProjectSyncs).mockReset()
    vi.mocked(integrationsApi.getSync).mockReset()
    vi.mocked(integrationsApi.runSync).mockReset()
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
    vi.mocked(integrationsApi.getProjectSyncs).mockResolvedValue({
      project_id: project.id,
      syncs: [],
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

    expect(integrationsApi.getProjectSyncs).toHaveBeenCalledWith('project-id')
    expect(integrationsApi.getSync).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Источник подключается отдельно к каждому этапу')
    expect(wrapper.get('fieldset').attributes()).toHaveProperty('disabled')

    await wrapper.get('#sync-stage').setValue('stage-id')
    await flushPromises()

    expect(integrationsApi.getSync).toHaveBeenCalledWith('project-id', 'stage-id')
    expect(wrapper.get('fieldset').attributes()).not.toHaveProperty('disabled')
  })

  it('shows game feedback returned by a document synchronization', async () => {
    vi.mocked(integrationsApi.getSync).mockResolvedValue({
      project_id: 'project-id',
      stage_id: 'stage-id',
      configured: true,
      type: 'word',
      path: '/book.docx',
      item_id: null,
      last_synced_at: null,
      desktop_only: true,
    })
    vi.mocked(integrationsApi.runSync).mockResolvedValue({
      changed: true,
      symbols: 100,
      sync: {
        project_id: 'project-id',
        stage_id: 'stage-id',
        configured: true,
        type: 'word',
        path: '/book.docx',
        item_id: null,
        last_synced_at: '2026-08-23T18:00:00',
        desktop_only: true,
      },
      progress: {
        project: projectFixture({ id: 'project-id' }),
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
        warning: null,
        game: {
          ok: true,
          message: 'Начислена награда за текст.',
          messages: ['Начислена награда за текст.'],
          result: { rewarded: true },
          state: gameStateFixture(),
        },
      },
    })
    const pinia = createPinia()
    const wrapper = mount(IntegrationsPage, {
      global: {
        plugins: [pinia],
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
    await wrapper.get('#sync-stage').setValue('stage-id')
    await flushPromises()
    const syncButton = wrapper.findAll('button')
      .find((button) => button.text().includes('Синхронизировать сейчас'))
    expect(syncButton).toBeDefined()

    await syncButton?.trigger('click')
    await flushPromises()

    expect(useNotificationsStore(pinia).notifications).toContainEqual(expect.objectContaining({
      kind: 'success',
      message: 'Начислена награда за текст.',
    }))
    expect(useNotificationsStore(pinia).notifications).toContainEqual(expect.objectContaining({
      kind: 'success',
      message: 'В проект добавлено 100 символов',
    }))
    wrapper.unmount()
  })

  it('shows the project-unit delta returned by a Word import', async () => {
    const imported: WordImportResult = {
      changed: true,
      symbols: 100,
      project: projectFixture({ id: 'project-id', total: 100 }),
      progress: {
        project: projectFixture({ id: 'project-id', total: 100 }),
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
        warning: null,
        game: null,
      },
    }
    const WordUploadCardStub = defineComponent({
      emits: ['imported'],
      setup(_, { emit }) {
        return {
          emitImported: () => emit('imported', imported, null),
        }
      },
      template: '<button data-testid="word-import" @click="emitImported">Импорт</button>',
    })
    const pinia = createPinia()
    const wrapper = mount(IntegrationsPage, {
      global: {
        plugins: [pinia],
        stubs: {
          IonContent: { template: '<div><slot /></div>' },
          IonPage: { template: '<div><slot /></div>' },
          IonIcon: true,
          IonSpinner: true,
          StatePanel: true,
          WordUploadCard: WordUploadCardStub,
        },
      },
    })
    await flushPromises()

    await wrapper.get('[data-testid="word-import"]').trigger('click')

    expect(useNotificationsStore(pinia).notifications).toContainEqual(expect.objectContaining({
      kind: 'success',
      message: 'В проект добавлено 100 символов',
    }))
    wrapper.unmount()
  })
})
