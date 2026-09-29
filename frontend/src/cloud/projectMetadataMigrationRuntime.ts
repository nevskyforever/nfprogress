import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api, type V3MetadataPushItem } from '@/api/encryptedSyncV3'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { SQLiteNoteSyncAckRepository, type NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { SQLiteNoteSyncInboxRepository, type NoteSyncInboxRepository, type CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { SQLiteProjectMetadataMigrationRepository, type MetadataScope, type MetadataMigrationStatus, type ProjectMetadataMigrationRepository } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import { encodeProjectMetadataEvent, openProjectMetadataEvent, sealProjectMetadataEvent, validateProjectMetadataEvent } from './projectMetadataCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'

export interface MetadataApplyResult { applied: number; conflicts: number; orphans: number; blocked: readonly string[]; listed: number }
export interface MetadataAckResult { status: 'no_progress' | 'advanced' | 'already_acknowledged' | 'already_advanced' | 'stale'; cursor: number }
const now = (): string => canonicalizeSyncTimestamp(new Date().toISOString())

/** Internal migration boundary. Capture and publication require explicit calls. */
export class ProjectMetadataMigrationRuntime {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly identity: CloudIdentityRepository,
    private readonly keys: RuntimeKeyContext,
    private readonly native: ProjectMetadataMigrationRepository = new SQLiteProjectMetadataMigrationRepository(),
    private readonly inbox: NoteSyncInboxRepository = new SQLiteNoteSyncInboxRepository(),
    private readonly ack: NoteSyncAckRepository = new SQLiteNoteSyncAckRepository(),
    private readonly api: typeof encryptedSyncV3Api = encryptedSyncV3Api,
  ) {}

  private async scope(accountId: string, deviceId: string): Promise<{ scope: MetadataScope; context: AuthContextSnapshot }> {
    const binding = await this.bindings.ensureForCurrentUser(accountId)
    const identity = await this.identity.read(binding.context.userId)
    if (!identity || identity.local_account_id !== accountId || identity.device_id !== deviceId || !this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const lease = this.keys.leaseForAccount(accountId)
    if (!lease) throw new KeyNotProvisionedError()
    if (!lease.isCurrent() || lease.canonicalUserId !== binding.context.userId || lease.authEpoch !== binding.context.authEpoch) throw new StaleAuthContextError()
    return { scope: { account_id: accountId, canonical_user_id: binding.context.userId, device_id: deviceId }, context: binding.context }
  }

  private assertCurrent(context: AuthContextSnapshot): void {
    if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
  }

  async mode(accountId: string, deviceId: string): Promise<1 | 2 | 3> {
    const { context } = await this.scope(accountId, deviceId)
    const response = await this.auth.authorized(token => encryptedSyncV2Api.capabilities(token))
    this.assertCurrent(context)
    if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    return parseV2Capabilities(response.value).writer_transport_version
  }

  private async requireMode3(accountId: string, deviceId: string): Promise<void> {
    if (await this.mode(accountId, deviceId) !== 3) throw new TypeError('metadata_mode_3_required')
  }

  async declareReaderReady(accountId: string, deviceId: string): Promise<void> {
    const { context } = await this.scope(accountId, deviceId)
    const mode = await this.mode(accountId, deviceId)
    if (mode !== 2 && mode !== 3) throw new TypeError('metadata_mode_2_required')
    const response = await this.auth.authorized(token => this.api.readerReady(token, deviceId))
    this.assertCurrent(context)
    if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
  }

  async cutover(accountId: string, deviceId: string): Promise<void> {
    const { context } = await this.scope(accountId, deviceId)
    const capabilities = await this.auth.authorized(token => encryptedSyncV2Api.capabilities(token))
    this.assertCurrent(context)
    if (capabilities.context.userId !== context.userId || capabilities.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    const current = parseV2Capabilities(capabilities.value)
    if (current.writer_transport_version === 3) return
    if (current.writer_transport_version !== 2) throw new TypeError('metadata_mode_2_required')
    const response = await this.auth.authorized(token => this.api.cutover(token, current.cutover_epoch))
    this.assertCurrent(context)
    if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
  }

  async status(accountId: string, deviceId: string, projectId: string): Promise<MetadataMigrationStatus> {
    const { scope } = await this.scope(accountId, deviceId)
    return this.native.status(scope, projectId)
  }

  async begin(accountId: string, deviceId: string, projectId: string): Promise<MetadataMigrationStatus> {
    await this.requireMode3(accountId, deviceId)
    const { scope } = await this.scope(accountId, deviceId)
    const prior = await this.native.status(scope, projectId)
    if (prior.event_id || prior.genesis_tips > 0) return prior
    const candidateId = prior.candidate_id ?? await this.native.capture(scope, projectId, now())
    const candidate = await this.native.status(scope, projectId)
    if (candidate.candidate_id !== candidateId) throw new TypeError('metadata_candidate_changed')
    if (candidate.blockers.length || candidate.state !== 'legacy_candidate_present') return candidate
    await this.native.prepare(scope, candidateId, now())
    return this.native.status(scope, projectId)
  }

  async sealOnce(accountId: string, deviceId: string): Promise<number> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const events = await this.native.unsealed(scope)
    let sealed = 0
    for (const event of events) {
      validateProjectMetadataEvent(event)
      if (event.header.account_id !== scope.canonical_user_id || event.header.device_id !== deviceId) throw new TypeError('metadata_genesis_scope')
      const lease = this.keys.leaseForAccount(accountId)
      if (!lease) throw new KeyNotProvisionedError()
      await lease.use(async amk => {
        const envelope = await sealProjectMetadataEvent(amk, event)
        this.assertCurrent(context)
        await this.native.commitSealed(scope, event.header.event_id, envelope.nonce, envelope.ciphertext)
      })
      sealed += 1
    }
    return sealed
  }

  async uploadOnce(accountId: string, deviceId: string): Promise<number> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const items = await this.native.sealed(scope)
    let uploaded = 0
    for (const item of items) {
      if (item.revision !== 1 || item.nonce.length !== 24) throw new TypeError('metadata_sealed_event_invalid')
      const event: V3MetadataPushItem = {
        event: { event_id: item.event_id, project_id: item.project_id, entity_id: item.project_id,
          entity_type: 'project_metadata', operation: 'upsert', revision: item.revision, updated_at: item.updated_at, deleted_at: null },
        object: { crypto_version: 1, aad_version: 1, nonce: Uint8Array.from(item.nonce), ciphertext: Uint8Array.from(item.ciphertext) },
      }
      const pushed = await this.auth.authorized(token => this.api.pushMetadata(token, deviceId, [event]))
      this.assertCurrent(context)
      if (pushed.context.userId !== context.userId || pushed.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
      const receipt = pushed.value.results[0]
      if (!receipt || receipt.event_id !== item.event_id) throw new TypeError('metadata_receipt_mismatch')
      await this.native.commitReceipt(scope, item.event_id, receipt.server_sequence, receipt.duplicate, now())
      uploaded += 1
    }
    return uploaded
  }

  async pullOnce(accountId: string, deviceId: string): Promise<CommitInboundPageResult> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const state = await this.inbox.readPullState(accountId, deviceId, context.userId)
    const pulled = await this.auth.authorized(token => this.api.pull(token, deviceId, state.pull_cursor))
    this.assertCurrent(context)
    if (pulled.context.userId !== context.userId || pulled.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    return this.native.commitV3Page(scope, state.pull_cursor, pulled.value)
  }

  async applyOnce(accountId: string, deviceId: string, maxPages = 4): Promise<MetadataApplyResult> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    let applied = 0, conflicts = 0, orphans = 0, listed = 0, after = 0
    const blocked: string[] = []
    for (let page = 0; page < maxPages; page += 1) {
      const items = await this.native.received(scope, 8, after)
      if (!items.length) break
      listed += items.length
      for (const item of items) {
        after = item.server_sequence
        try {
          if (item.crypto_version !== 1 || item.aad_version !== 1 || item.entity_id !== item.project_id) throw new TypeError('metadata_inbox_context')
          const lease = this.keys.leaseForAccount(accountId)
          if (!lease) throw new KeyNotProvisionedError()
          const outcome = await lease.use(async amk => {
            const nonce = Uint8Array.from(item.nonce), ciphertext = Uint8Array.from(item.ciphertext)
            const event = await openProjectMetadataEvent(amk, { account_id: context.userId, project_id: item.project_id,
              entity_id: item.entity_id, event_id: item.event_id }, { crypto_version: 1, aad_version: 1, nonce, ciphertext })
            const h = event.header
            if (h.device_id !== item.source_device_id || h.revision !== item.revision || h.updated_at !== item.updated_at
              || event.deleted_at !== item.deleted_at || (h.operation === 'delete' ? 'delete' : 'upsert') !== item.operation) throw new TypeError('metadata_inbox_mismatch')
            const plaintext = encodeProjectMetadataEvent(event)
            try { this.assertCurrent(context); return await this.native.apply(scope, item.project_id, plaintext, nonce, ciphertext, now()) }
            finally { plaintext.fill(0) }
          })
          if (outcome === 'applied') applied += 1
          else if (outcome === 'conflict_preserved') conflicts += 1
          else orphans += 1
        } catch (error) {
          if (error instanceof StaleAuthContextError || error instanceof KeyNotProvisionedError) throw error
          blocked.push(item.event_id)
        }
      }
      if (items.length < 8) break
    }
    return { applied, conflicts, orphans, blocked, listed }
  }

  async ackOnce(accountId: string, deviceId: string): Promise<MetadataAckResult> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const candidate = await this.ack.prepare(accountId, deviceId, context.userId)
    if (candidate.candidate_cursor === candidate.current_ack_cursor) return { status: 'no_progress', cursor: candidate.current_ack_cursor }
    const response = await this.auth.authorized(token => this.api.ack(token, deviceId, candidate.candidate_cursor))
    this.assertCurrent(context)
    if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    const status = await this.ack.commit(scope.account_id, deviceId, context.userId, candidate.current_ack_cursor, candidate.candidate_cursor)
    return { status, cursor: candidate.candidate_cursor }
  }
}
