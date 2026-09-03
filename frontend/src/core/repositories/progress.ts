import type { ProgressResult, Project } from '@/types/api'

/**
 * Manual progress is the only generic progress mutation currently exposed by
 * the project UI. The server remains authoritative for totals, dates, and all
 * cross-domain effects.
 */
export interface ManualProgressInput {
  kind: 'manual'
  projectId: string
  stageId?: string | null
  newTotal: number
}

export interface RemoveProgressInput {
  projectId: string
  entryId: string
  stageId?: string | null
}

export interface ProgressRepository {
  add(input: ManualProgressInput): Promise<ProgressResult>
  remove(input: RemoveProgressInput): Promise<Project>
}
