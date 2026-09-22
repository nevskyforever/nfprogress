import { invoke } from '@tauri-apps/api/core'

import { encodeBase64Url } from '@/api/base64url'
import type {
  CommitSealedNoteSyncEventInput,
  CommitSealedNoteSyncEventResult,
  NoteSyncIntentRepository,
  RecordNoteSyncSealFailureInput,
  RecordNoteSyncSealFailureResult,
  UnsealedNoteSyncIntent,
} from '@/cloud/noteSyncIntent'

const MAX_RUST_INTENT_LIST_LIMIT = 200

export class SQLiteNoteSyncIntentRepository implements NoteSyncIntentRepository {
  list(limit: number, retryBlocked: boolean): Promise<UnsealedNoteSyncIntent[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_RUST_INTENT_LIST_LIMIT) {
      throw new RangeError('Invalid Note sync intent list limit.')
    }
    return invoke<UnsealedNoteSyncIntent[]>('list_unsealed_note_sync_intents', {
      limit,
      retryBlocked,
    })
  }

  recordSealFailure(
    input: RecordNoteSyncSealFailureInput,
  ): Promise<RecordNoteSyncSealFailureResult> {
    return invoke<RecordNoteSyncSealFailureResult>('record_note_sync_seal_failure', {
      command: {
        event_id: input.eventId,
        expected_mutation_generation: input.expectedMutationGeneration,
        error_code: input.errorCode,
      },
    })
  }

  commitSealedEvent(
    input: CommitSealedNoteSyncEventInput,
  ): Promise<CommitSealedNoteSyncEventResult> {
    return invoke<CommitSealedNoteSyncEventResult>('commit_sealed_note_sync_event', {
      command: {
        event_id: input.eventId,
        expected_mutation_generation: input.expectedMutationGeneration,
        envelope: {
          crypto_version: input.envelope.crypto_version,
          aad_version: input.envelope.aad_version,
          nonce: encodeBase64Url(input.envelope.nonce),
          ciphertext: encodeBase64Url(input.envelope.ciphertext),
        },
      },
    })
  }
}
