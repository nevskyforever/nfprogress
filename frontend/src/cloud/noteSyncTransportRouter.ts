import { encryptedSyncV2Api, parseV2Capabilities, type V2Capabilities } from '@/api/encryptedSyncV2'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { NoteSyncOrchestratorOptions, NoteSyncOrchestratorResult } from './noteSyncOrchestrator'
import type { NoteSyncV2CycleResult } from './noteSyncV2Cycle'
import type { NoteSyncV3CycleResult } from './noteSyncV3Cycle'

export type NoteSyncProductionResult =
  | { readonly transport_version: 1, readonly cutover_epoch: number, readonly cycle: NoteSyncOrchestratorResult,
      readonly hasRemainingWork: boolean, readonly blocked: readonly string[], readonly errors: NoteSyncOrchestratorResult['errors'] }
  | { readonly transport_version: 2, readonly cutover_epoch: number, readonly cycle: NoteSyncV2CycleResult,
      readonly hasRemainingWork: boolean, readonly blocked: readonly string[], readonly errors: NoteSyncV2CycleResult['errors'] }
  | { readonly transport_version: 3, readonly cutover_epoch: number, readonly cycle: NoteSyncV3CycleResult,
      readonly hasRemainingWork: boolean, readonly blocked: readonly string[], readonly errors: NoteSyncV3CycleResult['errors'] }

interface CycleRunner<T> {
  runOnce(accountId: string, deviceId: string, options?: NoteSyncOrchestratorOptions): Promise<T>
}

interface OrdinaryUploader {
  uploadOnce(accountId: string): Promise<unknown>
}

/** Selects one transport from fresh server authority for each top-level operation. */
export class NoteSyncTransportRouter {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly v1: CycleRunner<NoteSyncOrchestratorResult>,
    private readonly v2: CycleRunner<NoteSyncV2CycleResult>,
    private readonly v1Uploader: OrdinaryUploader,
    private readonly v2Uploader: OrdinaryUploader,
    private readonly capabilities: Pick<typeof encryptedSyncV2Api, 'capabilities'> = encryptedSyncV2Api,
    private readonly v3?: CycleRunner<NoteSyncV3CycleResult>,
  ) {}

  private async select(): Promise<V2Capabilities> {
    const context: AuthContextSnapshot = this.auth.requireContext()
    const response = await this.auth.authorized(token => this.capabilities.capabilities(token))
    if (!this.auth.isCurrent(context) || response.context.userId !== context.userId
      || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    return parseV2Capabilities(response.value)
  }

  async runOnce(accountId: string, deviceId: string, options?: NoteSyncOrchestratorOptions): Promise<NoteSyncProductionResult> {
    const selected = await this.select()
    if (selected.writer_transport_version === 1) {
      const cycle = await this.v1.runOnce(accountId, deviceId, options)
      return { transport_version: 1, cutover_epoch: selected.cutover_epoch, cycle,
        hasRemainingWork: cycle.hasRemainingWork, blocked: cycle.blocked, errors: cycle.errors }
    }
    if (selected.writer_transport_version === 2) {
      const cycle = await this.v2.runOnce(accountId, deviceId, options)
      return { transport_version: 2, cutover_epoch: selected.cutover_epoch, cycle,
        hasRemainingWork: cycle.hasRemainingWork, blocked: cycle.blocked, errors: cycle.errors }
    }
    if (!this.v3) throw new TypeError('metadata_mode_3_runtime_unavailable')
    const cycle = await this.v3.runOnce(accountId, deviceId, options)
    return { transport_version: 3, cutover_epoch: selected.cutover_epoch, cycle,
      hasRemainingWork: cycle.hasRemainingWork, blocked: cycle.blocked, errors: cycle.errors }
  }

  async uploadOnce(accountId: string): Promise<void> {
    const selected = await this.select()
    if (selected.writer_transport_version === 1) await this.v1Uploader.uploadOnce(accountId)
    else if (selected.writer_transport_version === 2 || selected.writer_transport_version === 3) await this.v2Uploader.uploadOnce(accountId)
    else throw new TypeError('unknown_transport_mode')
  }
}
