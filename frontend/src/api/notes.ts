import { apiRequest } from './client'

import type {
  JsonObject,
  MindMapResponse,
  NoteOrderResponse,
  NotesResponse,
  NotesScope,
  ProjectNote,
  ProjectNotePatch,
} from '@/types/notes'

function projectPath(projectId: string): string {
  return `/api/projects/${encodeURIComponent(projectId)}`
}

function withScope(path: string, scope: NotesScope): string {
  if (!scope.stageId) return path
  const search = new URLSearchParams({ stage_id: scope.stageId })
  return `${path}?${search.toString()}`
}

export const notesApi = {
  list(scope: NotesScope): Promise<NotesResponse> {
    return apiRequest<NotesResponse>(withScope(`${projectPath(scope.projectId)}/notes`, scope))
  },

  create(scope: NotesScope): Promise<ProjectNote> {
    return apiRequest<ProjectNote>(withScope(`${projectPath(scope.projectId)}/notes`, scope), {
      method: 'POST',
    })
  },

  get(scope: NotesScope, noteId: string): Promise<ProjectNote> {
    const path = `${projectPath(scope.projectId)}/notes/${encodeURIComponent(noteId)}`
    return apiRequest<ProjectNote>(withScope(path, scope))
  },

  update(scope: NotesScope, noteId: string, patch: ProjectNotePatch): Promise<ProjectNote> {
    const path = `${projectPath(scope.projectId)}/notes/${encodeURIComponent(noteId)}`
    return apiRequest<ProjectNote>(withScope(path, scope), {
      method: 'PATCH',
      body: patch,
    })
  },

  remove(scope: NotesScope, noteId: string): Promise<void> {
    const path = `${projectPath(scope.projectId)}/notes/${encodeURIComponent(noteId)}`
    return apiRequest<void>(withScope(path, scope), { method: 'DELETE' })
  },

  reorder(scope: NotesScope, noteIds: string[]): Promise<NoteOrderResponse> {
    return apiRequest<NoteOrderResponse>(
      withScope(`${projectPath(scope.projectId)}/notes/order`, scope),
      {
        method: 'PUT',
        body: { note_ids: noteIds },
      },
    )
  },

  mindMap(scope: NotesScope): Promise<MindMapResponse> {
    return apiRequest<MindMapResponse>(
      withScope(`${projectPath(scope.projectId)}/mindmap`, scope),
    )
  },

  saveMindMap(scope: NotesScope, data: JsonObject): Promise<MindMapResponse> {
    return apiRequest<MindMapResponse>(
      withScope(`${projectPath(scope.projectId)}/mindmap`, scope),
      {
        method: 'PUT',
        body: { data },
      },
    )
  },
}
