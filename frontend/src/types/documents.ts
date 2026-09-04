import type { ProgressResult } from './api'

export type TiptapDocument = { type: 'doc'; content?: Array<Record<string, unknown>> }

export interface ProjectDocument {
  document_id?: string
  project_id: string
  stage_id: string | null
  content: TiptapDocument
  content_format?: string
  title?: string
  created_at?: string | null
  exists: boolean
  updated_at: string | null
  revision?: number
  extensions?: Record<string, unknown>
  docx_path: string | null
  sync_state: 'unlinked' | 'synced' | 'local_changed' | 'external_changed' | 'word_changed' | 'conflict' | string
  last_synced_hash: string | null
  last_synced_at: string | null
  local_dirty: boolean
  word_dirty: boolean
  symbols: number
  has_content: boolean
}

export interface DocumentScope { projectId: string; stageId?: string }

export interface DocumentProgressResult {
  changed: boolean
  symbols: number
  progress: ProgressResult | null
  document?: ProjectDocument
}

export interface DocumentRepository {
  list(): Promise<ProjectDocument[]>
  get(scope: DocumentScope): Promise<ProjectDocument>
  save(scope: DocumentScope, content: TiptapDocument): Promise<ProjectDocument>
  link(scope: DocumentScope, filePath: string): Promise<ProjectDocument>
  writeDocx(scope: DocumentScope, contentBase64: string): Promise<ProjectDocument>
  writeDocxContent(scope: DocumentScope, content: TiptapDocument): Promise<ProjectDocument>
  external(scope: DocumentScope): Promise<{ state: string; content_base64?: string; hash?: string }>
  acceptWord(scope: DocumentScope, content: TiptapDocument, sourceHash: string): Promise<ProjectDocument>
  recordProgress(scope: DocumentScope, content?: TiptapDocument): Promise<DocumentProgressResult>
  parseWord(bytes: Uint8Array, filename: string): Promise<{ content: TiptapDocument; symbols: number; hash: string }>
}
