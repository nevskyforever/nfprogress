import type { ProgressResult, Project } from './api'

export type SyncType = 'word' | 'scrivener'

export interface SyncSummary {
  project_id: string
  stage_id: string | null
  configured: boolean
  type: SyncType | null
  path: string | null
  item_id: string | null
  last_synced_at: string | null
  desktop_only: true
}

export interface SyncConfigure {
  type: SyncType
  path: string
  stage_id?: string | null
  item_id?: string | null
}

export interface ProjectSyncs {
  project_id: string
  syncs: SyncSummary[]
}

export interface SyncRunResult {
  changed: boolean
  symbols: number
  sync: SyncSummary
  progress: ProgressResult | null
}

export interface ScrivenerItem {
  id: string
  title: string
  children: ScrivenerItem[]
}

export interface SyncBatchError {
  code: string
  message: string
}

export interface SyncBatchItem {
  project_id: string
  stage_id: string | null
  ok: boolean
  changed: boolean
  symbols: number | null
  progress?: ProgressResult | null
  error: SyncBatchError | null
}

export interface SyncBatchResult {
  checked: number
  changed: number
  failed: number
  items: SyncBatchItem[]
}

export interface WordCountResult {
  symbols: number
}

export interface WordImportResult {
  changed: boolean
  symbols: number
  project: Project
  progress: ProgressResult | null
}
