import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api, type V3MetadataPushItem } from '@/api/encryptedSyncV3'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { SQLiteNoteSyncAckRepository, type NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { SQLiteNoteSyncInboxRepository, type NoteSyncInboxRepository, type CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { SQLiteProjectMetadataMigrationRepository, type MetadataScope, type MetadataMigrationStatus, type MetadataAuthorityView, type MetadataDecisionKind, type ProjectMetadataMigrationRepository } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import type { ProjectMetadata, ProjectMetadataEvent } from './projectMetadataCodec'
import { cloudProjectsApi } from '@/api/cloudProjects'
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

  /** Separate explicit preparation of the frozen mode-2 prerequisite. */
  async prepareTransport(accountId: string, deviceId: string): Promise<void> {
    const { context } = await this.scope(accountId, deviceId)
    const capabilities = await this.auth.authorized(token => encryptedSyncV2Api.capabilities(token))
    this.assertCurrent(context)
    const current = parseV2Capabilities(capabilities.value)
    if (current.writer_transport_version !== 1) return
    await this.auth.authorized(token => encryptedSyncV2Api.cutover(token, current.cutover_epoch))
    this.assertCurrent(context)
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

  /** Read a bounded complete authenticated history before creating a new imported shell. */
  async importSnapshot(accountId: string, deviceId: string, projectId: string): Promise<MetadataImportSnapshot | null> {
    if (await this.mode(accountId, deviceId) !== 3) return null
    const { context } = await this.scope(accountId, deviceId)
    const descriptors = await this.auth.authorized(token => cloudProjectsApi.listBootstraps(token))
    this.assertCurrent(context)
    const descriptor = descriptors.value.projects.find(project => project.project_id === projectId)
    if (!descriptor?.bootstrap_id || descriptor.state !== 'active') throw new TypeError('metadata_import_lineage')
    const events: ProjectMetadataEvent[] = []
    let cursor = 0
    for (let page = 0; page < 16; page += 1) {
      const response = await this.auth.authorized(token => this.api.pull(token, deviceId, cursor))
      this.assertCurrent(context)
      for (const item of response.value.items) {
        if (item.event.entity_type !== 'project_metadata' || item.event.project_id !== projectId) continue
        const lease = this.keys.leaseForAccount(accountId)
        if (!lease) throw new KeyNotProvisionedError()
        const opened = await lease.use(amk => openProjectMetadataEvent(amk,
          { account_id: context.userId, project_id: projectId, entity_id: projectId, event_id: item.event.event_id }, item.object))
        this.assertCurrent(context)
        if (opened.header.bootstrap_id !== descriptor.bootstrap_id || opened.header.device_id !== item.event.device_id
          || opened.header.revision !== item.event.revision || opened.header.updated_at !== canonicalizeSyncTimestamp(item.event.updated_at)
          || opened.deleted_at !== (item.event.deleted_at === null ? null : canonicalizeSyncTimestamp(item.event.deleted_at)) || (opened.header.operation === 'delete' ? 'delete' : 'upsert') !== item.event.operation) throw new TypeError('metadata_import_descriptor')
        events.push(opened)
      }
      if (!response.value.has_more) return metadataImportSnapshot(events, descriptor.bootstrap_id, projectId)
      if (response.value.next_cursor <= cursor) throw new TypeError('metadata_import_cursor')
      cursor = response.value.next_cursor
    }
    throw new TypeError('metadata_import_history_budget')
  }

  async status(accountId: string, deviceId: string, projectId: string): Promise<MetadataMigrationStatus> {
    const { scope } = await this.scope(accountId, deviceId)
    return this.native.status(scope, projectId)
  }

  async authority(accountId: string, deviceId: string, projectId: string): Promise<MetadataAuthorityView> {
    const { scope } = await this.scope(accountId, deviceId)
    return this.native.authority(scope, projectId)
  }

  async adopt(accountId: string, deviceId: string, projectId: string,
    expectedHead: string, expectedLocal: ProjectMetadata): Promise<MetadataAuthorityView> {
    await this.requireMode3(accountId, deviceId)
    const { scope } = await this.scope(accountId, deviceId)
    return this.native.adopt(scope, projectId, expectedHead, expectedLocal, now())
  }

  async decide(accountId: string, deviceId: string, projectId: string, kind: MetadataDecisionKind,
    selectedEventId: string | null, proposed: ProjectMetadata | null, expectedLocal: ProjectMetadata,
    expectedTips: string[]): Promise<string> {
    await this.requireMode3(accountId, deviceId)
    const { scope } = await this.scope(accountId, deviceId)
    return this.native.prepareChange(scope, projectId, kind, selectedEventId, proposed, expectedLocal, expectedTips, now())
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
      if (!Number.isSafeInteger(item.revision) || item.revision < 1 || item.nonce.length !== 24) throw new TypeError('metadata_sealed_event_invalid')
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
            if (h.device_id !== item.source_device_id || h.revision !== item.revision || h.updated_at !== canonicalizeSyncTimestamp(item.updated_at)
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

export interface MetadataImportSnapshot { bootstrapId: string; metadata: ProjectMetadata | null; head: string | null; tips: string[] }
export function metadataImportSnapshot(events: ProjectMetadataEvent[], bootstrapId: string, projectId: string): MetadataImportSnapshot | null {
  if (!events.length) return null
  const history = new Map<string, ProjectMetadataEvent>()
  const tips = new Set<string>()
  for (const event of events) {
    validateProjectMetadataEvent(event)
    const h = event.header
    if (h.bootstrap_id !== bootstrapId || h.project_id !== projectId || history.has(h.event_id)) throw new TypeError('metadata_import_lineage')
    const parents = h.parent_event_ids.map(id => history.get(id))
    if (parents.some(parent => !parent) || parents.some(parent => parent!.header.account_id !== h.account_id)) throw new TypeError('metadata_import_dependency')
    if (parents.length && h.revision !== Math.max(...parents.map(parent => parent!.header.revision)) + 1) throw new TypeError('metadata_import_revision')
    if (['resolution', 'genesis_resolution'].includes(h.operation)) {
      if ([...tips].sort().join(',') !== h.parent_event_ids.join(',')) throw new TypeError('metadata_import_resolution')
      if (h.operation === 'genesis_resolution' && parents.some(parent => parent!.header.operation !== 'create')) throw new TypeError('metadata_import_resolution')
    }
    for (const parent of h.parent_event_ids) tips.delete(parent)
    tips.add(h.event_id); history.set(h.event_id, event)
  }
  const ids = [...tips].sort()
  const head = ids.length === 1 ? ids[0]! : null
  const metadata = head ? history.get(head)!.metadata : null
  if (head && !metadata) throw new TypeError('metadata_import_deleted')
  return { bootstrapId, metadata, head, tips: ids }
}
