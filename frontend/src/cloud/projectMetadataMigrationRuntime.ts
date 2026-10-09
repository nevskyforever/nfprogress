import { encryptObjectBytes } from '@/crypto'
import { selectWriterFrame, compressionBlocker } from './frameCompression'
import { SQLiteProjectCoverRepository, type ProjectCoverRepository } from '@/infrastructure/sqlite/projectCoverRepository'
import { encryptedCoversApi } from '@/api/encryptedCovers'
import { encryptProjectCover, createProjectCoverBlobId } from './projectCoverCrypto'
import { authenticateCoverReference, createCoverReference, InvalidCoverReferenceError, type ProjectCoverReference } from './projectCoverReference'
import { projectCoverDataUrlToBytes } from '@/components/projects/projectCoverPreparation'
import { ApiError } from '@/api/client'
import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import { encryptedSyncV3Api, isAccountItem, type V3MetadataPushItem } from '@/api/encryptedSyncV3'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { SQLiteNoteSyncAckRepository, type NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { SQLiteNoteSyncInboxRepository, type NoteSyncInboxRepository, type CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { SQLiteProjectMetadataMigrationRepository, type MetadataScope, type MetadataMigrationStatus, type MetadataAuthorityView, type MetadataDecisionKind, type ProjectMetadataMigrationRepository } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import type { ProjectMetadata, ProjectMetadataEvent } from './projectMetadataCodec'
import { cloudProjectsApi } from '@/api/cloudProjects'
import { encodeProjectMetadataEvent, frameProjectMetadata, openProjectMetadataEvent, validateProjectMetadataEvent } from './projectMetadataCodec'
import { encodeBase64Url } from '@/api/base64url'
import { canonicalizeSyncTimestamp } from './syncTimestamp'

export interface MetadataApplyResult { applied: number; conflicts: number; orphans: number; blocked: readonly string[]; listed: number }
export interface MetadataAckResult { status: 'no_progress' | 'advanced' | 'already_acknowledged' | 'already_advanced' | 'stale'; cursor: number }
const now = (): string => canonicalizeSyncTimestamp(new Date().toISOString())

/** Internal migration boundary. Capture and publication require explicit calls. */
export interface CoverTransfer {
 intent_id:string;source_cover:string|null;state:string;reference:ProjectCoverReference|null;blob_id:string|null;nonce:number[]|null;ciphertext:number[]|null;event_id:string|null;blocker:string|null
}
export interface CoverAuthorityStatus { has_local_cover?:boolean;metadata_state:string;active:boolean;blockers:string[];pending?:Pick<CoverTransfer,'state'|'blocker'>|null }
export class ProjectMetadataMigrationRuntime {
  private readonly covers:ProjectCoverRepository|null
  constructor(
    protected readonly auth: NormalUserAuthRuntime,
    protected readonly bindings: AuthoritativeAccountBinding,
    protected readonly identity: CloudIdentityRepository,
    protected readonly keys: RuntimeKeyContext,
    private readonly native: ProjectMetadataMigrationRepository = new SQLiteProjectMetadataMigrationRepository(),
    private readonly inbox: NoteSyncInboxRepository = new SQLiteNoteSyncInboxRepository(),
    private readonly ack: NoteSyncAckRepository = new SQLiteNoteSyncAckRepository(),
    private readonly api: typeof encryptedSyncV3Api = encryptedSyncV3Api,
    private readonly importPageSize = 200,
    covers?:ProjectCoverRepository,
  ) { this.covers=covers ?? (native instanceof SQLiteProjectMetadataMigrationRepository ? new SQLiteProjectCoverRepository() : null) }

  protected async scope(accountId: string, deviceId: string): Promise<{ scope: MetadataScope; context: AuthContextSnapshot }> {
    const binding = await this.bindings.ensureForCurrentUser(accountId)
    const identity = await this.identity.read(binding.context.userId)
    if (!identity || identity.local_account_id !== accountId || identity.device_id !== deviceId || !this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const lease = this.keys.leaseForAccount(accountId)
    if (!lease) throw new KeyNotProvisionedError()
    if (!lease.isCurrent() || lease.canonicalUserId !== binding.context.userId || lease.authEpoch !== binding.context.authEpoch) throw new StaleAuthContextError()
    return { scope: { account_id: accountId, canonical_user_id: binding.context.userId, device_id: deviceId }, context: binding.context }
  }

  protected assertCurrent(context: AuthContextSnapshot): void {
    if (!this.auth.isCurrent(context)) throw new StaleAuthContextError()
  }

  async mode(accountId: string, deviceId: string): Promise<1 | 2 | 3> {
    const { context } = await this.scope(accountId, deviceId)
    const response = await this.auth.authorized(token => encryptedSyncV2Api.capabilities(token))
    this.assertCurrent(context)
    if (response.context.userId !== context.userId || response.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
    return parseV2Capabilities(response.value).writer_transport_version
  }

  protected async requireMode3(accountId: string, deviceId: string): Promise<void> {
    if (await this.mode(accountId, deviceId) !== 3) throw new TypeError('metadata_mode_3_required')
  }

  protected async advertiseCompression(accountId: string, deviceId: string): Promise<boolean> {
    const {context}=await this.scope(accountId,deviceId)
    // An injected older API adapter cannot prove support: stay ID0.
    if (!this.api.compressionReaderCapabilities) return false
    try {
      await this.auth.authorized(token=>this.api.compressionReaderCapabilities(token,deviceId))
      this.assertCurrent(context)
      return true
    } catch(error) {
      if (error instanceof StaleAuthContextError) throw error
      this.assertCurrent(context)
      return false
    }
  }

  protected async compressionFrame(accountId: string, deviceId: string, canonical: Uint8Array): Promise<Uint8Array> {
    if (!this.api.compressionWriter || !this.api.compressionReaderCapabilities) return canonical
    const {context}=await this.scope(accountId,deviceId)
    return selectWriterFrame(canonical, async()=>{
      try {
        if (!await this.advertiseCompression(accountId,deviceId)) return false
        const gate=await this.auth.authorized(token=>this.api.compressionWriter(token,deviceId))
        this.assertCurrent(context)
        return gate.value.ready===true && gate.value.missing_devices===0
      } catch(error) {
        // Capability unavailable/unknown is never authorization for ID1.
        // Authentication epoch changes remain hard failures.
        if (error instanceof StaleAuthContextError) throw error
        this.assertCurrent(context)
        return false
      }
    })
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
    await this.advertiseCompression(accountId,deviceId)
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
    if (!Number.isSafeInteger(this.importPageSize) || this.importPageSize < 1 || this.importPageSize > 200) throw new TypeError('metadata_import_page_limit')
    const bootstrapId = descriptor.bootstrap_id
    await this.advertiseCompression(accountId,deviceId)
    const { scope } = await this.scope(accountId, deviceId)
    let progress = await this.native.readImport(scope, projectId, bootstrapId)
    this.assertCurrent(context)
    if (progress.state === 'blocked') throw new TypeError(progress.blocker ?? 'metadata_import_blocked')
    // Bound work per explicit attempt; the saved cursor resumes after restart/retry.
    for (let page = 0; page < 16; page += 1) {
      const since = progress.cursor
      const response = await this.auth.authorized(token => this.api.pull(token, deviceId, since, this.importPageSize))
      this.assertCurrent(context)
      const wire = response.value
      if (wire.items.length > this.importPageSize || wire.next_cursor < since
        || (wire.has_more && wire.next_cursor <= since)) throw new TypeError('metadata_import_cursor')
      const events: Array<{ server_sequence: number; plaintext: number[] }> = []
      let sequence = since
      for (const item of wire.items) {
        if (item.event.server_sequence <= sequence || item.event.server_sequence > wire.next_cursor) throw new TypeError('metadata_import_cursor')
        sequence = item.event.server_sequence
        if (isAccountItem(item) || item.event.entity_type !== 'project_metadata' || item.event.project_id !== projectId) continue
        const lease = this.keys.leaseForAccount(accountId)
        if (!lease) throw new KeyNotProvisionedError()
        const opened = await lease.use(amk => openProjectMetadataEvent(amk,
          { account_id: context.userId, project_id: projectId, entity_id: projectId, event_id: item.event.event_id }, item.object))
        this.assertCurrent(context)
        if (opened.header.bootstrap_id !== bootstrapId || opened.header.device_id !== item.event.device_id
          || opened.header.revision !== item.event.revision || opened.header.updated_at !== canonicalizeSyncTimestamp(item.event.updated_at)
          || opened.deleted_at !== (item.event.deleted_at === null ? null : canonicalizeSyncTimestamp(item.event.deleted_at)) || (opened.header.operation === 'delete' ? 'delete' : 'upsert') !== item.event.operation) throw new TypeError('metadata_import_descriptor')
        if(opened.version===2 && opened.metadata?.cover_reference) await this.verifyIncomingCover(scope,context,projectId,opened.metadata.cover_reference)
        const plaintext = encodeProjectMetadataEvent(opened)
        try { events.push({ server_sequence: item.event.server_sequence, plaintext: Array.from(plaintext) }) }
        finally { plaintext.fill(0) }
      }
      if (sequence !== wire.next_cursor || (!wire.items.length && wire.has_more)) throw new TypeError('metadata_import_cursor')
      const identityBytes = new TextEncoder().encode(JSON.stringify({ since, next: wire.next_cursor, more: wire.has_more,
        items: wire.items.map(item => ({ event: item.event, nonce: encodeBase64Url(item.object.nonce), ciphertext: encodeBase64Url(item.object.ciphertext) })) }))
      const digest = await crypto.subtle.digest('SHA-256', identityBytes)
      const pageIdentity = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
      this.assertCurrent(context)
      progress = await this.native.commitImportPage(scope, projectId, bootstrapId, {
        expected_cursor: since, next_cursor: wire.next_cursor, has_more: wire.has_more,
        page_events: wire.items.length, page_identity: pageIdentity, events,
      })
      this.assertCurrent(context)
      if (progress.state === 'blocked') throw new TypeError(progress.blocker ?? 'metadata_import_blocked')
      if (progress.state === 'complete') {
        if (!progress.event_count) return null
        if (progress.head && !progress.metadata) throw new TypeError('metadata_import_deleted')
        return { bootstrapId, metadata: progress.metadata, head: progress.head, tips: progress.tips, cursor: progress.cursor }
      }
    }
    throw new MetadataImportContinuationError(progress.cursor)
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

  async coverAuthority(accountId:string,deviceId:string,projectId:string):Promise<CoverAuthorityStatus> {
    const {scope,context}=await this.scope(accountId,deviceId)
    if(!this.covers)throw new TypeError('cover_runtime_unavailable')
    const status=await this.covers.command<CoverAuthorityStatus>(scope,projectId,'status',{},now());this.assertCurrent(context)
    const pending=await this.covers.command<CoverTransfer|null>(scope,projectId,'pending',{},now());this.assertCurrent(context)
    return {...status,pending:pending?{state:pending.state,blocker:pending.blocker}:null}
  }
  async coverPreview(accountId:string,deviceId:string,projectId:string,reference:ProjectCoverReference):Promise<string|null>{
    const {scope,context}=await this.scope(accountId,deviceId)
    if(!this.covers)throw new TypeError('cover_runtime_unavailable')
    const value=await this.covers.command<string|null>(scope,projectId,'preview',{reference},now());this.assertCurrent(context);return value
  }
  async captureCover(accountId:string,deviceId:string,projectId:string):Promise<void> {
    await this.requireMode3(accountId,deviceId)
    const {scope,context}=await this.scope(accountId,deviceId)
    if(!this.covers)throw new TypeError('cover_runtime_unavailable')
    await this.covers.command(scope,projectId,'capture',{},now());this.assertCurrent(context)
  }
  private async coverGate(context:AuthContextSnapshot):Promise<boolean> {
    const response=await this.auth.authorized(token=>this.api.coverReaderGate(token));this.assertCurrent(context)
    if(response.context.userId!==context.userId||response.context.authEpoch!==context.authEpoch)throw new StaleAuthContextError()
    return response.value.ready
  }
  /** Only previously captured intents are processed. Login/open/background never captures a source. */
  async processCoverTransfers(accountId:string,deviceId:string):Promise<number> {
    if(!this.covers)return 0
    const {scope,context}=await this.scope(accountId,deviceId)
    await this.auth.authorized(token=>this.api.coverReaderCapabilities(token,deviceId));this.assertCurrent(context)
    const projects=await this.covers.command<string[]>(scope,'*','projects',{},now());this.assertCurrent(context)
    let prepared=0
    for(const projectId of projects){
      let intent=await this.covers.command<CoverTransfer|null>(scope,projectId,'pending',{},now());this.assertCurrent(context)
      if(!intent)continue
      if(!await this.coverGate(context)){await this.covers.command(scope,projectId,'block_intent',{intent_id:intent.intent_id,code:'cover_readers_not_ready'},now());continue}
      if(intent.state==='captured'){
        if(intent.source_cover===null){await this.covers.command(scope,projectId,'seal',{intent_id:intent.intent_id,reference:null},now())}
        else{
          let jpeg:Uint8Array
          try{jpeg=await projectCoverDataUrlToBytes(intent.source_cover)}catch{this.assertCurrent(context);await this.covers.command(scope,projectId,'block_intent',{intent_id:intent.intent_id,code:'cover_source_invalid'},now());continue}
          const lease=this.keys.leaseForAccount(accountId);if(!lease)throw new KeyNotProvisionedError()
          try{await lease.use(async amk=>{
            const identity={userId:context.userId,projectId,blobId:createProjectCoverBlobId()}
            const envelope=await encryptProjectCover(amk,identity,jpeg)
            const reference=await createCoverReference(amk,identity,jpeg,envelope)
            this.assertCurrent(context)
            await this.covers!.command(scope,projectId,'seal',{intent_id:intent!.intent_id,reference,nonce:Array.from(envelope.nonce),ciphertext:Array.from(envelope.ciphertext),jpeg:Array.from(jpeg)},now())
          })}catch(error){if(error instanceof StaleAuthContextError||error instanceof KeyNotProvisionedError)throw error;this.assertCurrent(context);await this.covers.command(scope,projectId,'block_intent',{intent_id:intent.intent_id,code:'cover_source_invalid'},now());continue}
          finally{jpeg.fill(0)}
        }
        this.assertCurrent(context);intent=await this.covers.command<CoverTransfer>(scope,projectId,'pending',{},now());this.assertCurrent(context)
      }
      if(intent.state==='sealed'){
        if(!intent.reference||!intent.blob_id||!intent.nonce||!intent.ciphertext)throw new TypeError('cover_transfer_invalid')
        const envelope={crypto_version:1 as const,aad_version:1 as const,nonce:Uint8Array.from(intent.nonce),ciphertext:Uint8Array.from(intent.ciphertext)}
        const uploaded=await this.auth.authorized(token=>encryptedCoversApi.upload(token,projectId,intent!.blob_id!,envelope));this.assertCurrent(context)
        if(uploaded.value.blob_id!==intent.blob_id||uploaded.value.project_id!==projectId||uploaded.value.kind!=='project_cover'||uploaded.value.size_bytes!==envelope.ciphertext.length)throw new TypeError('cover_blob_invalid')
        await this.verifyIncomingCover(scope,context,projectId,intent.reference)
        await this.covers.command(scope,projectId,'uploaded',{intent_id:intent.intent_id},now());this.assertCurrent(context)
        intent={...intent,state:'uploaded'}
      }
      if(intent.state==='uploaded'){
        if(!await this.coverGate(context))continue
        await this.covers.command(scope,projectId,'prepare',{intent_id:intent.intent_id},now());this.assertCurrent(context);prepared++
      }
    }
    return prepared
  }
  private async verifyIncomingCover(scope:MetadataScope,context:AuthContextSnapshot,projectId:string,reference:ProjectCoverReference):Promise<void>{
    if(!this.covers)throw new TypeError('cover_runtime_unavailable')
    const downloaded=await this.auth.authorized(token=>encryptedCoversApi.download(token,projectId,reference.blob_id));this.assertCurrent(context)
    const lease=this.keys.leaseForAccount(scope.account_id);if(!lease)throw new KeyNotProvisionedError()
    await lease.use(async amk=>{
      const jpeg=await authenticateCoverReference(amk,{userId:context.userId,projectId,blobId:reference.blob_id},reference,downloaded.value)
      try{this.assertCurrent(context);await this.covers!.command(scope,projectId,'material',{reference,nonce:Array.from(downloaded.value.nonce),ciphertext:Array.from(downloaded.value.ciphertext),jpeg:Array.from(jpeg)},now());this.assertCurrent(context)}finally{jpeg.fill(0)}
    })
  }

  async sealOnce(accountId: string, deviceId: string): Promise<number> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    await this.processCoverTransfers(accountId,deviceId)
    const events = await this.native.unsealed(scope)
    let sealed = 0
    for (const event of events) {
      validateProjectMetadataEvent(event)
      if(event.version===2 && !await this.coverGate(context))continue
      if (event.header.account_id !== scope.canonical_user_id || event.header.device_id !== deviceId) throw new TypeError('metadata_genesis_scope')
      const lease = this.keys.leaseForAccount(accountId)
      if (!lease) throw new KeyNotProvisionedError()
      await lease.use(async amk => {
        const original = frameProjectMetadata(event)
        let frame=original
        let envelope
        try { frame=await this.compressionFrame(accountId,deviceId,original); envelope = await encryptObjectBytes(amk, {userId:event.header.account_id,projectId:event.header.project_id,entityId:event.header.entity_id,entityType:'project_metadata'}, frame) }
        finally { frame.fill(0); original.fill(0) }
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
      const pushed = await this.auth.authorized(token => item.metadata_codec_version===2 ? this.api.pushCoverMetadata(token,deviceId,[event]) : this.api.pushMetadata(token, deviceId, [event]))
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
    await this.advertiseCompression(accountId,deviceId)
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
            if(event.version===2 && event.metadata?.cover_reference){
              try{await this.verifyIncomingCover(scope,context,item.project_id,event.metadata.cover_reference)}
              catch(error){
                if(error instanceof StaleAuthContextError||error instanceof KeyNotProvisionedError)throw error
                this.assertCurrent(context)
                const code=error instanceof ApiError&&(error.status===404||(error.status===503&&error.code==='encrypted_blob_unavailable'))?'cover_blob_missing':'cover_blob_invalid'
                await this.covers?.command(scope,item.project_id,'block',{event_id:item.event_id,reference:event.metadata.cover_reference,code},now());this.assertCurrent(context)
                throw error
              }
            }
            const plaintext = encodeProjectMetadataEvent(event)
            try { this.assertCurrent(context); return await this.native.apply(scope, item.project_id, plaintext, nonce, ciphertext, now()) }
            finally { plaintext.fill(0) }
          })
          if (outcome === 'applied') applied += 1
          else if (outcome === 'conflict_preserved') conflicts += 1
          else orphans += 1
        } catch (error) {
          if (error instanceof StaleAuthContextError || error instanceof KeyNotProvisionedError) throw error
          // This typed error is raised only after metadata AEAD opens and its
          // versioned decoder encounters an invalid reference. Retain the exact
          // authenticated descriptor, including invalid fields, for safe retry.
          if (error instanceof InvalidCoverReferenceError) {
            this.assertCurrent(context)
            await this.covers?.command(scope, item.project_id, 'block', {
              event_id: item.event_id, reference: error.reference, code: 'cover_blob_invalid',
            }, now())
            this.assertCurrent(context)
          }
          const compressionCode = compressionBlocker(error)
          if (compressionCode) {
            this.assertCurrent(context)
            await this.native.compressionBlock(scope, item.event_id, Uint8Array.from(item.nonce), Uint8Array.from(item.ciphertext), compressionCode)
            this.assertCurrent(context)
          }
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

export class MetadataImportContinuationError extends Error {
  constructor(readonly cursor: number) { super('metadata_import_continuation_required') }
}
export interface MetadataImportSnapshot { bootstrapId: string; metadata: ProjectMetadata | null; head: string | null; tips: string[]; cursor?: number }
export function metadataImportSnapshot(events: ProjectMetadataEvent[], bootstrapId: string, projectId: string): MetadataImportSnapshot | null {
  if (!events.length) return null
  const history = new Map<string, ProjectMetadataEvent>()
  const tips = new Set<string>()
  for (const event of events) {
    validateProjectMetadataEvent(event)
    const h = event.header
    if (h.bootstrap_id !== bootstrapId || h.project_id !== projectId) throw new TypeError('metadata_import_lineage')
    const prior = history.get(h.event_id)
    if (prior) {
      if (new TextDecoder().decode(encodeProjectMetadataEvent(prior)) !== new TextDecoder().decode(encodeProjectMetadataEvent(event))) throw new TypeError('metadata_import_replay')
      continue
    }
    const parents = h.parent_event_ids.map(id => history.get(id))
    if (parents.some(parent => !parent) || parents.some(parent => parent!.header.account_id !== h.account_id)) throw new TypeError('metadata_import_dependency')
    if (parents.length && (h.revision !== Math.max(...parents.map(parent => parent!.header.revision)) + 1 || h.generation <= Math.max(...parents.map(parent => parent!.header.generation)))) throw new TypeError('metadata_import_revision')
    if (['resolution', 'genesis_resolution'].includes(h.operation)) {
      // A subset resolution is historical conflict evidence; uncovered tips remain.
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
