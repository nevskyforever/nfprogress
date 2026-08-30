export type TiptapDocument = { type: 'doc'; content?: Array<Record<string, unknown>> }

export interface ProjectDocument {
  project_id: string
  stage_id: string | null
  content: TiptapDocument
  exists: boolean
  updated_at: string | null
  docx_path: string | null
  sync_state: 'unlinked' | 'synced' | 'word_changed' | 'conflict' | string
  last_synced_hash: string | null
  last_synced_at: string | null
  local_dirty: boolean
  word_dirty: boolean
  symbols: number
  has_content: boolean
}

export interface DocumentScope { projectId: string; stageId?: string }
