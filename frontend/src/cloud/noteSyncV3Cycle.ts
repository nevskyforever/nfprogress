import type { ContentNoteReader } from './contentNoteReader'
import { diagnostics } from '@/diagnostics/service'
import type { AccountObjectReader } from './accountObjectReader'
import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { NoteSyncDeviceAckAdapter } from './noteSyncDeviceAck'
import { sealPendingNoteSyncIntents, type NoteSyncIntentRepository } from './noteSyncIntent'
import type { NoteSyncOrchestratorOptions, NoteSyncMixedInboxResult } from './noteSyncOrchestrator'
import { NoteSyncOrchestrator } from './noteSyncOrchestrator'
import { NoteSyncResolutionUploader } from './noteSyncResolutionUpload'
import { NoteSyncV2Uploader } from './noteSyncV2Upload'
import { ProjectMetadataMigrationRuntime, type MetadataApplyResult, type MetadataAckResult } from './projectMetadataMigrationRuntime'
import type { StageStructuralRuntime } from './stageStructuralRuntime'
import type { CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'

export interface NoteSyncV3CycleResult {
  readonly stages: readonly string[]
  readonly noteUploaded: number
  readonly resolutionUploaded: number
  readonly metadataUploaded: number
  readonly structuralApply?: MetadataApplyResult
  readonly pulled: readonly CommitInboundPageResult[]
  readonly noteApply?: NoteSyncMixedInboxResult
  readonly metadataApply?: MetadataApplyResult
  readonly ack?: MetadataAckResult
  readonly blocked: readonly string[]
  readonly errors: readonly { stage: string; code: string }[]
  readonly hasRemainingWork: boolean
}

/** Mode-3 cycle retains the Note-v2 writer and C17 mixed applier. */
export class NoteSyncV3Cycle {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly identity: CloudIdentityRepository,
    private readonly keys: RuntimeKeyContext,
    private readonly device: NoteSyncDeviceAckAdapter,
    private readonly intents: NoteSyncIntentRepository,
    private readonly noteUploader: NoteSyncV2Uploader,
    private readonly resolutionUploader: NoteSyncResolutionUploader,
    private readonly noteApplier: NoteSyncOrchestrator,
    private readonly metadata: ProjectMetadataMigrationRuntime,
    private readonly structural?: StageStructuralRuntime,
    private readonly accountReader?: AccountObjectReader & Partial<Pick<import("./accountCatalogRuntime").AccountCatalogRuntime,"sealCatalog"|"uploadCatalog">>,
    private readonly contentNotes?: ContentNoteReader,
  ) {}

  async runOnce(accountId: string, deviceId: string, options: NoteSyncOrchestratorOptions = {}): Promise<NoteSyncV3CycleResult> {
    const limits = { sealLimit: 8, applyLimit: 8, maxPullPages: 4, maxApplyPasses: 4, ...options }
    if (!Number.isSafeInteger(limits.sealLimit) || limits.sealLimit < 1 || limits.sealLimit > 32
      || !Number.isSafeInteger(limits.applyLimit) || limits.applyLimit < 1 || limits.applyLimit > 32
      || !Number.isSafeInteger(limits.maxPullPages) || limits.maxPullPages < 1 || limits.maxPullPages > 8
      || !Number.isSafeInteger(limits.maxApplyPasses) || limits.maxApplyPasses < 1 || limits.maxApplyPasses > 8) throw new RangeError('invalid_v3_cycle_limits')
    const context = this.auth.requireContext()
    const lease = this.keys.leaseForAccount(accountId)
    if (!lease) throw new KeyNotProvisionedError()
    if (!lease.isCurrent() || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    const stages: string[] = [], pulled: CommitInboundPageResult[] = [], blocked: string[] = []
    const errors: Array<{ stage: string; code: string }> = []
    let noteUploaded = 0, resolutionUploaded = 0, metadataUploaded = 0, hasRemainingWork = false
    let structuralApply: MetadataApplyResult | undefined
    let abort = false
    let noteApply: NoteSyncMixedInboxResult | undefined, metadataApply: MetadataApplyResult | undefined, ack: MetadataAckResult | undefined
    const result = (): NoteSyncV3CycleResult => ({ stages, noteUploaded, resolutionUploaded, metadataUploaded,
      pulled, noteApply, metadataApply, structuralApply, ack, blocked, errors, hasRemainingWork })
    const stage = async (name: string, action: () => Promise<void>): Promise<boolean> => {
      stages.push(name)
      try { await action(); return true }
      catch (error) {
        errors.push({ stage: name, code: error instanceof Error && 'code' in error && typeof error.code === 'string' ? error.code : error instanceof Error ? error.name : 'unknown_error' })
        hasRemainingWork = true
        abort ||= error instanceof StaleAuthContextError
          || (error instanceof Error && 'code' in error && error.code === 'sync_transport_mode_incompatible')
        return false
      }
    }
    const mode = async (): Promise<void> => {
      if (!this.auth.isCurrent(context) || !lease.isCurrent()) throw new StaleAuthContextError()
      const response = await this.auth.authorized(token => encryptedSyncV2Api.capabilities(token))
      if (!this.auth.isCurrent(context) || response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch
        || parseV2Capabilities(response.value).writer_transport_version !== 3) throw new StaleAuthContextError()
    }
    if (!await stage('preflight', async () => {
      const binding = await this.bindings.ensureForCurrentUser(accountId)
      const identity = await this.identity.read(context.userId)
      if (!identity || identity.local_account_id !== accountId || identity.device_id !== deviceId
        || binding.context.userId !== context.userId || binding.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
      await mode()
    })) return result()
    if (!await stage('register_device', async () => { await this.device.registerOnce(accountId, deviceId) })) return result()
    if (!await stage('seal_notes', async () => {
      await mode()
      const pass = await sealPendingNoteSyncIntents(this.intents, this.keys, { limit: limits.sealLimit })
      hasRemainingWork ||= pass.listed === limits.sealLimit || pass.results.some(item => item.status.includes('failure') || item.status === 'blocked_skipped')
    })) return result()
    await stage('seal_metadata', async () => { await mode(); hasRemainingWork ||= (await this.metadata.sealOnce(accountId, deviceId)) === 8 })
    if (this.structural) await stage('seal_structure', async () => { await mode(); const count = await this.structural!.sealOnce(accountId, deviceId); hasRemainingWork ||= count === 8 })
    if(this.accountReader?.sealCatalog) await stage('seal_catalog',async()=>{await mode();hasRemainingWork ||= await this.accountReader!.sealCatalog!(accountId,deviceId)===8})
    if (abort) return result()
    // A lost upload response must not prevent the self echo from being pulled.
    await stage('upload_notes', async () => { await mode(); noteUploaded = (await this.noteUploader.uploadOnce(accountId)).uploaded })
    if (abort) return result()
    await stage('upload_resolutions', async () => { await mode(); resolutionUploaded = (await this.resolutionUploader.uploadOnce(accountId)).uploaded })
    if (abort) return result()
    await stage('upload_metadata', async () => { await mode(); metadataUploaded = await this.metadata.uploadOnce(accountId, deviceId) })
    if (abort) return result()
    if (this.structural) await stage('upload_structure', async () => { await mode(); await this.structural!.uploadOnce(accountId, deviceId) })
    if (abort) return result()
    if(this.accountReader?.uploadCatalog) await stage('upload_catalog',async()=>{await mode();await this.accountReader!.uploadCatalog!(accountId,deviceId)})
    if(abort)return result()
    for (let page = 0; page < limits.maxPullPages; page += 1) {
      if (!await stage('pull_v3', async () => { await mode(); pulled.push(await this.metadata.pullOnce(accountId, deviceId)) })) return result()
      if (!pulled.at(-1)!.has_more) break
      if (pulled.length > 1 && pulled.at(-1)!.committed_cursor <= pulled[pulled.length - 2]!.committed_cursor) { hasRemainingWork = true; break }
    }
    if (pulled.length === limits.maxPullPages && pulled.at(-1)?.has_more) hasRemainingWork = true
    if (!await stage('apply_notes', async () => {
      await mode()
      noteApply = await this.noteApplier.runMixedInboxOnce(accountId, deviceId, { applyLimit: limits.applyLimit, maxApplyPasses: limits.maxApplyPasses })
      blocked.push(...noteApply.blocked)
      hasRemainingWork ||= noteApply.hasRemainingWork
    })) return result()
    if (!await stage('apply_metadata', async () => {
      await mode()
      metadataApply = await this.metadata.applyOnce(accountId, deviceId, limits.maxApplyPasses)
      blocked.push(...metadataApply.blocked)
      hasRemainingWork ||= metadataApply.blocked.length > 0 || metadataApply.orphans > 0 || metadataApply.listed === 8 * limits.maxApplyPasses
    })) return result()
    if (this.structural && !await stage('apply_structure', async () => {
      await mode(); structuralApply = await this.structural!.applyOnce(accountId, deviceId, limits.maxApplyPasses)
      blocked.push(...structuralApply.blocked)
      hasRemainingWork ||= structuralApply.blocked.length > 0 || structuralApply.orphans > 0 || structuralApply.listed === 8 * limits.maxApplyPasses
      // Frozen migration order can become ready during apply; leave a visible continuation.
      hasRemainingWork ||= structuralApply.applied > 0
    })) return result()
    if (this.contentNotes && !await stage('apply_content_notes', async()=>{await mode();const pass=await this.contentNotes!.readOnce(accountId,deviceId,limits.applyLimit,limits.maxApplyPasses);blocked.push(...pass.blocked);hasRemainingWork ||= pass.hasRemainingWork})) return result()
    if (this.accountReader && !await stage('apply_account', async () => {
      const account = await this.accountReader!.readOnce(accountId, deviceId, limits.applyLimit, limits.maxApplyPasses)
      blocked.push(...account.blocked)
      hasRemainingWork ||= account.hasRemainingWork || account.blocked.length > 0
    })) return result()
    await stage('ack_v3', async () => { await mode(); ack = await this.metadata.ackOnce(accountId, deviceId); hasRemainingWork ||= ack.status === 'stale'; diagnostics.record('sync','sync_cycle','ack_result',undefined,{status:ack.status,pending:blocked.length}) })
    return result()
  }
}
