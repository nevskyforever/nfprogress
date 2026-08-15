import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { projectsApi } from '@/api/projects'
import { projectFixture } from '@/test/fixtures'

import { useProjectsStore } from './projects'

vi.mock('@/api/projects', () => ({
  projectsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    setArchived: vi.fn(),
    complete: vi.fn(),
    createStage: vi.fn(),
    updateStage: vi.fn(),
    removeStage: vi.fn(),
    reorderStages: vi.fn(),
    completeStage: vi.fn(),
    recordProgress: vi.fn(),
    deleteProgress: vi.fn(),
    statistics: vi.fn(),
  },
}))

describe('projects store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads the filtered project list through the real API boundary', async () => {
    const project = projectFixture()
    vi.mocked(projectsApi.list).mockResolvedValue([project])
    const store = useProjectsStore()

    await store.load({ status: 'активен', search: 'дом', sort: 'updated' })

    expect(projectsApi.list).toHaveBeenCalledWith(
      { status: 'активен', search: 'дом', sort: 'updated' },
      expect.any(AbortSignal),
    )
    expect(store.projects).toEqual([project])
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('places a newly created project into current state immediately', async () => {
    const project = projectFixture({ id: 'new-project' })
    vi.mocked(projectsApi.create).mockResolvedValue(project)
    const store = useProjectsStore()

    const created = await store.create({
      name: project.name,
      goal: project.goal,
      unit: 'symbols',
    })

    expect(created).toEqual(project)
    expect(store.projects[0]).toEqual(project)
    expect(store.currentProject).toEqual(project)
    expect(store.creating).toBe(false)
  })

  it('reloads the complete parent project after a stage command', async () => {
    const initial = projectFixture({ stages_enabled: false })
    const createdStage = projectFixture({
      id: 'stage-1',
      name: 'Глава 1',
      parent_project_id: initial.id,
    })
    const updated = projectFixture({
      stages_enabled: true,
      stages: [createdStage],
    })
    vi.mocked(projectsApi.createStage).mockResolvedValue(createdStage)
    vi.mocked(projectsApi.get).mockResolvedValue(updated)
    const store = useProjectsStore()

    const result = await store.createStage(initial.id, { name: 'Глава 1', goal: 20_000 })

    expect(projectsApi.createStage).toHaveBeenCalledWith(initial.id, {
      name: 'Глава 1',
      goal: 20_000,
    })
    expect(projectsApi.get).toHaveBeenCalledWith(initial.id)
    expect(result).toEqual(updated)
    expect(store.currentProject).toEqual(updated)
  })

  it('applies an authoritative progress result without client-side calculations', async () => {
    const initial = projectFixture()
    const updated = projectFixture({
      total: 28_000,
      progress: 28,
      progress_entries: [
        {
          id: 'entry-1',
          new_total: 28_000,
          new_total_symbols: 28_000,
          added: 3_000,
          added_symbols: 3_000,
          added_progress: 3,
          created_at: '2026-08-15T12:00:00',
        },
      ],
    })
    vi.mocked(projectsApi.recordProgress).mockResolvedValue({
      project: updated,
      entry: updated.progress_entries[0]!,
      added_symbols: 3_000,
      game: null,
      warning: null,
    })
    const store = useProjectsStore()

    const result = await store.recordProgress(initial.id, { new_total: 28_000 })

    expect(projectsApi.recordProgress).toHaveBeenCalledWith(initial.id, { new_total: 28_000 })
    expect(result?.added_symbols).toBe(3_000)
    expect(store.currentProject).toEqual(updated)
  })
})
