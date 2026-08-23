import { apiRequest } from './client'
import type {
  ScrivenerItem,
  SyncBatchResult,
  SyncConfigure,
  SyncRunResult,
  SyncSummary,
  WordCountResult,
  WordImportResult,
} from '@/types/integrations'

function projectPath(projectId: string): string {
  return `/api/projects/${encodeURIComponent(projectId)}`
}

function projectSyncPath(projectId: string): string {
  return `${projectPath(projectId)}/sync`
}

function stageQuery(stageId?: string | null): string {
  if (!stageId) return ''
  return `?${new URLSearchParams({ stage_id: stageId }).toString()}`
}

export const integrationsApi = {
  getSync(projectId: string, stageId?: string | null): Promise<SyncSummary> {
    return apiRequest<SyncSummary>(`${projectSyncPath(projectId)}${stageQuery(stageId)}`)
  },

  configureSync(projectId: string, payload: SyncConfigure): Promise<SyncSummary> {
    return apiRequest<SyncSummary>(projectSyncPath(projectId), {
      method: 'PUT',
      body: payload,
    })
  },

  removeSync(projectId: string, stageId?: string | null): Promise<SyncSummary> {
    return apiRequest<SyncSummary>(`${projectSyncPath(projectId)}${stageQuery(stageId)}`, {
      method: 'DELETE',
    })
  },

  runSync(projectId: string, stageId?: string | null): Promise<SyncRunResult> {
    return apiRequest<SyncRunResult>(
      `${projectSyncPath(projectId)}/run${stageQuery(stageId)}`,
      { method: 'POST' },
    )
  },

  runAllSync(): Promise<SyncBatchResult> {
    return apiRequest<SyncBatchResult>('/api/integrations/sync/run-all', {
      method: 'POST',
    })
  },

  inspectScrivener(path: string): Promise<ScrivenerItem[]> {
    const params = new URLSearchParams({ path })
    return apiRequest<ScrivenerItem[]>(`/api/integrations/scrivener/items?${params.toString()}`)
  },

  countWord(file: File): Promise<WordCountResult> {
    const body = new FormData()
    body.set('file', file, file.name)
    return apiRequest<WordCountResult>('/api/integrations/word/count', {
      method: 'POST',
      rawBody: body,
    })
  },

  importWord(
    projectId: string,
    file: File,
    stageId?: string | null,
  ): Promise<WordImportResult> {
    const body = new FormData()
    body.set('file', file, file.name)
    return apiRequest<WordImportResult>(
      `${projectPath(projectId)}/imports/word${stageQuery(stageId)}`,
      { method: 'POST', rawBody: body },
    )
  },
}
