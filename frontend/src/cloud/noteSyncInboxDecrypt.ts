import type { RuntimeKeyContext } from '@/auth/keyContext'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { ReceivedNoteSyncInboxItem, NoteSyncInboxRepository } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { EncryptedSyncProtocolError, openNoteSyncEvent } from './encryptedSyncProtocol'
import type { NoteSyncPlaintext } from './noteSyncCodec'

export const DEFAULT_NOTE_INBOX_DECRYPT_LIMIT = 8
export const MAX_NOTE_INBOX_DECRYPT_LIMIT = 32

export type NoteInboxDecryptErrorCode =
  | 'key_unavailable'
  | 'stale_auth_context'
  | 'invalid_inbox_scope'
  | 'missing_encrypted_object'
  | 'decrypt_failed'
  | 'invalid_note_payload'
  | 'metadata_mismatch'
  | 'dependency_not_synced'
  | 'unsupported_content_format'
  | 'runtime_unavailable'

export interface NoteInboxDecryptResult {
  readonly event_id: string
  readonly server_sequence: number
  readonly status: 'validated' | 'error'
  readonly error_code?: NoteInboxDecryptErrorCode
}

export interface NoteInboxDecryptPassResult {
  readonly listed: number
  readonly results: readonly NoteInboxDecryptResult[]
}

export class NoteInboxDecryptError extends Error {
  readonly name = 'NoteInboxDecryptError'
  constructor(readonly code: NoteInboxDecryptErrorCode) { super(code) }
}

function protocolErrorCode(error: unknown): NoteInboxDecryptErrorCode | null {
  if (!(error instanceof EncryptedSyncProtocolError)) return null
  switch (error.code) {
    case 'decrypt_failed': return 'decrypt_failed'
    case 'metadata_mismatch': return 'metadata_mismatch'
    case 'dependency_not_synced': return 'dependency_not_synced'
    case 'unsupported_content_format': return 'unsupported_content_format'
    case 'invalid_envelope':
    case 'payload_too_large': return 'invalid_note_payload'
    default: return 'runtime_unavailable'
  }
}

function readErrorCode(error: unknown): NoteInboxDecryptErrorCode {
  if (error instanceof StaleAuthContextError) return 'stale_auth_context'
  const message = error instanceof Error ? error.message : ''
  if (message.includes('account binding mismatch') || message.includes('pulling device mismatch') || message.includes('invalid inbox scope')) return 'invalid_inbox_scope'
  if (message.includes('no encrypted object') || message.includes('Sealed Note sync event has no encrypted object')) return 'missing_encrypted_object'
  return 'runtime_unavailable'
}

/**
 * Runs `visitor` only while the AMK lease is live.  It is intentionally not a
 * public UI data source: callers must consume plaintext synchronously within
 * this callback and may return metadata only.  C15.7B will use this boundary
 * to invoke its single SQLite apply transaction.
 */
async function withDecryptedReceivedNoteInbox<T>(
  auth: NormalUserAuthRuntime,
  bindings: AuthoritativeAccountBinding,
  keyContext: RuntimeKeyContext,
  repository: NoteSyncInboxRepository,
  localAccountId: string,
  deviceId: string,
  limit: number,
  visitor: (item: ReceivedNoteSyncInboxItem, plaintext: NoteSyncPlaintext) => Promise<T>,
): Promise<Array<{ event: ReceivedNoteSyncInboxItem, value?: T, error_code?: NoteInboxDecryptErrorCode }>> {
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_NOTE_INBOX_DECRYPT_LIMIT) {
    throw new RangeError('Invalid Note inbox decrypt limit.')
  }
  const binding = await bindings.ensureForCurrentUser(localAccountId)
  const lease = keyContext.leaseForAccount(localAccountId)
  if (lease === null || !lease.isCurrent()) throw new NoteInboxDecryptError('key_unavailable')
  if (lease.localAccountId !== localAccountId || lease.canonicalUserId !== binding.context.userId
    || lease.authEpoch !== binding.context.authEpoch) throw new NoteInboxDecryptError('invalid_inbox_scope')
  if (!auth.isCurrent(binding.context)) throw new StaleAuthContextError()
  return lease.use(async masterKey => {
    const items = await repository.listReceived(localAccountId, deviceId, lease.canonicalUserId, limit)
    // Once `use()` starts, RuntimeKeyContext's drain contract owns the
    // invalidation boundary.  Rust still checks the immutable account/device
    // scope, so this already-started pass can finish without crossing accounts.
    const values: Array<{ event: ReceivedNoteSyncInboxItem, value?: T, error_code?: NoteInboxDecryptErrorCode }> = []
    for (const item of items) {
      if (item.entity_type !== 'note') throw new NoteInboxDecryptError('invalid_inbox_scope')
      try {
        const plaintext = await openNoteSyncEvent(masterKey, lease.canonicalUserId, item, item.envelope)
        values.push({ event: item, value: await visitor(item, plaintext) })
      } catch (error) {
        const code = protocolErrorCode(error)
        if (code === null) throw error
        values.push({ event: item, error_code: code })
      } finally {
        item.envelope.nonce.fill(0)
        item.envelope.ciphertext.fill(0)
      }
    }
    return values
  })
}

/** Performs one bounded validation pass and returns metadata only; it never applies or persists plaintext. */
export class NoteSyncInboxDecryptor {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly keyContext: RuntimeKeyContext,
    private readonly repository: NoteSyncInboxRepository,
  ) {}

  async decryptOnce(localAccountId: string, deviceId: string, limit = DEFAULT_NOTE_INBOX_DECRYPT_LIMIT): Promise<NoteInboxDecryptPassResult> {
    let listed = 0
    const results: NoteInboxDecryptResult[] = []
    try {
      const values = await withDecryptedReceivedNoteInbox(
        this.auth, this.bindings, this.keyContext, this.repository, localAccountId, deviceId, limit,
        async (item) => ({ event_id: item.event_id, server_sequence: item.server_sequence }),
      )
      listed = values.length
      for (const value of values) {
        if (value.error_code) results.push({ event_id: value.event.event_id, server_sequence: value.event.server_sequence, status: 'error', error_code: value.error_code })
        else results.push({ ...value.value!, status: 'validated' })
      }
      return { listed, results }
    } catch (error) {
      const code = error instanceof NoteInboxDecryptError ? error.code : readErrorCode(error)
      if (error instanceof StaleAuthContextError) throw error
      throw new NoteInboxDecryptError(code)
    }
  }
}
