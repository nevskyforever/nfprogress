import { invoke } from '@tauri-apps/api/core'

import type {
  ManualProgressInput,
  ProgressRepository,
  RemoveProgressInput,
} from '@/core/repositories/progress'
import type { ProgressResult, Project } from '@/types/api'

export class TauriProgressRepository implements ProgressRepository {
  add(input: ManualProgressInput): Promise<ProgressResult> {
    const command = input.stageId ? 'add_stage_progress' : 'add_project_progress'
    return invoke<ProgressResult>(command, {
      projectId: input.projectId,
      ...(input.stageId ? { stageId: input.stageId } : {}),
      newTotal: input.newTotal,
    })
  }

  remove(input: RemoveProgressInput): Promise<Project> {
    return invoke<Project>('delete_progress', {
      projectId: input.projectId,
      entryId: input.entryId,
      stageId: input.stageId ?? null,
    })
  }
}
