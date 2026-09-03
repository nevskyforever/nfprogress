import { projectsApi } from '@/api/projects'
import type { ProjectMetadataPatch, ProjectMetadataRepository } from '@/core/repositories/projectMetadata'

export class ApiProjectMetadataRepository implements ProjectMetadataRepository {
  updateMetadata(projectId: string, patch: ProjectMetadataPatch) {
    return projectsApi.updateMetadata(projectId, patch)
  }

  reorderProjects(orderedProjectIds: string[]) {
    return projectsApi.reorder(orderedProjectIds)
  }
}
