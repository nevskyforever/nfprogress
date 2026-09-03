import { projectsApi } from '@/api/projects'
import type { ProjectReadRepository } from '@/core/repositories/projects'
import type { ProjectListQuery } from '@/types/api'

export class ApiProjectReadRepository implements ProjectReadRepository {
  listProjects(query: ProjectListQuery = {}, signal?: AbortSignal) {
    return projectsApi.list(query, signal)
  }

  async getProject(id: string, signal?: AbortSignal) {
    return projectsApi.get(id, signal)
  }
}
