import type { RuntimeKeyContext } from '@/auth/keyContext'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { NoteSyncInboxRepository } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type {
  NoteSyncRemoteApplyRepository,
  NoteSyncRemoteApplyStatus,
} from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { encodeNoteSyncPlaintext } from './noteSyncCodec'
import {
  NoteInboxDecryptError,
  type NoteInboxDecryptErrorCode,
  withDecryptedReceivedNoteInbox,
} from './noteSyncInboxDecrypt'

export interface NoteInboxApplyResult {
  readonly event_id: string
  readonly server_sequence: number
  readonly status: NoteSyncRemoteApplyStatus | 'error'
  readonly error_code?: NoteInboxDecryptErrorCode
}

export interface NoteInboxApplyPassResult {
  readonly listed: number
  readonly results: readonly NoteInboxApplyResult[]
}

/**
 * Internal sync orchestration adapter. Plaintext is encoded and handed to the
 * narrow Rust command only inside C15.7A's existing AMK lease callback.
 */
export class NoteSyncInboxRemoteApplier {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly keyContext: RuntimeKeyContext,
    private readonly inbox: NoteSyncInboxRepository,
    private readonly apply: NoteSyncRemoteApplyRepository,
  ) {}

  async applyOnce(localAccountId: string, deviceId: string, limit = 8): Promise<NoteInboxApplyPassResult> {
    try {
      const values = await withDecryptedReceivedNoteInbox(
        this.auth,
        this.bindings,
        this.keyContext,
        this.inbox,
        localAccountId,
        deviceId,
        limit,
        async (item, plaintext, scope) => {
          const plaintextBytes = encodeNoteSyncPlaintext(plaintext)
          const nonce = Array.from(item.envelope.nonce)
          const ciphertext = Array.from(item.envelope.ciphertext)
          const wirePlaintext = Array.from(plaintextBytes)
          try {
            const status = await this.apply.applyVerified({
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
            })
            return { status }
          } catch {
            // Apply/IPC failures are not crypto failures. The durable inbox
            // remains untouched by this adapter and Rust owns classification.
            return { status: 'error' as const, error_code: 'runtime_unavailable' as const }
          } finally {
            plaintextBytes.fill(0)
            wirePlaintext.fill(0)
            nonce.fill(0)
            ciphertext.fill(0)
          }
        },
      )
      return {
        listed: values.length,
        results: values.map(value => value.error_code
          ? {
              event_id: value.event.event_id,
              server_sequence: value.event.server_sequence,
              status: 'error' as const,
              error_code: value.error_code,
            }
          : {
              event_id: value.event.event_id,
              server_sequence: value.event.server_sequence,
              status: value.value!.status,
              ...(value.value!.status === 'error' ? { error_code: value.value!.error_code } : {}),
            }),
      }
    } catch (error) {
      if (error instanceof StaleAuthContextError) throw error
      if (error instanceof NoteInboxDecryptError) throw error
      throw new NoteInboxDecryptError('runtime_unavailable')
    }
  }
}
