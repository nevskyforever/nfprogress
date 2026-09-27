import { invoke } from '@tauri-apps/api/core'
import { decodeBase64Url, encodeBase64Url } from '@/api/base64url'
import { AAD_VERSION, CRYPTO_VERSION, type ObjectCryptoEnvelope } from '@/crypto'
import type { ValidatedEncryptedPullBatch } from '@/cloud/noteSyncPull'

export interface NoteSyncPullState { pull_cursor: number; ack_cursor: number }
export interface CommitInboundPageResult { committed_cursor: number; new_events: number; replayed_events: number; has_more: boolean }
interface ReceivedNoteSyncInboxItemBase {
  event_id: string
  server_sequence: number
  source_device_id: string
  project_id: string
  entity_id: string
  entity_type: 'note'
  revision: number
  updated_at: string
  deleted_at: string | null
  envelope: ObjectCryptoEnvelope
}

export interface ReceivedNoteSyncV1InboxItem extends ReceivedNoteSyncInboxItemBase {
  operation: 'upsert' | 'delete'
}

export interface ReceivedNoteResolutionInboxItem extends ReceivedNoteSyncInboxItemBase {
  operation: 'resolution'
}

export type ReceivedNoteSyncInboxItem = ReceivedNoteSyncV1InboxItem | ReceivedNoteResolutionInboxItem
export type OrphanNoteResolutionInboxItem = ReceivedNoteResolutionInboxItem
export type ReceivedNoteSyncInboxPageKind = 'v1' | 'resolution'

interface NoteSyncInboxWireItem {
  event_id: string
  server_sequence: number
  source_device_id: string
  project_id: string
  entity_id: string
  entity_type: string
  operation: string
  revision: number
  updated_at: string
  deleted_at: string | null
  envelope: { crypto_version: number, aad_version: number, nonce: string, ciphertext: string }
}

export interface NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState>
  listReceived(accountId: string, deviceId: string, canonicalUserId: string, limit: number): Promise<ReceivedNoteSyncInboxItem[]>
  listReceivedPage?: {
    (accountId: string, deviceId: string, canonicalUserId: string, kind: 'v1', limit: number, afterServerSequence: number): Promise<ReceivedNoteSyncV1InboxItem[]>
    (accountId: string, deviceId: string, canonicalUserId: string, kind: 'resolution', limit: number, afterServerSequence: number): Promise<ReceivedNoteResolutionInboxItem[]>
  }
  listOrphanResolutions?(accountId: string, deviceId: string, canonicalUserId: string, limit: number, afterServerSequence: number): Promise<OrphanNoteResolutionInboxItem[]>
  commitInboundPage(batch: ValidatedEncryptedPullBatch, canonicalUserId: string): Promise<CommitInboundPageResult>
}

function decodeVerifiedEnvelope(envelope: NoteSyncInboxWireItem['envelope']): ObjectCryptoEnvelope {
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

function decodeReceivedItem(item: NoteSyncInboxWireItem): ReceivedNoteSyncInboxItem {
  if (item.entity_type !== 'note') throw new TypeError('Native inbox reader returned a non-Note event.')
  const common = {
    event_id: item.event_id,
    server_sequence: item.server_sequence,
    source_device_id: item.source_device_id,
    project_id: item.project_id,
    entity_id: item.entity_id,
    entity_type: 'note' as const,
    revision: item.revision,
    updated_at: item.updated_at,
    deleted_at: item.deleted_at,
    envelope: decodeVerifiedEnvelope(item.envelope),
  }
  if (item.operation === 'upsert' || item.operation === 'delete') return { ...common, operation: item.operation }
  if (item.operation === 'resolution') return { ...common, operation: 'resolution' }
  throw new TypeError('Native inbox reader returned an unsupported Note operation.')
}

export class SQLiteNoteSyncInboxRepository implements NoteSyncInboxRepository {
  readPullState(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncPullState> {
    return invoke('read_note_sync_pull_state', { command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId } })
  }

  async listReceived(accountId: string, deviceId: string, canonicalUserId: string, limit: number): Promise<ReceivedNoteSyncInboxItem[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32) throw new RangeError('Invalid received Note inbox list limit.')
    const items = await invoke<NoteSyncInboxWireItem[]>('list_received_note_sync_inbox', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId, limit },
    })
    return items.map(decodeReceivedItem)
  }

  async listReceivedPage(accountId: string, deviceId: string, canonicalUserId: string, kind: 'v1', limit: number, afterServerSequence: number): Promise<ReceivedNoteSyncV1InboxItem[]>
  async listReceivedPage(accountId: string, deviceId: string, canonicalUserId: string, kind: 'resolution', limit: number, afterServerSequence: number): Promise<ReceivedNoteResolutionInboxItem[]>
  async listReceivedPage(accountId: string, deviceId: string, canonicalUserId: string, kind: ReceivedNoteSyncInboxPageKind, limit: number, afterServerSequence: number): Promise<ReceivedNoteSyncInboxItem[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32) throw new RangeError('Invalid received Note inbox page limit.')
    if (!Number.isSafeInteger(afterServerSequence) || afterServerSequence < 0) throw new RangeError('Invalid received Note inbox page cursor.')
    const items = await invoke<NoteSyncInboxWireItem[]>('list_received_note_sync_inbox_page', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId, kind, limit, after_server_sequence: afterServerSequence },
    })
    if (kind === 'v1') {
      return items.map(item => {
        const decoded = decodeReceivedItem(item)
        if (decoded.operation === 'resolution') throw new TypeError('Native v1 inbox page returned a resolution.')
        return decoded
      })
    }
    return items.map(item => {
      const decoded = decodeReceivedItem(item)
      if (decoded.operation !== 'resolution') throw new TypeError('Native resolution inbox page returned a v1 event.')
      return decoded
    })
  }

  async listOrphanResolutions(accountId: string, deviceId: string, canonicalUserId: string, limit: number, afterServerSequence: number): Promise<OrphanNoteResolutionInboxItem[]> {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 32) throw new RangeError('Invalid orphan resolution inbox list limit.')
    if (!Number.isSafeInteger(afterServerSequence) || afterServerSequence < 0) throw new RangeError('Invalid orphan resolution inbox cursor.')
    const items = await invoke<NoteSyncInboxWireItem[]>('list_orphan_note_resolution_inbox', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId, limit, after_server_sequence: afterServerSequence },
    })
    return items.map(item => {
      if (item.operation !== 'resolution') throw new TypeError('Native orphan inbox reader returned a non-resolution event.')
      const decoded = decodeReceivedItem(item)
      if (decoded.operation !== 'resolution') throw new TypeError('Native orphan inbox reader returned a non-resolution event.')
      return decoded
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
