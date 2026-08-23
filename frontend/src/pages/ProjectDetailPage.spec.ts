import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { integrationsApi } from '@/api/integrations'
import { shareProgressImage } from '@/platform/progressShare'
import { useNotificationsStore } from '@/stores/notifications'
import { projectFixture } from '@/test/fixtures'
import type { Statistics } from '@/types/api'

import ProjectDetailPage from './ProjectDetailPage.vue'

const pushRoute = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { projectId: 'project-id' } }),
  useRouter: () => ({ replace: vi.fn(), push: pushRoute }),
}))

vi.mock('@/api/integrations', () => ({
  integrationsApi: {
    getSync: vi.fn(),
    runSync: vi.fn(),
  },
}))

vi.mock('@/api/projects', () => ({
  projectsApi: {
    get: vi.fn(),
    statistics: vi.fn(),
  },
}))

vi.mock('@/platform/progressShare', () => ({
  progressShareTitle: (name: string, parentName?: string) => parentName ? `${parentName}: ${name}` : name,
  shareProgressImage: vi.fn(),
}))

const statisticsFixture: Statistics = {
  entity_id: 'project-id',
  unit: 'symbols',
  metrics: {
    entries_count: 0,
    total: 0,
    average_symbols_per_active_day: 0,
    average_symbols_per_entry: 0,
    average_entries_per_active_day: 0,
    freezes_used: 0,
    best_day: null,
    best_weekday: null,
    current_streak: 0,
    max_streak: 0,
    days_since_start: 0,
    active_days: 0,
    active_days_percent: 0,
  },
  timeline: [],
}

function workspaceStubs() {
  return {
    IonContent: { template: '<div><slot /></div>' },
    IonIcon: true,
    IonPage: { template: '<div><slot /></div>' },
    IonSpinner: true,
    ProgressWorkspace: true,
    ProjectEditDialog: true,
    RouterLink: { template: '<a><slot /></a>' },
    StageDialog: true,
    StageWorkspace: {
      props: ['project'],
      emits: ['share'],
      template: '<button class="stage-share" type="button" @click="$emit(\'share\', project.stages[0])">stage share</button>',
    },
    StatePanel: true,
    StatisticsWorkspace: true,
  }
}

function mountWorkspace(pinia = createPinia()) {
  return mount(ProjectDetailPage, {
    global: {
      plugins: [pinia],
      stubs: workspaceStubs(),
    },
  })
}

describe('ProjectDetailPage progress sharing', () => {
  beforeEach(() => {
    vi.mocked(projectsApi.get).mockReset()
    vi.mocked(projectsApi.statistics).mockReset()
    vi.mocked(shareProgressImage).mockReset()
    vi.mocked(integrationsApi.getSync).mockReset()
    vi.mocked(integrationsApi.runSync).mockReset()
    pushRoute.mockReset()
    const stage = projectFixture({
      id: 'stage-id',
      name: 'Глава 3',
      progress: 50,
      parent_project_id: 'project-id',
    })
    vi.mocked(projectsApi.get).mockResolvedValue(projectFixture({
      id: 'project-id',
      name: 'Дом у моря',
      stages_enabled: true,
      stages: [stage],
    }))
    vi.mocked(projectsApi.statistics).mockResolvedValue(statisticsFixture)
    vi.mocked(shareProgressImage).mockResolvedValue('clipboard')
    vi.mocked(integrationsApi.getSync).mockResolvedValue({
      project_id: 'project-id',
      stage_id: 'stage-id',
      configured: false,
      type: null,
      path: null,
      item_id: null,
      last_synced_at: null,
      desktop_only: true,
    })
  })

  it('creates cards locally for both a project and its selected stage', async () => {
    const pinia = createPinia()
    const wrapper = mountWorkspace(pinia)
    await flushPromises()

    await wrapper.get('button[aria-label="Поделиться прогрессом «Дом у моря»"]').trigger('click')
    await flushPromises()
    await wrapper.get('.stage-share').trigger('click')
    await flushPromises()

    expect(shareProgressImage).toHaveBeenNthCalledWith(1, {
      title: 'Дом у моря',
      progress: 25,
    })
    expect(shareProgressImage).toHaveBeenNthCalledWith(2, {
      title: 'Дом у моря: Глава 3',
      progress: 50,
    })
    expect(useNotificationsStore(pinia).notifications).toContainEqual(expect.objectContaining({
      kind: 'info',
      message: 'Картинка прогресса добавлена в буфер обмена',
    }))
  })

  it('does not enable a progress card for a goal-free project', async () => {
    vi.mocked(projectsApi.get).mockResolvedValue(projectFixture({
      id: 'project-id',
      infinite: true,
      goal: null,
    }))
    const wrapper = mountWorkspace()
    await flushPromises()

    const shareButton = wrapper.get('button[aria-label*="Поделиться прогрессом"]')
    expect(shareButton.attributes('disabled')).toBeDefined()
    expect(shareProgressImage).not.toHaveBeenCalled()
  })

  it('keeps project sync visible and opens setup for the selected stage', async () => {
    const wrapper = mountWorkspace()
    await flushPromises()

    await wrapper.get('.project-sync-button').trigger('click')
    await flushPromises()

    expect(integrationsApi.getSync).toHaveBeenCalledWith('project-id', 'stage-id')
    expect(pushRoute).toHaveBeenCalledWith({
      name: 'integrations',
      query: { projectId: 'project-id', stageId: 'stage-id' },
    })
  })
})
