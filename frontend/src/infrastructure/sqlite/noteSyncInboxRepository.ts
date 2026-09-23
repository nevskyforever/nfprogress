import { invoke } from '@tauri-apps/api/core'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import type { ObjectCryptoEnvelope } from '@/crypto'
import type { ValidatedEncryptedPullBatch } from '@/cloud/noteSyncPull'

export interface NoteSyncPullState { pull_cursor: number; ack_cursor: number }
export interface CommitInboundPageResult { committed_cursor: number; new_events: number; replayed_events: number; has_more: boolean }
export interface ReceivedNoteSyncInboxItem {
  event_id: string
  server_sequence: number
  source_device_id: string
  project_id: string
  entity_id: string
  entity_type: 'note'
  operation: 'upsert' | 'delete'
  revision: number
  updated_at: string
  deleted_at: string | null
  envelope: ObjectCryptoEnvelope
}

interface ReceivedNoteSyncInboxWireItem extends Omit<ReceivedNoteSyncInboxItem, 'envelope'> {
  envelope: { crypto_version: number, aad_version: number, nonce: string, ciphertext: string }
}

export interface NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState>
  listReceived(accountId: string, deviceId: string, canonicalUserId: string, limit: number): Promise<ReceivedNoteSyncInboxItem[]>
  commitInboundPage(batch: ValidatedEncryptedPullBatch, canonicalUserId: string): Promise<CommitInboundPageResult>
}

export class SQLiteNoteSyncInboxRepository implements NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState> {
    return invoke('read_note_sync_pull_state', { command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId } })
  }

  async listReceived(accountId: string, deviceId: string, canonicalUserId: string, limit: number): Promise<ReceivedNoteSyncInboxItem[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32) throw new RangeError('Invalid received Note inbox list limit.')
    const items = await invoke<ReceivedNoteSyncInboxWireItem[]>('list_received_note_sync_inbox', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId, limit },
    })
    return items.map(item => ({
      ...item,
      envelope: {
        crypto_version: 1,
        aad_version: 1,
        nonce: decodeBase64Url(item.envelope.nonce, { expectedLength: 24 }),
        ciphertext: decodeBase64Url(item.envelope.ciphertext),
      },
    }))
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
