import { apiRequest } from './client'
import type { DocumentProgressResult, DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

function path(scope: DocumentScope, suffix = ''): string {
  const query = scope.stageId ? `?${new URLSearchParams({ stage_id: scope.stageId })}` : ''
  return `/api/documents/${encodeURIComponent(scope.projectId)}${suffix}${query}`
}

export const documentsApi = {
  list: () => apiRequest<ProjectDocument[]>('/api/documents/list'),
  get: (scope: DocumentScope) => apiRequest<ProjectDocument>(path(scope)),
  save: (scope: DocumentScope, content: TiptapDocument) => apiRequest<ProjectDocument>(path(scope), { method: 'PUT', body: { content } }),
  link: (scope: DocumentScope, filePath: string) => apiRequest<ProjectDocument>(path(scope, '/link'), { method: 'PUT', body: { path: filePath } }),
  writeDocx: (scope: DocumentScope, contentBase64: string) => apiRequest<ProjectDocument>(path(scope, '/docx'), { method: 'PUT', body: { content_base64: contentBase64 } }),
  external: (scope: DocumentScope) => apiRequest<{ state: string; content_base64?: string; hash?: string }>(path(scope, '/external')),
  acceptWord: (scope: DocumentScope, content: TiptapDocument, sourceHash: string) => apiRequest<ProjectDocument>(path(scope, '/accept-word'), { method: 'PUT', body: { content, source_hash: sourceHash } }),
  recordProgress: (scope: DocumentScope, content?: TiptapDocument) => apiRequest<DocumentProgressResult>(path(scope, '/progress'), {
    method: 'POST',
    ...(content ? { body: { content } } : {}),
  }),
}
