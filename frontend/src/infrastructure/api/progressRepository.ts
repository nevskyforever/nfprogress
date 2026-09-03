import { projectsApi } from '@/api/projects'
import type {
  ManualProgressInput,
  ProgressRepository,
  RemoveProgressInput,
} from '@/core/repositories/progress'

export class ApiProgressRepository implements ProgressRepository {
  add(input: ManualProgressInput) {
    const payload = {
      new_total: input.newTotal,
      ...(input.stageId !== undefined && input.stageId !== null
        ? { stage_id: input.stageId }
        : {}),
    }
    return projectsApi.recordProgress(input.projectId, payload)
  }

  remove(input: RemoveProgressInput) {
    return projectsApi.deleteProgress(input.projectId, input.entryId, input.stageId ?? undefined)
  }
}
