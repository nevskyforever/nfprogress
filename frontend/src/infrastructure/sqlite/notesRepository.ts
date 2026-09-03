import { invoke } from '@tauri-apps/api/core'

import type { NotesRepository } from '@/core/repositories/notes'
import type {
  JsonObject,
  MindMapResponse,
  NoteOrderResponse,
  NotesResponse,
  NotesScope,
  ProjectNote,
  ProjectNotePatch,
  XMindImportResponse,
} from '@/types/notes'
import { ApiNotesRepository } from '@/infrastructure/api/notesRepository'

function nativeScope(scope: NotesScope): { projectId: string; stageId: string | null } {
  return { projectId: scope.projectId, stageId: scope.stageId ?? null }
}

export class SQLiteNotesRepository implements NotesRepository {
  private readonly mapApi = new ApiNotesRepository()
  private readonly sourceTypes = new Map<string, ProjectNote['source_type']>()

  private remember(notes: ProjectNote[]): void {
    for (const note of notes) this.sourceTypes.set(note.id, note.source_type)
  }

  async list(scope: NotesScope): Promise<NotesResponse> {
    const response = await invoke<NotesResponse>('list_notes', nativeScope(scope))
    this.remember(response.notes)
    return response
  }

  async get(scope: NotesScope, noteId: string): Promise<ProjectNote> {
    const note = await invoke<ProjectNote | null>('get_note', { ...nativeScope(scope), noteId })
    if (!note) throw new Error('Заметка не найдена.')
    this.remember([note])
    return note
  }

  async create(scope: NotesScope): Promise<ProjectNote> {
    const note = await invoke<ProjectNote>('create_note', nativeScope(scope))
    this.remember([note])
    return note
  }

  async update(scope: NotesScope, noteId: string, patch: ProjectNotePatch): Promise<ProjectNote> {
    const update = this.sourceTypes.get(noteId)
    const note = update === 'mindmap'
      ? await this.mapApi.update(scope, noteId, patch)
      : await invoke<ProjectNote>('update_note', { ...nativeScope(scope), noteId, patch })
    this.remember([note])
    return note
  }

  async delete(scope: NotesScope, noteId: string): Promise<void> {
    if (this.sourceTypes.get(noteId) === 'mindmap') {
      await this.mapApi.delete(scope, noteId)
    } else {
      await invoke('delete_note', { ...nativeScope(scope), noteId })
    }
    this.sourceTypes.delete(noteId)
  }

  reorder(scope: NotesScope, noteIds: string[]): Promise<NoteOrderResponse> {
    return invoke<NoteOrderResponse>('reorder_notes', { ...nativeScope(scope), noteIds })
  }

  mindMap(scope: NotesScope): Promise<MindMapResponse> { return this.mapApi.mindMap(scope) }
  saveMindMap(scope: NotesScope, data: JsonObject): Promise<MindMapResponse> { return this.mapApi.saveMindMap(scope, data) }
  importXMind(scope: NotesScope, file: File): Promise<XMindImportResponse> { return this.mapApi.importXMind(scope, file) }
}
