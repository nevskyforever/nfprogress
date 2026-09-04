import type { ProjectReadRepository } from '@/core/repositories/projects'
import type { ProjectListQuery } from '@/types/api'
import { ApiProjectReadRepository } from '@/infrastructure/api/projectReadRepository'
import { SQLiteProjectReadRepository } from '@/infrastructure/sqlite/projectReadRepository'

const apiRepository = new ApiProjectReadRepository()

function desktopRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

class PlatformProjectReadRepository implements ProjectReadRepository {
  private readonly sqlite = new SQLiteProjectReadRepository()

  async listProjects(query: ProjectListQuery = {}, signal?: AbortSignal) {
    if (!desktopRuntime()) return apiRepository.listProjects(query, signal)
    return this.sqlite.listProjects(query)
  }

  async getProject(id: string, signal?: AbortSignal) {
    if (!desktopRuntime()) return apiRepository.getProject(id, signal)
    return this.sqlite.getProject(id)
  }
}

let repository: ProjectReadRepository | undefined
export function getProjectReadRepository(): ProjectReadRepository {
  repository ??= new PlatformProjectReadRepository()
  return repository
}
