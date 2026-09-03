import type {
  ManualProgressInput,
  ProgressRepository,
  RemoveProgressInput,
} from '@/core/repositories/progress'
import { ApiProgressRepository } from '@/infrastructure/api/progressRepository'
import { TauriProgressRepository } from '@/infrastructure/tauri/progressRepository'

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined
}

class PlatformProgressRepository implements ProgressRepository {
  private readonly api = new ApiProgressRepository()
  private readonly tauri = new TauriProgressRepository()

  private get active(): ProgressRepository {
    return isTauriRuntime() ? this.tauri : this.api
  }

  add(input: ManualProgressInput) {
    return this.active.add(input)
  }

  remove(input: RemoveProgressInput) {
    return this.active.remove(input)
  }
}

let repository: ProgressRepository | undefined
export function getProgressRepository(): ProgressRepository {
  repository ??= new PlatformProgressRepository()
  return repository
}
