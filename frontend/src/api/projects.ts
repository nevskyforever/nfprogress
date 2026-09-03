import { apiRequest } from './client'
import type { ProjectMetadataPatch } from '@/core/repositories/projectMetadata'
import type {
  ProgressCreate,
  ProgressResult,
  Project,
  ProjectCreate,
  ProjectListQuery,
  ProjectFolder,
  ProjectUpdate,
  EntityUpdate,
  GlobalStreakSummary,
  StageCreate,
  Statistics,
  TodaySummary,
} from '@/types/api'

function projectPath(projectId: string): string {
  return `/api/projects/${encodeURIComponent(projectId)}`
}

function stagePath(projectId: string, stageId: string): string {
  return `${projectPath(projectId)}/stages/${encodeURIComponent(stageId)}`
}

function queryString(query: ProjectListQuery): string {
  const params = new URLSearchParams()
  if (query.status) params.set('status', query.status)
  if (query.search?.trim()) params.set('search', query.search.trim())
  if (query.sort) params.set('sort', query.sort)
  const encoded = params.toString()
  return encoded ? `?${encoded}` : ''
}

export const projectsApi = {
  list(query: ProjectListQuery = {}, signal?: AbortSignal): Promise<Project[]> {
    return apiRequest<Project[]>(`/api/projects${queryString(query)}`, { signal })
  },

  folders(signal?: AbortSignal): Promise<ProjectFolder[]> {
    return apiRequest<ProjectFolder[]>('/api/projects/folders', { signal })
  },

  createFolder(name: string): Promise<ProjectFolder> {
    return apiRequest<ProjectFolder>('/api/projects/folders', { method: 'POST', body: { name } })
  },

  updateFolder(folderId: string, name: string): Promise<ProjectFolder> {
    return apiRequest<ProjectFolder>(`/api/projects/folders/${encodeURIComponent(folderId)}`, {
      method: 'PATCH', body: { name },
    })
  },

  removeFolder(folderId: string): Promise<void> {
    return apiRequest<void>(`/api/projects/folders/${encodeURIComponent(folderId)}`, { method: 'DELETE' })
  },

  reorder(projectIds: string[]): Promise<Project[]> {
    return apiRequest<Project[]>('/api/projects/order', {
      method: 'PUT', body: { project_ids: projectIds },
    })
  },

  get(projectId: string, signal?: AbortSignal): Promise<Project> {
    return apiRequest<Project>(projectPath(projectId), { signal })
  },

  today(signal?: AbortSignal): Promise<TodaySummary> {
    return apiRequest<TodaySummary>('/api/projects/today', { signal })
  },

  globalStreak(signal?: AbortSignal): Promise<GlobalStreakSummary> {
    return apiRequest<GlobalStreakSummary>('/api/projects/streaks/global', { signal })
  },

  create(payload: ProjectCreate): Promise<Project> {
    return apiRequest<Project>('/api/projects', { method: 'POST', body: payload })
  },

  update(projectId: string, payload: ProjectUpdate): Promise<Project> {
    return apiRequest<Project>(projectPath(projectId), { method: 'PATCH', body: payload })
  },

  updateMetadata(projectId: string, patch: ProjectMetadataPatch): Promise<Project> {
    return apiRequest<Project>(`${projectPath(projectId)}/metadata`, { method: 'PATCH', body: patch })
  },

  remove(projectId: string): Promise<void> {
    return apiRequest<void>(projectPath(projectId), { method: 'DELETE' })
  },

  setArchived(projectId: string, archived: boolean): Promise<Project> {
    return apiRequest<Project>(`${projectPath(projectId)}/archive`, {
      method: 'POST',
      body: { archived },
    })
  },

  complete(projectId: string): Promise<Project> {
    return apiRequest<Project>(`${projectPath(projectId)}/complete`, { method: 'POST' })
  },

  createStage(projectId: string, payload: StageCreate): Promise<Project> {
    return apiRequest<Project>(`${projectPath(projectId)}/stages`, {
      method: 'POST',
      body: payload,
    })
  },

  updateStage(projectId: string, stageId: string, payload: EntityUpdate): Promise<Project> {
    return apiRequest<Project>(stagePath(projectId, stageId), {
      method: 'PATCH',
      body: payload,
    })
  },

  removeStage(projectId: string, stageId: string): Promise<void> {
    return apiRequest<void>(stagePath(projectId, stageId), { method: 'DELETE' })
  },

  reorderStages(projectId: string, stageIds: string[]): Promise<Project> {
    return apiRequest<Project>(`${projectPath(projectId)}/stages/order`, {
      method: 'PUT',
      body: { stage_ids: stageIds },
    })
  },

  completeStage(projectId: string, stageId: string): Promise<Project> {
    return apiRequest<Project>(`${stagePath(projectId, stageId)}/complete`, { method: 'POST' })
  },

  recordProgress(projectId: string, payload: ProgressCreate): Promise<ProgressResult> {
    return apiRequest<ProgressResult>(`${projectPath(projectId)}/progress`, {
      method: 'POST',
      body: payload,
    })
  },

  deleteProgress(projectId: string, entryId: string, stageId?: string): Promise<Project> {
    const params = new URLSearchParams()
    if (stageId) params.set('stage_id', stageId)
    const encoded = params.toString()
    const suffix = encoded ? `?${encoded}` : ''
    return apiRequest<Project>(
      `${projectPath(projectId)}/progress/${encodeURIComponent(entryId)}${suffix}`,
      { method: 'DELETE' },
    )
  },

  statistics(projectId: string, stageId?: string): Promise<Statistics> {
    const params = new URLSearchParams()
    if (stageId) params.set('stage_id', stageId)
    const encoded = params.toString()
    const suffix = encoded ? `?${encoded}` : ''
    return apiRequest<Statistics>(`${projectPath(projectId)}/statistics${suffix}`)
  },
}
