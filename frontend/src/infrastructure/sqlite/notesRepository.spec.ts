import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { SQLiteNotesRepository } from './notesRepository'

describe('SQLiteNotesRepository', () => {
  const repository = new SQLiteNotesRepository()
  const scope = { projectId: 'project-id', stageId: null }

  beforeEach(() => invoke.mockReset())

  it('uses typed note commands for desktop CRUD and ordering', async () => {
    invoke
      .mockResolvedValueOnce({ notes: [], read_only: false, context: { hasStages: false, stages: [] } })
      .mockResolvedValueOnce({ id: 'note-id' })
      .mockResolvedValueOnce({ id: 'note-id' })
      .mockResolvedValueOnce(undefined)
      .mockResolvedValueOnce({ changed: true, notes: [] })

    await repository.list(scope)
    await repository.create(scope)
    await repository.update(scope, 'note-id', { title: 'Новая' })
    await repository.delete(scope, 'note-id')
    await repository.reorder(scope, ['note-id'])

    expect(invoke).toHaveBeenNthCalledWith(1, 'list_notes', scope)
    expect(invoke).toHaveBeenNthCalledWith(2, 'create_note', scope)
    expect(invoke).toHaveBeenNthCalledWith(3, 'update_note', { ...scope, noteId: 'note-id', patch: { title: 'Новая' } })
    expect(invoke).toHaveBeenNthCalledWith(4, 'delete_note', { ...scope, noteId: 'note-id' })
    expect(invoke).toHaveBeenNthCalledWith(5, 'reorder_notes', { ...scope, noteIds: ['note-id'] })
  })
})
