import { apiRequest } from './client'
import { currentPlatform } from '@/platform/runtime'
import type { DocumentProgressResult, DocumentRepository, DocumentScope, ProjectDocument, TiptapDocument } from '@/types/documents'

function path(scope: DocumentScope, suffix = ''): string {
  const query = scope.stageId ? `?${new URLSearchParams({ stage_id: scope.stageId })}` : ''
  return `/api/documents/${encodeURIComponent(scope.projectId)}${suffix}${query}`
}

async function nativeInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(command, args)
}

function nativeScope(scope: DocumentScope): Record<string, unknown> {
  return { projectId: scope.projectId, stageId: scope.stageId ?? null }
}

export const documentsApi: DocumentRepository = {
  list: () => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument[]>('list_documents')
    : apiRequest<ProjectDocument[]>('/api/documents/list'),
  get: (scope: DocumentScope) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('get_document', { scope: nativeScope(scope) })
    : apiRequest<ProjectDocument>(path(scope)),
  save: (scope: DocumentScope, content: TiptapDocument) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('save_document', { command: { ...nativeScope(scope), content } })
    : apiRequest<ProjectDocument>(path(scope), { method: 'PUT', body: { content } }),
  link: (scope: DocumentScope, filePath: string) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('bind_document_file', { command: { ...nativeScope(scope), path: filePath } })
    : apiRequest<ProjectDocument>(path(scope, '/link'), { method: 'PUT', body: { path: filePath } }),
  writeDocx: (scope: DocumentScope, contentBase64: string) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('write_document_word', { command: { ...nativeScope(scope), contentBase64 } })
    : apiRequest<ProjectDocument>(path(scope, '/docx'), { method: 'PUT', body: { content_base64: contentBase64 } }),
  writeDocxContent: (scope: DocumentScope, content: TiptapDocument) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('write_document_word_content', { ...nativeScope(scope), content })
    : Promise.reject(new Error('Нативная запись DOCX доступна только в desktop-приложении.')),
  parseWord: (bytes: Uint8Array, filename: string) => currentPlatform() === 'tauri'
    ? nativeInvoke<{ content: TiptapDocument; symbols: number; hash: string }>('parse_word_document', { command: { bytes: Array.from(bytes), filename } })
    : Promise.reject(new Error('Нативный разбор DOCX доступен только в desktop-приложении.')),
  external: (scope: DocumentScope) => currentPlatform() === 'tauri'
    ? nativeInvoke<{ state: string; content_base64?: string; hash?: string }>('read_document_external', { scope: nativeScope(scope) })
    : apiRequest<{ state: string; content_base64?: string; hash?: string }>(path(scope, '/external')),
  acceptWord: (scope: DocumentScope, content: TiptapDocument, sourceHash: string) => currentPlatform() === 'tauri'
    ? nativeInvoke<ProjectDocument>('accept_document_external', { command: { ...nativeScope(scope), content, sourceHash } })
    : apiRequest<ProjectDocument>(path(scope, '/accept-word'), { method: 'PUT', body: { content, source_hash: sourceHash } }),
  recordProgress: (scope: DocumentScope, content?: TiptapDocument) => currentPlatform() === 'tauri'
    ? nativeInvoke<DocumentProgressResult>('record_document_progress', { command: { ...nativeScope(scope), ...(content ? { content } : {}) } })
    : apiRequest<DocumentProgressResult>(path(scope, '/progress'), {
      method: 'POST',
      ...(content ? { body: { content } } : {}),
    }),
}
