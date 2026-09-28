import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import { ApiError } from '@/api/client'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, type AuthoritativeKeyContextLease, type RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { NoteSyncOrchestrator, type NoteSyncMixedInboxResult, type NoteSyncOrchestratorOptions } from './noteSyncOrchestrator'
import { sealPendingNoteSyncIntents, type NoteSyncIntentRepository, type NoteSyncSealingPassResult } from './noteSyncIntent'
import { NoteSyncDeviceAckAdapter, type NoteSyncAckOnceResult } from './noteSyncDeviceAck'
import { NoteSyncResolutionUploader } from './noteSyncResolutionUpload'
import { NoteSyncV2Uploader } from './noteSyncV2Upload'
import { DurableNoteSyncV2Inbox, NoteSyncV2AckAdapter, NoteSyncV2TransportError } from './noteSyncV2Transport'

export interface NoteSyncV2CycleResult {
  readonly stages: readonly string[]
  readonly sealed: readonly NoteSyncSealingPassResult[]
  readonly ordinaryUploaded: number
  readonly resolutionUploaded: number
  readonly pulled: readonly CommitInboundPageResult[]
  readonly mixedApply?: NoteSyncMixedInboxResult
  readonly ack?: NoteSyncAckOnceResult
  readonly blocked: readonly string[]
  readonly errors: readonly { readonly stage: string, readonly code: string }[]
  readonly hasRemainingWork: boolean
}

const DEFAULTS: Required<NoteSyncOrchestratorOptions> = { sealLimit: 8, applyLimit: 8, maxPullPages: 4, maxApplyPasses: 4 }

/** Dormant mode-2 composition. No production runtime or bootstrap constructs this class. */
export class NoteSyncV2Cycle {
  private static readonly flights = new Map<string, Promise<NoteSyncV2CycleResult>>()

  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly identity: CloudIdentityRepository,
    private readonly keys: RuntimeKeyContext,
    private readonly device: NoteSyncDeviceAckAdapter,
    private readonly intents: NoteSyncIntentRepository,
    private readonly ordinary: NoteSyncV2Uploader,
    private readonly resolution: NoteSyncResolutionUploader,
    private readonly inbox: DurableNoteSyncV2Inbox,
    private readonly mixed: NoteSyncOrchestrator,
    private readonly ackAdapter: NoteSyncV2AckAdapter,
    private readonly capabilities: Pick<typeof encryptedSyncV2Api, 'capabilities'> = encryptedSyncV2Api,
  ) {}

  async runOnce(accountId: string, deviceId: string, options: NoteSyncOrchestratorOptions = {}): Promise<NoteSyncV2CycleResult> {
    const limits = { ...DEFAULTS, ...options }
    if (!Number.isSafeInteger(limits.sealLimit) || limits.sealLimit < 1 || limits.sealLimit > 32
      || !Number.isSafeInteger(limits.applyLimit) || limits.applyLimit < 1 || limits.applyLimit > 32
      || !Number.isSafeInteger(limits.maxPullPages) || limits.maxPullPages < 1 || limits.maxPullPages > 8
      || !Number.isSafeInteger(limits.maxApplyPasses) || limits.maxApplyPasses < 1 || limits.maxApplyPasses > 8) {
      throw new RangeError('Invalid bounded Note sync orchestration options.')
    }
    const context = this.auth.requireContext()
    const lease = this.keys.leaseForAccount(accountId)
    if (lease === null) throw new KeyNotProvisionedError()
    this.assertCurrent(context, lease, accountId)
    const flightKey = `${accountId}\0${deviceId}\0${context.userId}\0${context.authEpoch}\0${lease.keyContextId}\0${lease.keyEpoch}`
    const existing = NoteSyncV2Cycle.flights.get(flightKey)
    if (existing) return existing
    const flight = this.runBounded(accountId, deviceId, context, lease, limits)
    NoteSyncV2Cycle.flights.set(flightKey, flight)
    try { return await flight } finally {
      if (NoteSyncV2Cycle.flights.get(flightKey) === flight) NoteSyncV2Cycle.flights.delete(flightKey)
    }
  }

  private assertCurrent(context: AuthContextSnapshot, lease: AuthoritativeKeyContextLease, accountId: string): void {
    if (!this.auth.isCurrent(context) || !lease.isCurrent() || lease.localAccountId !== accountId
      || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
  }

  private async requireMode(context: AuthContextSnapshot, lease: AuthoritativeKeyContextLease, accountId: string): Promise<void> {
    this.assertCurrent(context, lease, accountId)
    try {
      const response = await this.auth.authorized(token => this.capabilities.capabilities(token))
      this.assertCurrent(context, lease, accountId)
      if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
      if (parseV2Capabilities(response.value).writer_transport_version !== 2) throw new NoteSyncV2TransportError('mode_incompatible')
    } catch (error) {
      if (error instanceof ApiError && error.code === 'sync_transport_mode_incompatible') throw new NoteSyncV2TransportError('mode_incompatible')
      throw error
    }
  }

  private async runBounded(accountId: string, deviceId: string, context: AuthContextSnapshot,
    lease: AuthoritativeKeyContextLease, options: Required<NoteSyncOrchestratorOptions>): Promise<NoteSyncV2CycleResult> {
    const stages: string[] = []
    const sealed: NoteSyncSealingPassResult[] = []
    const pulled: CommitInboundPageResult[] = []
    const errors: Array<{ stage: string, code: string }> = []
    let ordinaryUploaded = 0
    let resolutionUploaded = 0
    let mixedApply: NoteSyncMixedInboxResult | undefined
    let ack: NoteSyncAckOnceResult | undefined
    let hasRemainingWork = false
    const result = (): NoteSyncV2CycleResult => ({ stages, sealed, ordinaryUploaded, resolutionUploaded, pulled,
      mixedApply, ack, blocked: [...new Set([
        ...sealed.flatMap(pass => pass.results.filter(item => item.status === 'blocked_skipped').map(item => item.status)),
        ...(mixedApply?.blocked ?? []),
      ])], errors, hasRemainingWork })
    const fail = (stage: string, error: unknown): void => {
      errors.push({ stage, code: error instanceof Error ? ('code' in error && typeof error.code === 'string' ? error.code : error.name) : 'unknown_error' })
      hasRemainingWork = true
    }
    const stage = async (name: string, action: () => Promise<void>): Promise<boolean> => {
      stages.push(name)
      try { await action(); return true } catch (error) { fail(name, error); return false }
    }
    if (!await stage('preflight', async () => {
      const binding = await this.bindings.ensureForCurrentUser(accountId)
      this.assertCurrent(context, lease, accountId)
      if (binding.context.userId !== context.userId || binding.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
      const durable = await this.identity.read(context.userId)
      this.assertCurrent(context, lease, accountId)
      if (!durable || durable.local_account_id !== accountId || durable.device_id !== deviceId) throw new StaleAuthContextError()
      await this.requireMode(context, lease, accountId)
    })) return result()
    if (!await stage('register_device', async () => {
      this.assertCurrent(context, lease, accountId)
      await this.device.registerOnce(accountId, deviceId)
    })) return result()
    if (!await stage('seal', async () => {
      await this.requireMode(context, lease, accountId)
      const pass = await sealPendingNoteSyncIntents(this.intents, this.keys, { limit: options.sealLimit })
      sealed.push(pass)
      hasRemainingWork ||= pass.listed === options.sealLimit || pass.results.some(item => item.status.includes('failure') || item.status === 'blocked_skipped' || item.status === 'commit_failed' || item.status === 'unclassified_error')
    })) return result()
    // Independent durable queues are both attempted on ordinary transport errors.
    // Mode/stale failures stop immediately, with all earlier receipts intact.
    let modeFailed = false
    for (const [name, upload] of [
      ['upload_ordinary', () => this.ordinary.uploadOnce(accountId)],
      ['upload_resolution', () => this.resolution.uploadOnce(accountId)],
    ] as const) {
      stages.push(name)
      try {
        await this.requireMode(context, lease, accountId)
        const value = await upload()
        if (value.deviceId !== null && value.deviceId !== deviceId) throw new StaleAuthContextError()
        if (name === 'upload_ordinary') ordinaryUploaded = value.uploaded
        else resolutionUploaded = value.uploaded
        this.assertCurrent(context, lease, accountId)
      } catch (error) {
        fail(name, error)
        if (error instanceof StaleAuthContextError || error instanceof NoteSyncV2TransportError && error.code === 'mode_incompatible'
          || error instanceof Error && 'code' in error && error.code === 'mode_incompatible') { modeFailed = true; break }
      }
    }
    if (modeFailed || errors.length) return result()
    for (let page = 0; page < options.maxPullPages; page += 1) {
      if (!await stage('pull', async () => {
        await this.requireMode(context, lease, accountId)
        const value = await this.inbox.pullOnce(accountId, deviceId)
        pulled.push(value)
      })) return result()
      const last = pulled.at(-1)!
      if (!last.has_more) break
      if (last.committed_cursor === 0 || pulled.length > 1 && last.committed_cursor <= pulled[pulled.length - 2]!.committed_cursor) {
        hasRemainingWork = true
        break
      }
    }
    if (pulled.length === options.maxPullPages && pulled.at(-1)?.has_more) hasRemainingWork = true
    if (!await stage('mixed_apply', async () => {
      await this.requireMode(context, lease, accountId)
      mixedApply = await this.mixed.runMixedInboxOnce(accountId, deviceId,
        { applyLimit: options.applyLimit, maxApplyPasses: options.maxApplyPasses })
      hasRemainingWork ||= mixedApply.hasRemainingWork
    })) return result()
    await stage('ack_v2', async () => {
      await this.requireMode(context, lease, accountId)
      ack = await this.ackAdapter.ackOnce(accountId, deviceId)
      hasRemainingWork ||= ack.status === 'stale'
    })
    return result()
  }
}
