import type { RuntimeKeyContext, AuthoritativeKeyContextLease } from '@/auth/keyContext'
import { KeyNotProvisionedError } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { DurableNoteSyncInbox } from './noteSyncInbox'
import type { CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { NoteSyncInboxRemoteApplier, type NoteInboxApplyPageResult, type NoteInboxApplyPassResult } from './noteSyncInboxApply'
import {
  NoteSyncResolutionInboxApplier,
  type NoteResolutionInboxApplyPageResult,
  type NoteResolutionOrphanRetryPassResult,
} from './noteSyncResolutionInboxApply'
import { sealPendingNoteSyncIntents, type NoteSyncIntentRepository, type NoteSyncSealingPassResult } from './noteSyncIntent'
import { NoteSyncUploader } from './noteSyncUpload'
import { NoteSyncDeviceAckAdapter, type NoteSyncAckOnceResult } from './noteSyncDeviceAck'

export interface NoteSyncOrchestratorOptions {
  readonly sealLimit?: number
  readonly applyLimit?: number
  readonly maxPullPages?: number
  readonly maxApplyPasses?: number
}

export interface NoteSyncOrchestratorResult {
  readonly stages: readonly string[]
  readonly sealed: readonly NoteSyncSealingPassResult[]
  readonly uploaded: number
  readonly pulled: readonly CommitInboundPageResult[]
  readonly applied: readonly NoteInboxApplyPassResult[]
  readonly ack?: NoteSyncAckOnceResult
  readonly blocked: readonly string[]
  readonly errors: readonly { readonly stage: string, readonly code: string }[]
  readonly hasRemainingWork: boolean
}

export interface NoteSyncMixedInboxResult {
  readonly stages: readonly string[]
  readonly v1Pages: readonly NoteInboxApplyPageResult[]
  readonly resolutionPages: readonly NoteResolutionInboxApplyPageResult[]
  readonly orphanRetry?: NoteResolutionOrphanRetryPassResult
  readonly blocked: readonly string[]
  readonly errors: readonly { readonly stage: string, readonly code: string }[]
  readonly hasRemainingWork: boolean
}

export class NoteSyncMixedInboxUnavailableError extends Error {
  readonly name = 'NoteSyncMixedInboxUnavailableError'
}

const DEFAULTS: Required<NoteSyncOrchestratorOptions> = {
  sealLimit: 8,
  applyLimit: 8,
  maxPullPages: 4,
  maxApplyPasses: 4,
}

/**
 * Internal bounded composition of the established Notes sync primitives.
 * It owns neither cryptography, SQLite writes nor HTTP protocol logic.
 */
export class NoteSyncOrchestrator {
  private static readonly flights = new Map<string, Promise<NoteSyncOrchestratorResult>>()
  private static readonly mixedFlights = new Map<string, Promise<NoteSyncMixedInboxResult>>()
  private readonly orphanCursors = new Map<string, number>()

  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly keys: RuntimeKeyContext,
    private readonly intents: NoteSyncIntentRepository,
    private readonly uploader: NoteSyncUploader,
    private readonly inbox: DurableNoteSyncInbox,
    private readonly applier: NoteSyncInboxRemoteApplier,
    private readonly deviceAck: NoteSyncDeviceAckAdapter,
    private readonly resolutionApplier?: NoteSyncResolutionInboxApplier,
  ) {}

  async runOnce(localAccountId: string, deviceId: string, options: NoteSyncOrchestratorOptions = {}): Promise<NoteSyncOrchestratorResult> {
    const bounded = this.options(options)
    const context = this.auth.requireContext()
    const lease = this.keys.leaseForAccount(localAccountId)
    if (lease === null) throw new KeyNotProvisionedError()
    if (!lease.isCurrent() || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) {
      throw new StaleAuthContextError()
    }
    const flightKey = `${localAccountId}\u0000${deviceId}\u0000${context.authEpoch}\u0000${lease.keyContextId}\u0000${lease.keyEpoch}`
    const existing = NoteSyncOrchestrator.flights.get(flightKey)
    if (existing) return existing
    const flight = this.runBounded(localAccountId, deviceId, lease, bounded)
    NoteSyncOrchestrator.flights.set(flightKey, flight)
    try {
      return await flight
    } finally {
      if (NoteSyncOrchestrator.flights.get(flightKey) === flight) NoteSyncOrchestrator.flights.delete(flightKey)
    }
  }

  /**
   * @internal Dormant apply-only composition for D4A2 validation. Production
   * runtime deliberately keeps using runOnce() until v2 pull/ACK cutover.
   */
  async runMixedInboxOnce(
    localAccountId: string,
    deviceId: string,
    options: Pick<NoteSyncOrchestratorOptions, 'applyLimit' | 'maxApplyPasses'> = {},
  ): Promise<NoteSyncMixedInboxResult> {
    if (this.resolutionApplier === undefined) throw new NoteSyncMixedInboxUnavailableError('Mixed inbox processing is not composed.')
    const bounded = this.options(options)
    const context = this.auth.requireContext()
    const lease = this.keys.leaseForAccount(localAccountId)
    if (lease === null) throw new KeyNotProvisionedError()
    if (!lease.isCurrent() || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) {
      throw new StaleAuthContextError()
    }
    const flightKey = `${localAccountId}\u0000${deviceId}\u0000${context.authEpoch}\u0000${lease.keyContextId}\u0000${lease.keyEpoch}`
    const existing = NoteSyncOrchestrator.mixedFlights.get(flightKey)
    if (existing) return existing
    const flight = this.runMixedInboxBounded(localAccountId, deviceId, lease, bounded, flightKey)
    NoteSyncOrchestrator.mixedFlights.set(flightKey, flight)
    try {
      return await flight
    } finally {
      if (NoteSyncOrchestrator.mixedFlights.get(flightKey) === flight) NoteSyncOrchestrator.mixedFlights.delete(flightKey)
    }
  }

  private async runMixedInboxBounded(
    localAccountId: string,
    deviceId: string,
    lease: AuthoritativeKeyContextLease,
    options: Required<NoteSyncOrchestratorOptions>,
    lifecycleKey: string,
  ): Promise<NoteSyncMixedInboxResult> {
    const resolutionApplier = this.resolutionApplier!
    const stages: string[] = []
    const v1Pages: NoteInboxApplyPageResult[] = []
    const resolutionPages: NoteResolutionInboxApplyPageResult[] = []
    const blocked: string[] = []
    const errors: Array<{ stage: string, code: string }> = []
    let v1Cursor = 0
    let resolutionCursor = 0
    let v1Active = true
    let resolutionActive = true
    let hasRemainingWork = false

    for (let pass = 0; pass < options.maxApplyPasses && (v1Active || resolutionActive); pass += 1) {
      if (v1Active) {
        this.assertCurrent(lease)
        stages.push('apply_v1')
        try {
          const page = await this.applier.applyPage(localAccountId, deviceId, options.applyLimit, v1Cursor)
          v1Pages.push(page)
          v1Cursor = page.lastServerSequence
          this.collectBlocked(page.results, blocked)
          if (page.errorCount > 0) hasRemainingWork = true
          v1Active = page.listed === options.applyLimit
        } catch (error) {
          errors.push(this.error('apply_v1', error))
          hasRemainingWork = true
          v1Active = false
        }
      }

      if (resolutionActive) {
        this.assertCurrent(lease)
        stages.push('apply_resolution')
        try {
          const page = await resolutionApplier.applyReceivedPage(
            localAccountId, deviceId, options.applyLimit, resolutionCursor,
          )
          resolutionPages.push(page)
          resolutionCursor = page.lastServerSequence
          this.collectBlocked(page.results, blocked)
          if (page.errorCount > 0) hasRemainingWork = true
          resolutionActive = page.listed === options.applyLimit
        } catch (error) {
          errors.push(this.error('apply_resolution', error))
          hasRemainingWork = true
          resolutionActive = false
        }
      }
    }
    if (v1Active || resolutionActive) hasRemainingWork = true

    let orphanRetry: NoteResolutionOrphanRetryPassResult | undefined
    this.assertCurrent(lease)
    stages.push('retry_orphans')
    try {
      const initialCursor = this.orphanCursors.get(lifecycleKey) ?? 0
      orphanRetry = await resolutionApplier.retryOrphansFrom(
        localAccountId, deviceId, options.applyLimit, initialCursor,
      )
      this.collectBlocked(orphanRetry.results, blocked)
      if (orphanRetry.errorCount > 0 || !orphanRetry.reachedEnd) hasRemainingWork = true
      this.orphanCursors.set(lifecycleKey, orphanRetry.reachedEnd ? 0 : orphanRetry.lastServerSequence)
    } catch (error) {
      errors.push(this.error('retry_orphans', error))
      hasRemainingWork = true
    }

    if (blocked.length > 0 || errors.length > 0) hasRemainingWork = true
    return {
      stages,
      v1Pages,
      resolutionPages,
      orphanRetry,
      blocked: [...new Set(blocked)],
      errors,
      hasRemainingWork,
    }
  }

  private async runBounded(localAccountId: string, deviceId: string, lease: AuthoritativeKeyContextLease, options: Required<NoteSyncOrchestratorOptions>): Promise<NoteSyncOrchestratorResult> {
    const stages: string[] = []
    const sealed: NoteSyncSealingPassResult[] = []
    const pulled: CommitInboundPageResult[] = []
    const applied: NoteInboxApplyPassResult[] = []
    const blocked: string[] = []
    const errors: Array<{ stage: string, code: string }> = []
    let uploaded = 0
    let ack: NoteSyncAckOnceResult | undefined
    let hasRemainingWork = false

    try {
      this.assertCurrent(lease)
      stages.push('register_device')
      await this.deviceAck.registerOnce(localAccountId, deviceId)
    } catch (error) {
      errors.push(this.error('register_device', error))
      return { stages, sealed, uploaded, pulled, applied, blocked, errors, hasRemainingWork: true }
    }

    this.assertCurrent(lease)
    stages.push('seal')
    const seal = await sealPendingNoteSyncIntents(this.intents, this.keys, { limit: options.sealLimit })
    sealed.push(seal)
    hasRemainingWork ||= seal.listed >= options.sealLimit || seal.results.some(item => item.status.includes('failure') || item.status === 'blocked_skipped')

    this.assertCurrent(lease)
    stages.push('upload')
    try {
      uploaded += (await this.uploader.uploadOnce(localAccountId)).uploaded
    } catch (error) {
      errors.push(this.error('upload', error))
      hasRemainingWork = true
    }

    for (let page = 0; page < options.maxPullPages; page += 1) {
      this.assertCurrent(lease)
      stages.push('pull')
      try {
        const result = await this.inbox.pullOnce(localAccountId, deviceId)
        pulled.push(result)
        if (!result.has_more) break
        hasRemainingWork = true
        if (result.committed_cursor === 0 || (pulled.length > 1 && result.committed_cursor === pulled[pulled.length - 2]!.committed_cursor)) break
      } catch (error) {
        errors.push(this.error('pull', error))
        hasRemainingWork = true
        break
      }
    }
    if (pulled.length === options.maxPullPages && pulled.at(-1)?.has_more) hasRemainingWork = true

    let applyFailed = false
    for (let pass = 0; pass < options.maxApplyPasses; pass += 1) {
      this.assertCurrent(lease)
      stages.push('apply')
      try {
        const result = await this.applier.applyOnce(localAccountId, deviceId, options.applyLimit)
        applied.push(result)
        for (const item of result.results) {
          if (item.status === 'orphan' || item.status === 'conflict' || item.status === 'rejected' || item.status === 'error') blocked.push(item.status)
        }
        if (result.listed === 0) break
        if (result.results.some(item => item.status === 'error')) { hasRemainingWork = true; break }
        if (result.listed < options.applyLimit) break
        hasRemainingWork = true
      } catch (error) {
        errors.push(this.error('apply', error))
        hasRemainingWork = true
        applyFailed = true
        break
      }
    }
    if (applied.length === options.maxApplyPasses && applied.at(-1)?.listed === options.applyLimit) hasRemainingWork = true

    if (!applyFailed) {
      this.assertCurrent(lease)
      stages.push('ack')
      try {
        ack = await this.deviceAck.ackOnce(localAccountId, deviceId)
        if (ack.status !== 'no_progress') hasRemainingWork ||= ack.status === 'stale'
      } catch (error) {
        errors.push(this.error('ack', error))
        hasRemainingWork = true
      }
    }
    return { stages, sealed, uploaded, pulled, applied, ack, blocked: [...new Set(blocked)], errors, hasRemainingWork }
  }

  private assertCurrent(lease: AuthoritativeKeyContextLease): void {
    if (!lease.isCurrent() || !this.auth.isCurrent({ userId: lease.canonicalUserId, username: '', authEpoch: lease.authEpoch })) {
      throw new StaleAuthContextError()
    }
  }

  private collectBlocked(results: readonly { readonly status: string }[], blocked: string[]): void {
    for (const item of results) {
      if (item.status === 'orphan' || item.status === 'self_echo_pending' || item.status === 'conflict'
        || item.status === 'rejected' || item.status === 'error') blocked.push(item.status)
    }
  }

  private options(options: NoteSyncOrchestratorOptions): Required<NoteSyncOrchestratorOptions> {
    const bounded = { ...DEFAULTS, ...options }
    if (!Number.isSafeInteger(bounded.sealLimit) || bounded.sealLimit < 1 || bounded.sealLimit > 32
      || !Number.isSafeInteger(bounded.applyLimit) || bounded.applyLimit < 1 || bounded.applyLimit > 32
      || !Number.isSafeInteger(bounded.maxPullPages) || bounded.maxPullPages < 1 || bounded.maxPullPages > 8
      || !Number.isSafeInteger(bounded.maxApplyPasses) || bounded.maxApplyPasses < 1 || bounded.maxApplyPasses > 8) {
      throw new RangeError('Invalid bounded Note sync orchestration options.')
    }
    return bounded
  }

  private error(stage: string, error: unknown): { stage: string, code: string } {
    return { stage, code: error instanceof Error ? error.name : 'unknown_error' }
  }
}
