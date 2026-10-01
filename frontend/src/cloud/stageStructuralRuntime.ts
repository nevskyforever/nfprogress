import { encryptedSyncV3Api } from '@/api/encryptedSyncV3'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import { SQLiteStageStructuralRepository, type StructuralDecision, type StructuralView } from '@/infrastructure/sqlite/stageStructuralRepository'
import { ProjectMetadataMigrationRuntime, type MetadataApplyResult } from './projectMetadataMigrationRuntime'
import { frameStructuralEvent, openStructuralEvent, sealStructuralEvent, validateStructuralEvent } from './stageCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'
const now = (): string => canonicalizeSyncTimestamp(new Date().toISOString())
/** Reuses the accepted account/key/device guards. Only begin captures legacy Stages. */
export class StageStructuralRuntime extends ProjectMetadataMigrationRuntime {
  constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository,
    keys: RuntimeKeyContext, private readonly structural = new SQLiteStageStructuralRepository(),
    private readonly structuralApi = encryptedSyncV3Api) { super(auth, bindings, identity, keys) }
  async view(accountId: string, deviceId: string, projectId: string): Promise<StructuralView> {
    const { scope, context } = await this.scope(accountId, deviceId)
    const view = await this.structural.authority(scope, projectId); this.assertCurrent(context); return view
  }
  async beginStructure(accountId: string, deviceId: string, projectId: string): Promise<StructuralView> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const view = await this.structural.begin(scope, projectId, now()); this.assertCurrent(context); return view
  }
  async decideStructure(accountId: string, deviceId: string, projectId: string, decision: StructuralDecision): Promise<string> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const id = await this.structural.decide(scope, projectId, decision, now()); this.assertCurrent(context); return id
  }
  override async sealOnce(accountId: string, deviceId: string): Promise<number> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const items = await this.structural.pending(scope, false)
    for (const { event } of items) {
      validateStructuralEvent(event)
      if (event.header.account_id !== context.userId || event.header.device_id !== deviceId) throw new TypeError('structural_scope_mismatch')
      const lease = this.keys.leaseForAccount(accountId)
      if (!lease) throw new KeyNotProvisionedError()
      await lease.use(async amk => {
        const sealed = await sealStructuralEvent(amk, event); this.assertCurrent(context)
        const frame = frameStructuralEvent(event)
        try { await this.structural.seal(scope, event.header.event_id, frame, sealed.nonce, sealed.ciphertext) }
        finally { frame.fill(0) }
      })
    }
    return items.length
  }
  override async uploadOnce(accountId: string, deviceId: string): Promise<number> {
    await this.requireMode3(accountId, deviceId)
    const { scope, context } = await this.scope(accountId, deviceId)
    const items = await this.structural.pending(scope, true)
    for (const { event, nonce, ciphertext } of items) {
      validateStructuralEvent(event)
      if (!nonce || !ciphertext || event.header.account_id !== context.userId || event.header.device_id !== deviceId) throw new TypeError('structural_scope_mismatch')
      const h = event.header
      const pushed = await this.auth.authorized(token => this.structuralApi.pushMetadata(token, deviceId, [{
        event: { event_id: h.event_id, project_id: h.project_id, entity_id: h.entity_id, entity_type: h.entity_type,
          operation: h.operation === 'delete' ? 'delete' : 'upsert', revision: h.revision, updated_at: h.updated_at, deleted_at: event.deleted_at },
        object: { crypto_version: 1, aad_version: 1, nonce: Uint8Array.from(nonce), ciphertext: Uint8Array.from(ciphertext) },
      }]))
      this.assertCurrent(context)
      if (pushed.context.userId !== context.userId || pushed.context.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
      const receipt = pushed.value.results[0]
      if (pushed.value.results.length !== 1 || receipt?.event_id !== h.event_id) throw new TypeError('structural_receipt_mismatch')
      await this.structural.receipt(scope, h.event_id, receipt.server_sequence, receipt.duplicate, now())
    }
    return items.length
  }
  override async applyOnce(accountId: string, deviceId: string, maxPages = 4): Promise<MetadataApplyResult> {
    await this.requireMode3(accountId, deviceId)
    if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 8) throw new RangeError('structural_apply_limit')
    const { scope, context } = await this.scope(accountId, deviceId)
    let applied = 0, conflicts = 0, orphans = 0, listed = 0, after = 0
    const blocked: string[] = []
    for (let page = 0; page < maxPages; page += 1) {
      const items = await this.structural.received(scope, 8, after)
      if (!items.length) break
      listed += items.length
      for (const item of items) {
        after = item.server_sequence
        try {
          if (item.crypto_version !== 1 || item.aad_version !== 1 || !['stage', 'stage_order'].includes(item.entity_type)) throw new TypeError('structural_scope_mismatch')
          const lease = this.keys.leaseForAccount(accountId)
          if (!lease) throw new KeyNotProvisionedError()
          const outcome = await lease.use(async amk => {
            const nonce = Uint8Array.from(item.nonce), ciphertext = Uint8Array.from(item.ciphertext)
            const event = await openStructuralEvent(amk, { account_id: context.userId, project_id: item.project_id,
              entity_id: item.entity_id, entity_type: item.entity_type, event_id: item.event_id }, { crypto_version: 1, aad_version: 1, nonce, ciphertext })
            const h = event.header
            if (h.device_id !== item.source_device_id || h.revision !== item.revision || h.updated_at !== canonicalizeSyncTimestamp(item.updated_at)
              || event.deleted_at !== (item.deleted_at === null ? null : canonicalizeSyncTimestamp(item.deleted_at))
              || (h.operation === 'delete' ? 'delete' : 'upsert') !== item.operation) throw new TypeError('structural_scope_mismatch')
            const frame = frameStructuralEvent(event)
            try { this.assertCurrent(context); return await this.structural.apply(scope, item.event_id, frame, nonce, ciphertext) }
            finally { frame.fill(0) }
          })
          if (outcome === 'applied') applied += 1
          else if (outcome === 'conflict_preserved') conflicts += 1
          else { orphans += 1; blocked.push(item.event_id) }
        } catch (error) {
          if (error instanceof StaleAuthContextError || error instanceof KeyNotProvisionedError) throw error
          this.assertCurrent(context)
          await this.structural.block(scope, item.event_id, (error === 'metadata_scope_mismatch' || error instanceof TypeError && error.message === 'structural_scope_mismatch') ? 'structural_scope_mismatch' : error instanceof TypeError && error.message === 'invalid_stage_structure' ? 'invalid_stage_frame' : 'structural_authentication_failed')
          blocked.push(item.event_id)
        }
      }
      if (items.length < 8) break
    }
    this.assertCurrent(context)
    await this.structural.retry(scope)
    return { applied, conflicts, orphans, blocked, listed }
  }
}
