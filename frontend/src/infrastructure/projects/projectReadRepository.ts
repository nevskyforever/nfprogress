import type { ProjectReadRepository } from '@/core/repositories/projects'
import type { ProjectListQuery } from '@/types/api'
import { ApiProjectReadRepository } from '@/infrastructure/api/projectReadRepository'
import { SQLiteProjectReadRepository } from '@/infrastructure/sqlite/projectReadRepository'

const apiRepository = new ApiProjectReadRepository()

function desktopRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

class FallbackProjectReadRepository implements ProjectReadRepository {
  private readonly sqlite = new SQLiteProjectReadRepository()

  async listProjects(query: ProjectListQuery = {}, signal?: AbortSignal) {
    // The mirror has no project_order column. Preserve manual PKL ordering via API.
    if (!desktopRuntime() || (query.sort ?? 'manual') === 'manual') {
      return apiRepository.listProjects(query, signal)
    }
    try {
      return await this.sqlite.listProjects(query)
    } catch (error) {
      console.warn('SQLite project list unavailable; using API.', error)
      return apiRepository.listProjects(query, signal)
    }
  }

  async getProject(id: string, signal?: AbortSignal) {
    if (!desktopRuntime()) return apiRepository.getProject(id, signal)
    try {
      const project = await this.sqlite.getProject(id)
      // A stale mirror can be healthy yet miss a newly-created project.
      return project ?? apiRepository.getProject(id, signal)
    } catch (error) {
      console.warn('SQLite project read unavailable; using API.', error)
      return apiRepository.getProject(id, signal)
    }
  }
}

let repository: ProjectReadRepository | undefined
export function getProjectReadRepository(): ProjectReadRepository {
  repository ??= new FallbackProjectReadRepository()
  return repository
}
