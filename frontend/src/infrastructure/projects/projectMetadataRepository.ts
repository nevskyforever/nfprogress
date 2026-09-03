import type { ProjectMetadataPatch, ProjectMetadataRepository } from '@/core/repositories/projectMetadata'
import { ApiProjectMetadataRepository } from '@/infrastructure/api/projectMetadataRepository'
import { TauriProjectMetadataRepository } from '@/infrastructure/tauri/projectMetadataRepository'

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

class PlatformProjectMetadataRepository implements ProjectMetadataRepository {
  private readonly api = new ApiProjectMetadataRepository()
  private readonly tauri = new TauriProjectMetadataRepository()

  private get active(): ProjectMetadataRepository {
    return isTauriRuntime() ? this.tauri : this.api
  }

  updateMetadata(projectId: string, patch: ProjectMetadataPatch) {
    return this.active.updateMetadata(projectId, patch)
  }

  reorderProjects(orderedProjectIds: string[]) {
    return this.active.reorderProjects(orderedProjectIds)
  }
}

let repository: ProjectMetadataRepository | undefined
export function getProjectMetadataRepository(): ProjectMetadataRepository {
  repository ??= new PlatformProjectMetadataRepository()
  return repository
}
