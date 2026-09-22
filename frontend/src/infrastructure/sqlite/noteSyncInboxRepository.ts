import { invoke } from '@tauri-apps/api/core'
import { encodeBase64Url } from '@/api/base64url'
import type { ValidatedEncryptedPullBatch } from '@/cloud/noteSyncPull'

export interface NoteSyncPullState { pull_cursor: number; ack_cursor: number }
export interface CommitInboundPageResult { committed_cursor: number; new_events: number; replayed_events: number; has_more: boolean }

export interface NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState>
  commitInboundPage(batch: ValidatedEncryptedPullBatch, canonicalUserId: string): Promise<CommitInboundPageResult>
}

export class SQLiteNoteSyncInboxRepository implements NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState> {
    return invoke('read_note_sync_pull_state', { command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId } })
  }

  commitInboundPage(batch: ValidatedEncryptedPullBatch, canonicalUserId: string): Promise<CommitInboundPageResult> {
    return invoke('commit_note_sync_inbound_page', {
      command: {
        account_id: batch.accountId, device_id: batch.deviceId, canonical_user_id: canonicalUserId,
        expected_cursor: batch.since, next_cursor: batch.nextCursor, has_more: batch.hasMore,
        items: batch.items.map(({ event, object }) => ({
          event_id: event.event_id, server_sequence: event.server_sequence, source_device_id: event.device_id,
          project_id: event.project_id, entity_id: event.entity_id, entity_type: event.entity_type,
          operation: event.operation, revision: event.revision, updated_at: event.updated_at, deleted_at: event.deleted_at,
          envelope: object === null ? null : {
            crypto_version: object.crypto_version, aad_version: object.aad_version,
            nonce: encodeBase64Url(object.nonce), ciphertext: encodeBase64Url(object.ciphertext),
          },
        })),
      },
    })
  }
}
