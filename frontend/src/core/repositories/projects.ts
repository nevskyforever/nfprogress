import type { Project, ProjectListQuery } from '@/types/api'

/** Read-only project boundary shared by desktop, web, and mobile clients. */
export interface ProjectReadRepository {
  listProjects(query?: ProjectListQuery, signal?: AbortSignal): Promise<Project[]>
  getProject(id: string, signal?: AbortSignal): Promise<Project | null>
}
