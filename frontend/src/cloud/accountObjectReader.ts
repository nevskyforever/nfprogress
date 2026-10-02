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
  entity_id: string; entity_type: string; crypto_version: number; aad_version: number; nonce: number[]; ciphertext: number[]
}
export type AccountReaderBlocker = 'account_entity_codec_not_activated' | 'account_scope_rejected' | 'decrypt_failed'
export async function authenticateAccountObject(amk: AccountMasterKey, userId: string, row: ReceivedAccountObject): Promise<AccountReaderBlocker> {
  if (row.scope !== 'account' || row.canonical_user_id !== userId || !ACCOUNT_ENTITY_TYPES.includes(row.entity_type as typeof ACCOUNT_ENTITY_TYPES[number])
    || row.crypto_version !== 2 || row.aad_version !== 2) return 'account_scope_rejected'
  const plaintext = await decryptAccountObject(amk, { userId, scope: 'account', entityId: row.entity_id, entityType: row.entity_type },
    { crypto_version: 2, aad_version: 2, nonce: new Uint8Array(row.nonce), ciphertext: new Uint8Array(row.ciphertext) })
  // No payload parser/apply proof exists in this slice. Discard the transient decrypted
  // buffer, retain the exact encrypted history for future activated catalog readers.
  plaintext.fill(0)
  return 'account_entity_codec_not_activated'
}
export interface AccountInboxRepository {
  received(scope: MetadataScope, limit: number, after: number): Promise<ReceivedAccountObject[]>
  block(scope: MetadataScope, row: ReceivedAccountObject, code: AccountReaderBlocker): Promise<void>
}
const native: AccountInboxRepository = {
  received: (scope, limit, after) => invoke('list_received_account_objects', { scope, limit, after }),
  block: (scope, row, code) => invoke('block_account_object', { scope, eventId: row.event_id, nonce: row.nonce, ciphertext: row.ciphertext, code }),
}
export class AccountObjectReader extends ProjectMetadataMigrationRuntime {
  constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository,
    keys: RuntimeKeyContext, private readonly accountInbox: AccountInboxRepository = native) { super(auth, bindings, identity, keys) }
  async readOnce(accountId: string, deviceId: string, limit = 8, maxPasses = 4): Promise<{ blocked: AccountReaderBlocker[]; listed: number; hasRemainingWork: boolean }> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32 || !Number.isSafeInteger(maxPasses) || maxPasses < 1 || maxPasses > 8) throw new RangeError('invalid_account_reader_limits')
    const { scope, context } = await this.scope(accountId, deviceId)
    const blocked: AccountReaderBlocker[] = []
    let after = 0, listed = 0, remaining = false
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
        try { code = await lease.use(amk => authenticateAccountObject(amk, context.userId, row)) }
        catch (error) {
          if (!(error instanceof Error) || error.name !== 'CryptoError') throw error
          code = 'decrypt_failed'
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
    return { blocked: [...new Set(blocked)], listed, hasRemainingWork: remaining }
  }
}
