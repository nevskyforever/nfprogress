import { frameCatalogEvent, openCatalogEvent } from './accountCatalogCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'
import { invoke } from '@tauri-apps/api/core'
import { ACCOUNT_ENTITY_TYPES, decryptAccountObject } from '@/crypto/accountObjectCrypto'
import type { AccountMasterKey } from '@/crypto'
import { diagnostics } from '@/diagnostics/service'
import { KeyNotProvisionedError, type RuntimeKeyContext } from '@/auth/keyContext'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { MetadataScope } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import { ProjectMetadataMigrationRuntime } from './projectMetadataMigrationRuntime'

export interface ReceivedAccountObject {
  event_id: string; server_sequence: number; canonical_user_id: string; scope: string;
  source_device_id?:string;operation?:string;revision?:number;updated_at?:string;deleted_at?:string|null;
  entity_id: string; entity_type: string; crypto_version: number; aad_version: number; nonce: number[]; ciphertext: number[]
}
export type AccountReaderBlocker = 'account_entity_codec_not_activated' | 'account_scope_rejected' | 'decrypt_failed' | 'invalid_catalog_frame' | 'catalog_dependency_missing' | 'catalog_parent_unknown' | 'catalog_membership_changed' | 'catalog_project_unproven' | 'catalog_folder_has_members' | 'catalog_resource_limit' | 'catalog_dependency_conflict' | 'unsupported_catalog_source'
export async function authenticateAccountObject(amk: AccountMasterKey, userId: string, row: ReceivedAccountObject): Promise<AccountReaderBlocker> {
  if (row.scope !== 'account' || row.canonical_user_id !== userId || !ACCOUNT_ENTITY_TYPES.includes(row.entity_type as typeof ACCOUNT_ENTITY_TYPES[number])
    || row.crypto_version !== 2 || row.aad_version !== 2) return 'account_scope_rejected'
  const plaintext = await decryptAccountObject(amk, { userId, scope: 'account', entityId: row.entity_id, entityType: row.entity_type },
    { crypto_version: 2, aad_version: 2, nonce: new Uint8Array(row.nonce), ciphertext: new Uint8Array(row.ciphertext) })
  // An authentication-only probe cannot establish durable apply proof. The
  // activated production reader below requires the native catalog transaction.
  plaintext.fill(0)
  return 'account_entity_codec_not_activated'
}
export interface AccountInboxRepository {
  apply?(scope:MetadataScope,row:ReceivedAccountObject,frame:Uint8Array):Promise<string>
  received(scope: MetadataScope, limit: number, after: number): Promise<ReceivedAccountObject[]>
  block(scope: MetadataScope, row: ReceivedAccountObject, code: AccountReaderBlocker): Promise<void>
}
const native: AccountInboxRepository = {
  apply:(scope,row,frame)=>invoke('apply_account_catalog',{scope,eventId:row.event_id,frame:Array.from(frame),nonce:row.nonce,ciphertext:row.ciphertext}),
  received: (scope, limit, after) => invoke('list_received_account_objects', { scope, limit, after }),
  block: (scope, row, code) => invoke('block_account_object', { scope, eventId: row.event_id, nonce: row.nonce, ciphertext: row.ciphertext, code }),
}
export class AccountObjectReader extends ProjectMetadataMigrationRuntime {
  private retryPage: { scope: string; after: number } | undefined
  constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository,
    keys: RuntimeKeyContext, private readonly accountInbox: AccountInboxRepository = native) { super(auth, bindings, identity, keys) }
  async readOnce(accountId: string, deviceId: string, limit = 8, maxPasses = 4): Promise<{ blocked: AccountReaderBlocker[]; listed: number; hasRemainingWork: boolean }> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32 || !Number.isSafeInteger(maxPasses) || maxPasses < 1 || maxPasses > 8) throw new RangeError('invalid_account_reader_limits')
    const { scope, context } = await this.scope(accountId, deviceId)
    const blocked: AccountReaderBlocker[] = []
    const retryScope = JSON.stringify([scope.account_id, scope.device_id, context.userId, context.authEpoch])
    let after = this.retryPage?.scope === retryScope ? this.retryPage.after : 0, listed = 0, remaining = false, changed=false
    for (let pass = 0; pass < maxPasses; pass++) {
      const rows = await this.accountInbox.received(scope, limit, after)
      this.assertCurrent(context)
      if (rows.length > limit) throw new TypeError('account_scope_rejected')
      for (const row of rows) {
        if (!Number.isSafeInteger(row.server_sequence) || row.server_sequence <= after) throw new TypeError('account_scope_rejected')
        const lease = this.keys.leaseForAccount(accountId)
        if (!lease) throw new KeyNotProvisionedError()
        if (!lease.isCurrent() || lease.canonicalUserId !== context.userId || lease.authEpoch !== context.authEpoch) throw new StaleAuthContextError()
        let code: AccountReaderBlocker
        try {
          if (this.accountInbox.apply) {
            if(row.scope!=='account'||row.canonical_user_id!==context.userId||row.crypto_version!==2||row.aad_version!==2)throw new TypeError('account_scope_rejected')
            const event=await lease.use(amk=>openCatalogEvent(amk,context.userId,row.entity_id,row.entity_type,{crypto_version:2,aad_version:2,nonce:Uint8Array.from(row.nonce),ciphertext:Uint8Array.from(row.ciphertext)}))
            const h=event.header
            if(h.event_id!==row.event_id || h.device_id!==row.source_device_id || h.revision!==row.revision || h.updated_at!==canonicalizeSyncTimestamp(row.updated_at!) || event.deleted_at!==(row.deleted_at===null?null:canonicalizeSyncTimestamp(row.deleted_at!)) || (event.deleted_at===null?'upsert':'delete')!==row.operation) throw new TypeError('account_scope_rejected')
            const frame=frameCatalogEvent(event)
            let outcome:string;try {this.assertCurrent(context);outcome=await this.accountInbox.apply(scope,row,frame)}finally{frame.fill(0)}
            if(outcome==='applied'||outcome==='conflict_preserved'){this.assertCurrent(context);diagnostics.record('sync','sync_cycle','apply_result',undefined,{status:outcome,target_type:row.entity_type},outcome==='conflict_preserved'?'warning':'info');after=row.server_sequence;listed+=1;changed=true;continue}
            code=outcome as AccountReaderBlocker
          } else code = await lease.use(amk => authenticateAccountObject(amk, context.userId, row))
        }
        catch (error) {
          if(error instanceof StaleAuthContextError || error instanceof KeyNotProvisionedError)throw error
          code=typeof error==='string' && ['catalog_resource_limit','catalog_project_unproven','catalog_dependency_conflict','unsupported_catalog_source'].includes(error)?error as AccountReaderBlocker:error instanceof TypeError && error.message==='invalid_catalog_frame'?'invalid_catalog_frame':error instanceof Error && error.name==='CryptoError'?'decrypt_failed':'account_scope_rejected'
        }
        this.assertCurrent(context)
        await this.accountInbox.block(scope, row, code)
        this.assertCurrent(context)
        diagnostics.record('sync', 'sync_cycle', 'blocker', undefined, { error_code: code }, 'warning')
        blocked.push(code); listed++; after = row.server_sequence
      }
      remaining = rows.length === limit
      if (!remaining) break
    }
    // Continue keyset traversal across bounded cycles so an old blocked prefix
    // cannot starve the successor that makes it recoverable. End-of-list resets
    // the next cycle to retry retained blockers; this is never an ACK cursor.
    this.retryPage = { scope: retryScope, after: remaining ? after : 0 }
    return { blocked: [...new Set(blocked)], listed, hasRemainingWork: remaining||changed }
  }
}
