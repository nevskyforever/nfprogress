import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { documentsApi } from '@/api/documents'
import { projectsApi } from '@/api/projects'
import { announceDataChange } from '@/services/dataChanges'
import { projectFixture } from '@/test/fixtures'
import type { ProjectDocument } from '@/types/documents'

import TextsPage from './TextsPage.vue'

vi.mock('@/api/documents', () => ({
  documentsApi: { list: vi.fn() },
}))
vi.mock('@/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}))

const ionicStubs = {
  IonContent: { template: '<div><slot /></div>' },
  IonIcon: true,
  IonPage: { template: '<div><slot /></div>' },
  RouterLink: { template: '<a><slot /></a>' },
}

function documentFixture(stageId: string | null, symbols = 12): ProjectDocument {
  return {
    project_id: 'project-id',
    stage_id: stageId,
    content: { type: 'doc' },
    exists: true,
    updated_at: '2026-08-31T10:00:00Z',
    docx_path: null,
    sync_state: 'unlinked',
    last_synced_hash: null,
    last_synced_at: null,
    local_dirty: true,
    word_dirty: false,
    symbols,
    has_content: true,
  }
}

function mountPage() {
  return mount(TextsPage, {
    global: { plugins: [createPinia()], stubs: ionicStubs },
  })
}

describe('TextsPage', () => {
  beforeEach(() => {
    vi.mocked(documentsApi.list).mockReset()
    vi.mocked(projectsApi.list).mockReset()
    vi.mocked(documentsApi.list).mockResolvedValue([
      documentFixture(null),
      documentFixture('stage-id', 24),
    ])
    vi.mocked(projectsApi.list).mockResolvedValue([
      projectFixture({
        id: 'project-id',
        name: 'Роман',
        stages: [projectFixture({
          id: 'stage-id',
          name: 'Глава 1',
          parent_project_id: 'project-id',
        })],
        stages_enabled: true,
      }),
    ])
  })

  it('displays project and stage documents with their names', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Роман')
    expect(wrapper.text()).toContain('текст проекта')
    expect(wrapper.text()).toContain('этап: Глава 1')
    expect(wrapper.findAll('a')).toHaveLength(2)
    wrapper.unmount()
  })

  it('filters project and stage documents by their names', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const search = wrapper.get('input[type="search"]')

    await search.setValue('роман')

    expect(wrapper.findAll('a')).toHaveLength(2)

    await search.setValue('глава')

    expect(wrapper.findAll('a')).toHaveLength(1)
    expect(wrapper.text()).toContain('этап: Глава 1')
    expect(wrapper.text()).not.toContain('текст проекта')

    await search.setValue('не существует')

    expect(wrapper.findAll('a')).toHaveLength(0)
    expect(wrapper.text()).toContain('Ничего не найдено')

    await wrapper.get('button[aria-label="Очистить поиск"]').trigger('click')
    expect(wrapper.findAll('a')).toHaveLength(2)
    wrapper.unmount()
  })

  it('reloads documents after project data changes', async () => {
    const wrapper = mountPage()
    await flushPromises()
    vi.mocked(documentsApi.list).mockResolvedValue([documentFixture('stage-id', 30)])

    announceDataChange('projects')
    await flushPromises()

    expect(documentsApi.list).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('этап: Глава 1')
    expect(wrapper.text()).not.toContain('текст проекта')
    wrapper.unmount()
  })
})
