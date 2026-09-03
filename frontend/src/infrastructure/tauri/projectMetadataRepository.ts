import { invoke } from '@tauri-apps/api/core'

import type { ProjectMetadataPatch, ProjectMetadataRepository } from '@/core/repositories/projectMetadata'
import type { Project } from '@/types/api'

export class TauriProjectMetadataRepository implements ProjectMetadataRepository {
  updateMetadata(projectId: string, patch: ProjectMetadataPatch): Promise<Project> {
    return invoke<Project>('update_project_metadata', { projectId, patch })
  }

  reorderProjects(orderedProjectIds: string[]): Promise<Project[]> {
    return invoke<Project[]>('reorder_projects', { projectIds: orderedProjectIds })
  }
}
