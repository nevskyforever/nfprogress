import { notesApi } from '@/api/notes'
import type { NotesRepository } from '@/core/repositories/notes'

export class ApiNotesRepository implements NotesRepository {
  list = (scope: Parameters<typeof notesApi.list>[0]) => notesApi.list(scope)
  get = (scope: Parameters<typeof notesApi.get>[0], noteId: string) => notesApi.get(scope, noteId)
  create = (scope: Parameters<typeof notesApi.create>[0]) => notesApi.create(scope)
  update = (scope: Parameters<typeof notesApi.update>[0], noteId: string, patch: Parameters<typeof notesApi.update>[2]) => notesApi.update(scope, noteId, patch)
  delete = (scope: Parameters<typeof notesApi.remove>[0], noteId: string) => notesApi.remove(scope, noteId)
  reorder = (scope: Parameters<typeof notesApi.reorder>[0], noteIds: string[]) => notesApi.reorder(scope, noteIds)
  mindMap = (scope: Parameters<typeof notesApi.mindMap>[0]) => notesApi.mindMap(scope)
  saveMindMap = (scope: Parameters<typeof notesApi.saveMindMap>[0], data: Parameters<typeof notesApi.saveMindMap>[1]) => notesApi.saveMindMap(scope, data)
  importXMind = (scope: Parameters<typeof notesApi.importXMind>[0], file: File) => notesApi.importXMind(scope, file)
}
