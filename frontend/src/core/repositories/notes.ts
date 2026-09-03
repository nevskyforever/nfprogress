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

export interface NotesRepository {
  list(scope: NotesScope): Promise<NotesResponse>
  get(scope: NotesScope, noteId: string): Promise<ProjectNote>
  create(scope: NotesScope): Promise<ProjectNote>
  update(scope: NotesScope, noteId: string, patch: ProjectNotePatch): Promise<ProjectNote>
  delete(scope: NotesScope, noteId: string): Promise<void>
  reorder(scope: NotesScope, noteIds: string[]): Promise<NoteOrderResponse>
  mindMap(scope: NotesScope): Promise<MindMapResponse>
  saveMindMap(scope: NotesScope, data: JsonObject): Promise<MindMapResponse>
  importXMind(scope: NotesScope, file: File): Promise<XMindImportResponse>
}
