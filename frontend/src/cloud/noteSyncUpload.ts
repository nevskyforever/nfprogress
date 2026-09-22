import { encryptedSyncApi, encryptedSyncObjectFromWire, encryptedSyncPushBodyBytes, ENCRYPTED_SYNC_VERSION, MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES, type EncryptedSyncPushItem } from '@/api/encryptedSync'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { NoteSyncOutboxRepository, NoteSyncUploadReceipt, SealedNoteSyncOutboxItem } from './noteSyncOutbox'

const MAX_UPLOAD_EVENTS = 100
const SEALED_READ_LIMIT = 200

export class NoteSyncUploadError extends Error {
  readonly name = 'NoteSyncUploadError'
  constructor(readonly code: 'malformed_acknowledgement' | 'no_uploadable_events', message: string) { super(message) }
}

function eventFrom(item: SealedNoteSyncOutboxItem) {
  return {
    event_id: item.event_id, project_id: item.project_id, entity_id: item.entity_id,
    entity_type: item.entity_type, operation: item.operation, revision: item.revision,
    updated_at: item.updated_at, deleted_at: item.deleted_at,
  } as const
}

function requestFor(deviceId: string, items: readonly SealedNoteSyncOutboxItem[]): { protocol_version: 1, encrypted_sync_version: 1, device_id: string, items: EncryptedSyncPushItem[] } {
  return {
    protocol_version: 1,
    encrypted_sync_version: ENCRYPTED_SYNC_VERSION,
    device_id: deviceId,
    items: items.map(item => ({ event: eventFrom(item), object: encryptedSyncObjectFromWire(item.envelope) })),
  }
}

function batchFrom(items: readonly SealedNoteSyncOutboxItem[]): SealedNoteSyncOutboxItem[] {
  const first = items[0]
  if (!first) return []
  const deviceId = first.device_id
  const visible = new Map(items.map(item => [item.event_id, item]))
  const selected: SealedNoteSyncOutboxItem[] = []
  const selectedIds = new Set<string>()
  for (const item of items) {
    if (item.device_id !== deviceId || selected.length === MAX_UPLOAD_EVENTS) continue
    // A listed sealed parent must be emitted before its child. A parent absent
    // from this sealed-only view was already accepted by the SQLite reader.
    if (item.parent_event_id && visible.has(item.parent_event_id) && !selectedIds.has(item.parent_event_id)) continue
    const candidate = [...selected, item]
    if (encryptedSyncPushBodyBytes(requestFor(deviceId, candidate)) > MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES) break
    selected.push(item)
    selectedIds.add(item.event_id)
  }
  return selected
}

function receiptsFor(batch: readonly SealedNoteSyncOutboxItem[], response: Awaited<ReturnType<typeof encryptedSyncApi.push>>): NoteSyncUploadReceipt[] {
  const expected = new Set(batch.map(item => item.event_id.toLowerCase()))
  if (response.results.length !== expected.size) throw new NoteSyncUploadError('malformed_acknowledgement', 'Encrypted sync acknowledgement is incomplete.')
  const receipts: NoteSyncUploadReceipt[] = []
  for (const result of response.results) {
    const id = result.event_id.toLowerCase()
    if (!expected.delete(id)) throw new NoteSyncUploadError('malformed_acknowledgement', 'Encrypted sync acknowledgement has an unexpected event.')
    if (response.current_cursor < result.server_sequence) {
      throw new NoteSyncUploadError('malformed_acknowledgement', 'Encrypted sync acknowledgement cursor is inconsistent.')
    }
    receipts.push(result)
  }
  if (expected.size !== 0) throw new NoteSyncUploadError('malformed_acknowledgement', 'Encrypted sync acknowledgement is incomplete.')
  return receipts
}

/** Runs one manually-triggered, bounded durable upload pass. It never seals or re-encrypts Notes. */
export class NoteSyncUploader {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly outbox: NoteSyncOutboxRepository,
  ) {}

  async uploadOnce(localAccountId: string): Promise<{ uploaded: number, deviceId: string | null }> {
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    const listed = await this.outbox.listSealed(localAccountId, SEALED_READ_LIMIT)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    if (listed.some(item => item.account_id !== localAccountId)) throw new NoteSyncUploadError('malformed_acknowledgement', 'Sealed outbox account scope is inconsistent.')
    const batch = batchFrom(listed)
    if (batch.length === 0) return { uploaded: 0, deviceId: null }
    const deviceId = batch[0]!.device_id
    const request = requestFor(deviceId, batch)
    const pushed = await this.auth.authorized(accessToken => encryptedSyncApi.push(accessToken, request))
    if (pushed.context.userId !== binding.context.userId || !this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const receipts = receiptsFor(batch, pushed.value)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    await this.outbox.commitAccepted(localAccountId, deviceId, receipts)
    return { uploaded: batch.length, deviceId }
  }
}
