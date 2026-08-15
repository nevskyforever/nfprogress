import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { notesApi } from '@/api/notes'
import { mindMapFixture, noteFixture } from '@/test/noteFixtures'

import { useProjectNotes } from './useProjectNotes'

vi.mock('@/api/notes', () => ({
  notesApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    reorder: vi.fn(),
    mindMap: vi.fn(),
    saveMindMap: vi.fn(),
  },
}))

describe('useProjectNotes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads notes and their map together for one project scope', async () => {
    const note = noteFixture()
    const map = mindMapFixture()
    vi.mocked(notesApi.list).mockResolvedValue({
      notes: [note],
      read_only: false,
      context: { hasStages: false, stages: [] },
    })
    vi.mocked(notesApi.mindMap).mockResolvedValue(map)
    const workspace = useProjectNotes(ref('project-id'), ref(null))

    await workspace.load()

    expect(notesApi.list).toHaveBeenCalledWith({ projectId: 'project-id', stageId: null })
    expect(workspace.notes.value).toEqual([note])
    expect(workspace.mindMap.value).toEqual(map)
    expect(workspace.loading.value).toBe(false)
  })

  it('replaces cards from authoritative map synchronization response', async () => {
    const synchronized = noteFixture({
      id: 'mindmap-note',
      source_type: 'mindmap',
      source_node_id: 'node-id',
      content_format: 'plain',
      content: 'Обновлено на карте',
    })
    const response = mindMapFixture({ notes: [synchronized] })
    vi.mocked(notesApi.saveMindMap).mockResolvedValue(response)
    const workspace = useProjectNotes(ref('project-id'), ref(null))

    await workspace.saveMindMap(response.data ?? {})

    expect(workspace.notes.value).toEqual([synchronized])
    expect(workspace.mindMap.value).toEqual(response)
  })

  it('does not apply a late autosave response to a newly selected stage', async () => {
    let finishRequest: ((value: ReturnType<typeof mindMapFixture>) => void) | undefined
    vi.mocked(notesApi.saveMindMap).mockReturnValue(
      new Promise((resolve) => {
        finishRequest = resolve
      }),
    )
    const selectedStage = ref<string | null>('stage-one')
    const workspace = useProjectNotes(ref('project-id'), selectedStage)
    const save = workspace.saveMindMap(
      { nodeData: { id: 'stage-one-root' } },
      { projectId: 'project-id', stageId: 'stage-one' },
    )

    selectedStage.value = 'stage-two'
    finishRequest?.(mindMapFixture({ stage_id: 'stage-one', name: 'Первый этап' }))
    await save

    expect(notesApi.saveMindMap).toHaveBeenCalledWith(
      { projectId: 'project-id', stageId: 'stage-one' },
      { nodeData: { id: 'stage-one-root' } },
    )
    expect(workspace.mindMap.value).toBeNull()
  })
})
