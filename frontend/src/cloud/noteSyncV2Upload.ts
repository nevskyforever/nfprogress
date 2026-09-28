import { ApiError } from '@/api/client'
import { encodeV2Push, encryptedSyncV2Api, parseV2Capabilities, parseV2PushResponse, validateV2PushItem, type V2PushItem, type V2PushRequest } from '@/api/encryptedSyncV2'
import { MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES, MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES } from '@/api/encryptedSync'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { NoteSyncOutboxRepository, NoteSyncUploadFailureCode, SealedNoteSyncOutboxItem } from './noteSyncOutbox'

const READ_LIMIT = 200
const MAX_EVENTS = 100
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

export class NoteSyncV2UploadError extends Error {
  constructor(readonly code: 'mode_incompatible' | 'malformed_receipt' | 'wire_limit' | 'local_acceptance_failed', message: string) { super(message) }
}

function wireItem(item: SealedNoteSyncOutboxItem): V2PushItem {
  const base = { event_id: item.event_id, project_id: item.project_id, entity_id: item.entity_id,
    entity_type: item.entity_type, revision: item.revision, updated_at: item.updated_at }
  const event = item.operation === 'delete'
    ? { ...base, operation: 'delete' as const, deleted_at: item.deleted_at as string }
    : { ...base, operation: 'upsert' as const, deleted_at: item.deleted_at as null }
  return { event, object: item.envelope }
}

function request(deviceId: string, items: readonly SealedNoteSyncOutboxItem[]): V2PushRequest {
  return { protocol_version: 2, encrypted_sync_version: 2, device_id: deviceId, items: items.map(wireItem) }
}

function batchFrom(deviceId: string, items: readonly SealedNoteSyncOutboxItem[]): SealedNoteSyncOutboxItem[] {
  const visible = new Set(items.map(item => item.event_id))
  const selectedIds = new Set<string>()
  const selected: SealedNoteSyncOutboxItem[] = []
  let ciphertextBytes = 0
  for (const item of items) {
    if (selected.length === MAX_EVENTS) break
    if (item.parent_event_id && visible.has(item.parent_event_id) && !selectedIds.has(item.parent_event_id)) continue
    const validated = validateV2PushItem(wireItem(item))
    if (selectedIds.has(validated.eventId)) throw new TypeError('Duplicate sealed Note event.')
    const candidate = [...selected, item]
    if (ciphertextBytes + validated.ciphertextBytes > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES
      || new TextEncoder().encode(JSON.stringify(request(deviceId, candidate))).byteLength > MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES) {
      if (!selected.length) throw new NoteSyncV2UploadError('wire_limit', 'Sealed Note exceeds transport limits.')
      break
    }
    selected.push(item)
    selectedIds.add(validated.eventId)
    ciphertextBytes += validated.ciphertextBytes
  }
  return selected
}

function same(a: SealedNoteSyncOutboxItem, b: SealedNoteSyncOutboxItem): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

function failureCode(error: unknown): NoteSyncUploadFailureCode | null {
  if (error instanceof StaleAuthContextError || error instanceof NoteSyncV2UploadError && error.code === 'mode_incompatible') return null
  if (error instanceof NoteSyncV2UploadError && error.code === 'malformed_receipt') return 'malformed_receipt'
  if (error instanceof NoteSyncV2UploadError && error.code === 'local_acceptance_failed') return 'local_acceptance_failed'
  if (error instanceof ApiError) {
    if (error.code === 'sync_transport_mode_incompatible') return null
    if (error.status === 0) return 'network_unavailable'
    if (error.status === 429) return 'rate_limited'
    if (error.status >= 500) return 'http_5xx'
    if (error.status === 401) return 'unauthorized'
    if (error.code === 'sync_device_not_registered') return 'device_not_registered'
    if (error.code === 'cloud_project_not_enabled') return 'cloud_project_disabled'
    if (error.code === 'sync_event_id_conflict') return 'conflicting_event'
    return 'invalid_protocol'
  }
  if (error instanceof DOMException && error.name === 'AbortError') return 'request_timeout'
  if (error instanceof Error && /timeout/i.test(error.message)) return 'request_timeout'
  return 'network_unavailable'
}

/** Ordinary mode-2 Note upload using the existing sealed outbox and native receipt transaction. */
export class NoteSyncV2Uploader {
  private static readonly flights = new Map<string, Promise<{ uploaded: number, deviceId: string | null }>>()
  constructor(private readonly auth: NormalUserAuthRuntime, private readonly bindings: AuthoritativeAccountBinding,
    private readonly identity: CloudIdentityRepository, private readonly outbox: NoteSyncOutboxRepository,
    private readonly api: Pick<typeof encryptedSyncV2Api, 'capabilities' | 'push'> = encryptedSyncV2Api) {}

  async uploadOnce(accountId: string): Promise<{ uploaded: number, deviceId: string | null }> {
    const binding = await this.bindings.ensureForCurrentUser(accountId)
    const context = binding.context
    if (!UUID.test(context.userId)) throw new StaleAuthContextError()
    const identity = await this.identity.read(context.userId)
    if (!identity || identity.local_account_id !== accountId || !UUID.test(identity.device_id) || !this.auth.isCurrent(context)) throw new StaleAuthContextError()
    const deviceId = identity.device_id
    const key = `${accountId}\0${context.userId}\0${deviceId}\0${context.authEpoch}`
    const existing = NoteSyncV2Uploader.flights.get(key)
    if (existing) return existing
    const flight = this.run(accountId, deviceId, context)
    NoteSyncV2Uploader.flights.set(key, flight)
    try { return await flight } finally { if (NoteSyncV2Uploader.flights.get(key) === flight) NoteSyncV2Uploader.flights.delete(key) }
  }

  private async run(accountId: string, deviceId: string, context: AuthContextSnapshot): Promise<{ uploaded: number, deviceId: string | null }> {
    const listed = await this.outbox.listSealed(accountId, READ_LIMIT)
    this.assertCurrent(context)
    this.assertScope(listed, accountId, deviceId)
    const batch = batchFrom(deviceId, listed)
    if (!batch.length) return { uploaded: 0, deviceId: null }
    const capabilities = await this.auth.authorized(token => this.api.capabilities(token))
    this.assertCurrent(context, capabilities.context)
    if (parseV2Capabilities(capabilities.value).writer_transport_version !== 2) throw new NoteSyncV2UploadError('mode_incompatible', 'Writer transport mode is not 2.')
    const fresh = await this.outbox.listSealed(accountId, READ_LIMIT)
    this.assertCurrent(context)
    this.assertScope(fresh, accountId, deviceId)
    const freshBatch = batchFrom(deviceId, fresh)
    if (freshBatch.length !== batch.length || batch.some((item, index) => !same(item, freshBatch[index]!))) throw new StaleAuthContextError()
    try {
      const payload = request(deviceId, batch)
      encodeV2Push(payload)
      const pushed = await this.auth.authorized(token => this.api.push(token, payload))
      this.assertCurrent(context, pushed.context)
      let response: ReturnType<typeof parseV2PushResponse>
      try { response = parseV2PushResponse(pushed.value, batch.map(item => item.event_id)) }
      catch { throw new NoteSyncV2UploadError('malformed_receipt', 'Invalid encrypted sync v2 receipt.') }
      this.assertCurrent(context)
      // The native transaction is scoped to this exact account and device after it starts.
      let accepted: Awaited<ReturnType<NoteSyncOutboxRepository['commitAccepted']>>
      try { accepted = await this.outbox.commitAccepted(accountId, deviceId, response.results) }
      catch { throw new NoteSyncV2UploadError('local_acceptance_failed', 'Native Note acceptance failed.') }
      if (!Array.isArray(accepted) || accepted.length !== batch.length || accepted.some(value => value !== 'accepted' && value !== 'already_accepted')) {
        throw new NoteSyncV2UploadError('malformed_receipt', 'Invalid native acceptance result.')
      }
      return { uploaded: batch.length, deviceId }
    } catch (error) {
      if (error instanceof ApiError && error.code === 'sync_transport_mode_incompatible') throw new NoteSyncV2UploadError('mode_incompatible', 'Server transport mode changed.')
      const code = failureCode(error)
      if (code) {
        try { await this.outbox.recordUploadFailure({ account_id: accountId, device_id: deviceId, event_ids: batch.map(item => item.event_id), error_code: code }) }
        catch { /* Preserve the original upload error; sealed rows remain retryable. */ }
      }
      throw error
    }
  }

  private assertCurrent(expected: AuthContextSnapshot, actual?: AuthContextSnapshot): void {
    if (actual && (actual.userId !== expected.userId || actual.authEpoch !== expected.authEpoch) || !this.auth.isCurrent(expected)) throw new StaleAuthContextError()
  }

  private assertScope(items: readonly SealedNoteSyncOutboxItem[], accountId: string, deviceId: string): void {
    if (items.some(item => item.account_id !== accountId || item.device_id !== deviceId)) throw new StaleAuthContextError()
  }
}
