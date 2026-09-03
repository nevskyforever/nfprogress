import type { Project } from '@/types/api'

/** Explicitly allow-listed metadata exposed by the P2 boundary. */
export interface ProjectMetadataPatch {
  name?: string
  goal?: number
  unit?: Project['unit']
  deadline?: string | null
  infinite?: boolean
}

export interface ProjectMetadataRepository {
  updateMetadata(projectId: string, patch: ProjectMetadataPatch): Promise<Project>
  reorderProjects(orderedProjectIds: string[]): Promise<Project[]>
}
