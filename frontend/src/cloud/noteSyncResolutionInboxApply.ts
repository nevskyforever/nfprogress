import { MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES } from '@/api/encryptedSync'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import { AAD_VERSION, CRYPTO_VERSION, CryptoError, decryptObjectBytes, type AccountMasterKey } from '@/crypto'
import type {
  NoteSyncInboxRepository,
  ReceivedNoteResolutionInboxItem,
  ReceivedNoteSyncInboxItem,
} from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type {
  NoteSyncResolutionPeerApplyStatus,
  NoteSyncResolutionRemoteApplyRepository,
  NoteSyncResolutionSelfEchoStatus,
  VerifiedNoteSyncRemoteApplyCommand,
} from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { decodeNoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'

export const DEFAULT_RESOLUTION_INBOX_APPLY_LIMIT = 8
export const MAX_RESOLUTION_INBOX_APPLY_LIMIT = 32
export const MAX_ORPHAN_RETRY_PAGES = 2

export type NoteResolutionInboxApplyStatus = NoteSyncResolutionPeerApplyStatus | NoteSyncResolutionSelfEchoStatus
export type NoteResolutionInboxApplyErrorCode =
  | 'key_unavailable'
  | 'stale_auth_context'
  | 'invalid_inbox_scope'
  | 'orphan_retry_unavailable'
  | 'invalid_envelope'
  | 'decrypt_failed'
  | 'invalid_resolution_payload'
  | 'metadata_mismatch'
  | 'ipc_failure'
  | 'invalid_native_status'
  | 'runtime_unavailable'

export interface NoteResolutionInboxApplyResult {
  readonly event_id: string
  readonly server_sequence: number
  readonly status: NoteResolutionInboxApplyStatus | 'error'
  readonly error_code?: NoteResolutionInboxApplyErrorCode
}

export class NoteResolutionInboxApplyError extends Error {
  readonly name = 'NoteResolutionInboxApplyError'
  constructor(readonly code: NoteResolutionInboxApplyErrorCode) { super(code) }
}

interface ResolutionApplyScope {
  readonly accountId: string
  readonly canonicalUserId: string
  readonly pullingDeviceId: string
}

const PEER_STATUSES: readonly NoteSyncResolutionPeerApplyStatus[] = ['applied', 'already_applied', 'orphan', 'self_echo_pending']
const SELF_ECHO_STATUSES: readonly NoteSyncResolutionSelfEchoStatus[] = ['reconciled', 'already_reconciled']

function clearEnvelope(item: ReceivedNoteSyncInboxItem): void {
  item.envelope.nonce.fill(0)
  item.envelope.ciphertext.fill(0)
}

function topLevelError(error: unknown): NoteResolutionInboxApplyError {
  if (error instanceof NoteResolutionInboxApplyError) return error
  if (error instanceof StaleAuthContextError) return new NoteResolutionInboxApplyError('stale_auth_context')
  return new NoteResolutionInboxApplyError('runtime_unavailable')
}

function validateEnvelope(item: ReceivedNoteResolutionInboxItem): void {
  const { envelope } = item
  if (envelope.crypto_version !== CRYPTO_VERSION || envelope.aad_version !== AAD_VERSION
    || !(envelope.nonce instanceof Uint8Array) || envelope.nonce.byteLength !== 24
    || !(envelope.ciphertext instanceof Uint8Array) || envelope.ciphertext.byteLength < 16
    || envelope.ciphertext.byteLength > MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES) {
    throw new NoteResolutionInboxApplyError('invalid_envelope')
  }
}

function validateInboxMetadata(item: ReceivedNoteResolutionInboxItem): void {
  if (item.entity_type !== 'note' || item.operation !== 'resolution' || item.deleted_at !== null
    || !Number.isSafeInteger(item.server_sequence) || item.server_sequence < 0
    || !Number.isSafeInteger(item.revision) || item.revision < 2
    || !item.event_id || !item.source_device_id || !item.project_id || !item.entity_id || !item.updated_at) {
    throw new NoteResolutionInboxApplyError('metadata_mismatch')
  }
}

function errorCode(error: unknown, dispatchStarted: boolean): NoteResolutionInboxApplyErrorCode {
  if (error instanceof NoteResolutionInboxApplyError) return error.code
  if (dispatchStarted) return 'ipc_failure'
  if (error instanceof CryptoError) {
    if (error.code === 'decrypt_failed') return 'decrypt_failed'
    if (error.code === 'invalid_format' || error.code === 'unsupported_version') return 'invalid_envelope'
    return 'runtime_unavailable'
  }
  if (error instanceof TypeError && error.name === 'invalid_note_payload') return 'invalid_resolution_payload'
  return 'runtime_unavailable'
}

/**
 * Dormant authenticated resolution-v2 decrypt-to-native boundary. It owns no
 * key cache, scheduler or cursor and returns metadata/status only.
 */
export class NoteSyncResolutionInboxApplier {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly keyContext: RuntimeKeyContext,
    private readonly inbox: NoteSyncInboxRepository,
    private readonly nativeApply: NoteSyncResolutionRemoteApplyRepository,
  ) {}

  private validateLimit(limit: number): void {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_RESOLUTION_INBOX_APPLY_LIMIT) {
      throw new RangeError('Invalid resolution inbox apply limit.')
    }
  }

  private async withAuthoritativeLease<T>(
    localAccountId: string,
    deviceId: string,
    operation: (masterKey: AccountMasterKey, scope: ResolutionApplyScope) => Promise<T>,
  ): Promise<T> {
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    try {
      await this.inbox.readPullState(localAccountId, deviceId, binding.context.userId)
    } catch (error) {
      const message = error instanceof Error ? error.message : ''
      if (message.includes('account binding mismatch') || message.includes('pulling device mismatch') || message.includes('invalid inbox scope')) {
        throw new NoteResolutionInboxApplyError('invalid_inbox_scope')
      }
      throw error
    }
    const lease = this.keyContext.leaseForAccount(localAccountId)
    if (lease === null || !lease.isCurrent()) throw new NoteResolutionInboxApplyError('key_unavailable')
    if (lease.localAccountId !== localAccountId || lease.canonicalUserId !== binding.context.userId
      || lease.authEpoch !== binding.context.authEpoch) throw new NoteResolutionInboxApplyError('invalid_inbox_scope')
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    return lease.use(masterKey => operation(masterKey, {
      accountId: localAccountId,
      canonicalUserId: lease.canonicalUserId,
      pullingDeviceId: deviceId,
    }))
  }

  private async applyItem(
    masterKey: AccountMasterKey,
    scope: ResolutionApplyScope,
    item: ReceivedNoteResolutionInboxItem,
  ): Promise<NoteResolutionInboxApplyResult> {
    let plaintext: Uint8Array | undefined
    let nonce: number[] | undefined
    let ciphertext: number[] | undefined
    let wirePlaintext: number[] | undefined
    let dispatchStarted = false
    try {
      validateInboxMetadata(item)
      validateEnvelope(item)
      plaintext = await decryptObjectBytes(masterKey, {
        userId: scope.canonicalUserId,
        projectId: item.project_id,
        entityId: item.entity_id,
        entityType: 'note',
      }, item.envelope)
      const resolution = decodeNoteSyncResolutionV2(plaintext)
      if (resolution.header.event_id !== item.event_id
        || resolution.header.project_id !== item.project_id
        || resolution.header.entity_id !== item.entity_id
        || resolution.header.entity_type !== item.entity_type
        || resolution.header.operation !== item.operation
        || resolution.header.revision !== item.revision
        || resolution.header.updated_at !== item.updated_at
        || item.deleted_at !== null) {
        throw new NoteResolutionInboxApplyError('metadata_mismatch')
      }
      nonce = Array.from(item.envelope.nonce)
      ciphertext = Array.from(item.envelope.ciphertext)
      wirePlaintext = Array.from(plaintext)
      const command: VerifiedNoteSyncRemoteApplyCommand = {
        account_id: scope.accountId,
        canonical_user_id: scope.canonicalUserId,
        pulling_device_id: scope.pullingDeviceId,
        event_id: item.event_id,
        server_sequence: item.server_sequence,
        source_device_id: item.source_device_id,
        crypto_version: item.envelope.crypto_version,
        aad_version: item.envelope.aad_version,
        nonce,
        ciphertext,
        plaintext: wirePlaintext,
      }
      dispatchStarted = true
      if (item.source_device_id === scope.pullingDeviceId) {
        const status = await this.nativeApply.reconcileVerifiedResolutionSelfEcho(command)
        if (!SELF_ECHO_STATUSES.includes(status)) throw new NoteResolutionInboxApplyError('invalid_native_status')
        return { event_id: item.event_id, server_sequence: item.server_sequence, status }
      }
      const status = await this.nativeApply.applyVerifiedResolution(command)
      if (!PEER_STATUSES.includes(status)) throw new NoteResolutionInboxApplyError('invalid_native_status')
      return { event_id: item.event_id, server_sequence: item.server_sequence, status }
    } catch (error) {
      return {
        event_id: item.event_id,
        server_sequence: item.server_sequence,
        status: 'error',
        error_code: errorCode(error, dispatchStarted),
      }
    } finally {
      plaintext?.fill(0)
      nonce?.fill(0)
      ciphertext?.fill(0)
      wirePlaintext?.fill(0)
      clearEnvelope(item)
    }
  }

  async applyReceivedOnce(
    localAccountId: string,
    deviceId: string,
    limit = DEFAULT_RESOLUTION_INBOX_APPLY_LIMIT,
  ): Promise<readonly NoteResolutionInboxApplyResult[]> {
    this.validateLimit(limit)
    try {
      return await this.withAuthoritativeLease(localAccountId, deviceId, async (masterKey, scope) => {
        const items = await this.inbox.listReceived(localAccountId, deviceId, scope.canonicalUserId, limit)
        const resolutions = items.filter((item): item is ReceivedNoteResolutionInboxItem => item.operation === 'resolution')
        for (const item of items) if (item.operation !== 'resolution') clearEnvelope(item)
        const results: NoteResolutionInboxApplyResult[] = []
        for (const item of resolutions) results.push(await this.applyItem(masterKey, scope, item))
        return results
      })
    } catch (error) {
      throw topLevelError(error)
    }
  }

  async retryOrphansOnce(
    localAccountId: string,
    deviceId: string,
    limit = DEFAULT_RESOLUTION_INBOX_APPLY_LIMIT,
  ): Promise<readonly NoteResolutionInboxApplyResult[]> {
    this.validateLimit(limit)
    const listOrphans = this.inbox.listOrphanResolutions?.bind(this.inbox)
    if (listOrphans === undefined) throw new NoteResolutionInboxApplyError('orphan_retry_unavailable')
    try {
      return await this.withAuthoritativeLease(localAccountId, deviceId, async (masterKey, scope) => {
        const results: NoteResolutionInboxApplyResult[] = []
        const seen = new Set<string>()
        let afterServerSequence = 0
        let pages = 0
        while (pages < MAX_ORPHAN_RETRY_PAGES) {
          const items = await listOrphans(localAccountId, deviceId, scope.canonicalUserId, limit, afterServerSequence)
          pages += 1
          let previousSequence = afterServerSequence
          for (const item of items) {
            if (item.server_sequence <= previousSequence || seen.has(item.event_id)) {
              for (const pending of items) clearEnvelope(pending)
              throw new NoteResolutionInboxApplyError('invalid_inbox_scope')
            }
            previousSequence = item.server_sequence
            seen.add(item.event_id)
          }
          for (const item of items) results.push(await this.applyItem(masterKey, scope, item))
          if (items.length === 0 || items.length < limit) break
          afterServerSequence = previousSequence
        }
        return results
      })
    } catch (error) {
      throw topLevelError(error)
    }
  }
}
