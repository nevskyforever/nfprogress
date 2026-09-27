import type { RuntimeKeyContext } from '@/auth/keyContext'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { NoteSyncInboxRepository, ReceivedNoteSyncInboxItem, ReceivedNoteSyncV1InboxItem } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type {
  NoteSyncRemoteApplyRepository,
  NoteSyncRemoteApplyStatus,
} from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { encodeNoteSyncPlaintext, type NoteSyncPlaintext } from './noteSyncCodec'
import {
  NoteInboxDecryptError,
  type NoteInboxDecryptErrorCode,
  withDecryptedReceivedNoteInbox,
  withDecryptedReceivedNoteInboxPage,
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

export interface NoteInboxApplyPageResult extends NoteInboxApplyPassResult {
  readonly lastServerSequence: number
  readonly errorCount: number
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

  private async dispatch(
    item: ReceivedNoteSyncV1InboxItem,
    plaintext: NoteSyncPlaintext,
    scope: { readonly accountId: string; readonly canonicalUserId: string; readonly pullingDeviceId: string },
  ): Promise<{ status: NoteSyncRemoteApplyStatus | 'error', error_code?: NoteInboxDecryptErrorCode }> {
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
      return { status: 'error', error_code: 'runtime_unavailable' }
    } finally {
      plaintextBytes.fill(0)
      wirePlaintext.fill(0)
      nonce.fill(0)
      ciphertext.fill(0)
    }
  }

  private results(values: Array<{
    event: ReceivedNoteSyncInboxItem
    value?: { status: NoteSyncRemoteApplyStatus | 'error', error_code?: NoteInboxDecryptErrorCode }
    error_code?: NoteInboxDecryptErrorCode
  }>): NoteInboxApplyResult[] {
    return values.map(value => value.error_code
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
        })
  }

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
        (item, plaintext, scope) => this.dispatch(item, plaintext, scope),
      )
      return {
        listed: values.length,
        results: this.results(values),
      }
    } catch (error) {
      if (error instanceof StaleAuthContextError) throw error
      if (error instanceof NoteInboxDecryptError) throw error
      throw new NoteInboxDecryptError('runtime_unavailable')
    }
  }


  async applyPage(localAccountId: string, deviceId: string, limit = 8, afterServerSequence = 0): Promise<NoteInboxApplyPageResult> {
    try {
      const values = await withDecryptedReceivedNoteInboxPage(
        this.auth,
        this.bindings,
        this.keyContext,
        this.inbox,
        localAccountId,
        deviceId,
        limit,
        afterServerSequence,
        (item, plaintext, scope) => this.dispatch(item, plaintext, scope),
      )
      const results = this.results(values)
      return {
        listed: values.length,
        lastServerSequence: values.at(-1)?.event.server_sequence ?? afterServerSequence,
        errorCount: results.filter(result => result.status === 'error').length,
        results,
      }
    } catch (error) {
      if (error instanceof StaleAuthContextError) throw error
      if (error instanceof NoteInboxDecryptError) throw error
      throw new NoteInboxDecryptError('runtime_unavailable')
    }
  }
}
