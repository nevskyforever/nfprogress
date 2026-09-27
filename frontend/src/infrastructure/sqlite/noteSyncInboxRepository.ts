import { invoke } from '@tauri-apps/api/core'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import { AAD_VERSION, CRYPTO_VERSION, type ObjectCryptoEnvelope } from '@/crypto'
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

export interface OrphanNoteResolutionInboxItem extends Omit<ReceivedNoteSyncInboxItem, 'operation'> {
  operation: 'resolution'
}

interface ReceivedNoteSyncInboxWireItem extends Omit<ReceivedNoteSyncInboxItem, 'envelope'> {
  envelope: { crypto_version: number, aad_version: number, nonce: string, ciphertext: string }
}

interface OrphanNoteResolutionInboxWireItem extends Omit<OrphanNoteResolutionInboxItem, 'envelope'> {
  envelope: { crypto_version: number, aad_version: number, nonce: string, ciphertext: string }
}

export interface NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState>
  listReceived(accountId: string, deviceId: string, canonicalUserId: string, limit: number): Promise<ReceivedNoteSyncInboxItem[]>
  listOrphanResolutions?(accountId: string, deviceId: string, canonicalUserId: string, limit: number, afterServerSequence: number): Promise<OrphanNoteResolutionInboxItem[]>
  commitInboundPage(batch: ValidatedEncryptedPullBatch, canonicalUserId: string): Promise<CommitInboundPageResult>
}

function decodeVerifiedEnvelope(envelope: ReceivedNoteSyncInboxWireItem['envelope']): ObjectCryptoEnvelope {
  if (envelope.crypto_version !== CRYPTO_VERSION || envelope.aad_version !== AAD_VERSION) {
    throw new TypeError('Native inbox reader returned an unsupported envelope version.')
  }
  return {
    crypto_version: envelope.crypto_version,
    aad_version: envelope.aad_version,
    nonce: decodeBase64Url(envelope.nonce, { expectedLength: 24 }),
    ciphertext: decodeBase64Url(envelope.ciphertext),
  }
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
      envelope: decodeVerifiedEnvelope(item.envelope),
    }))
  }

  async listOrphanResolutions(accountId: string, deviceId: string, canonicalUserId: string, limit: number, afterServerSequence: number): Promise<OrphanNoteResolutionInboxItem[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32) throw new RangeError('Invalid orphan resolution inbox list limit.')
    if (!Number.isSafeInteger(afterServerSequence) || afterServerSequence < 0) throw new RangeError('Invalid orphan resolution inbox cursor.')
    const items = await invoke<OrphanNoteResolutionInboxWireItem[]>('list_orphan_note_resolution_inbox', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId, limit, after_server_sequence: afterServerSequence },
    })
    return items.map(item => {
      if (item.operation !== 'resolution') throw new TypeError('Native orphan inbox reader returned a non-resolution event.')
      return { ...item, operation: 'resolution', envelope: decodeVerifiedEnvelope(item.envelope) }
    })
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
