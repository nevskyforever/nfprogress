import type { ObjectCryptoEnvelope } from '@/crypto'
import type { SyncEventEnvelope } from '@/cloud/syncProtocol'
import { parseSyncTimestamp } from '@/cloud/syncTimestamp'
import { decodeBase64Url, encodeBase64Url } from './base64url'
import { apiRequest } from './client'

export const ENCRYPTED_SYNC_VERSION = 1 as const
export const MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES = 8_388_624
export const MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES = 16_777_216
export const MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES = 33_554_432

export interface EncryptedSyncPushItem {
  event: SyncEventEnvelope
  object: ObjectCryptoEnvelope
}

export interface EncryptedSyncPushRequest {
  protocol_version: 1
  encrypted_sync_version: typeof ENCRYPTED_SYNC_VERSION
  device_id: string
  items: EncryptedSyncPushItem[]
}

export interface EncryptedSyncPullEvent extends SyncEventEnvelope {
  device_id: string
  server_sequence: number
}

export interface EncryptedSyncPullItem {
  event: EncryptedSyncPullEvent
  object: ObjectCryptoEnvelope | null
}

export interface EncryptedSyncPushResponse {
  protocol_version: 1
  encrypted_sync_version: typeof ENCRYPTED_SYNC_VERSION
  results: Array<{ event_id: string; server_sequence: number; duplicate: boolean }>
  current_cursor: number
}

export interface EncryptedSyncPullResponse {
  protocol_version: 1
  encrypted_sync_version: typeof ENCRYPTED_SYNC_VERSION
  items: EncryptedSyncPullItem[]
  next_cursor: number
  has_more: boolean
}

interface WireObjectEnvelope {
  crypto_version: number
  aad_version: number
  nonce: string
  ciphertext: string
}

interface WirePullResponse extends Omit<EncryptedSyncPullResponse, 'items'> {
  items: Array<{ event: EncryptedSyncPullEvent; object: WireObjectEnvelope | null }>
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const C9_EVENT_KEYS = [
  'event_id', 'project_id', 'entity_id', 'entity_type', 'operation', 'revision', 'updated_at', 'deleted_at',
] as const

function canonicalUuid(value: string): string {
  if (typeof value !== 'string' || !UUID.test(value)) throw new TypeError('Invalid encrypted sync UUID.')
  return value.toLowerCase()
}

function invalidEnvelope(): never {
  throw new TypeError('Invalid encrypted sync envelope.')
}

function eventToWire(event: SyncEventEnvelope): SyncEventEnvelope {
  if (typeof event !== 'object' || event === null || Object.keys(event).length !== C9_EVENT_KEYS.length
    || !C9_EVENT_KEYS.every(key => Object.prototype.hasOwnProperty.call(event, key))) invalidEnvelope()
  return {
    event_id: canonicalUuid(event.event_id),
    project_id: event.project_id,
    entity_id: event.entity_id,
    entity_type: event.entity_type,
    operation: event.operation,
    revision: event.revision,
    updated_at: event.updated_at,
    deleted_at: event.deleted_at,
  }
}

function validateObject(envelope: ObjectCryptoEnvelope): void {
  if (typeof envelope !== 'object' || envelope === null || envelope.crypto_version !== 1 || envelope.aad_version !== 1
    || Object.prototype.toString.call(envelope.nonce) !== '[object Uint8Array]' || envelope.nonce.byteLength !== 24
    || Object.prototype.toString.call(envelope.ciphertext) !== '[object Uint8Array]' || envelope.ciphertext.byteLength < 16
    || envelope.ciphertext.byteLength > MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES) invalidEnvelope()
}

export function assertEncryptedSyncBatch(items: readonly EncryptedSyncPushItem[]): void {
  let total = 0
  for (const item of items) {
    validateObject(item.object)
    total += item.object.ciphertext.byteLength
    if (total > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES) {
      throw new RangeError('Encrypted sync batch exceeds ciphertext size limit.')
    }
  }
}

function objectToWire(envelope: ObjectCryptoEnvelope): WireObjectEnvelope {
  validateObject(envelope)
  return {
    crypto_version: envelope.crypto_version,
    aad_version: envelope.aad_version,
    nonce: encodeBase64Url(envelope.nonce),
    ciphertext: encodeBase64Url(envelope.ciphertext),
  }
}

export function encryptedSyncObjectFromWire(value: WireObjectEnvelope): ObjectCryptoEnvelope {
  if (typeof value !== 'object' || value === null || value.crypto_version !== 1 || value.aad_version !== 1) invalidEnvelope()
  const nonce = decodeBase64Url(value.nonce, { expectedLength: 24 })
  const ciphertext = decodeBase64Url(value.ciphertext, {
    minimumLength: 16,
    maximumLength: MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
  })
  return { crypto_version: 1, aad_version: 1, nonce, ciphertext }
}

function authorization(accessToken: string): Headers {
  const headers = new Headers({ Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' })
  return headers
}

function encodePushBody(request: EncryptedSyncPushRequest): string {
  assertEncryptedSyncBatch(request.items)
  const body = JSON.stringify({
    protocol_version: request.protocol_version,
    encrypted_sync_version: request.encrypted_sync_version,
    device_id: canonicalUuid(request.device_id),
    items: request.items.map(item => ({
      event: eventToWire(item.event),
      object: objectToWire(item.object),
    })),
  })
  if (new TextEncoder().encode(body).byteLength > MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES) {
    throw new RangeError('Encrypted sync request exceeds wire size limit.')
  }
  return body
}

export function encryptedSyncPushBodyBytes(request: EncryptedSyncPushRequest): number {
  return new TextEncoder().encode(encodePushBody(request)).byteLength
}

function parsePushResponse(response: EncryptedSyncPushResponse): EncryptedSyncPushResponse {
  if (typeof response !== 'object' || response === null || response.protocol_version !== 1
    || response.encrypted_sync_version !== 1 || !Array.isArray(response.results)
    || !Number.isSafeInteger(response.current_cursor) || response.current_cursor < 0) invalidEnvelope()
  const results = response.results.map(result => {
    if (typeof result !== 'object' || result === null || Object.keys(result).length !== 3
      || !canonicalUuid(result.event_id) || !Number.isSafeInteger(result.server_sequence)
      || result.server_sequence < 1 || typeof result.duplicate !== 'boolean') invalidEnvelope()
    return { event_id: canonicalUuid(result.event_id), server_sequence: result.server_sequence, duplicate: result.duplicate }
  })
  return { protocol_version: 1, encrypted_sync_version: 1, results, current_cursor: response.current_cursor }
}

function exactKeys(value: object, keys: readonly string[]): boolean {
  const actual = Object.keys(value)
  return actual.length === keys.length && keys.every(key => Object.prototype.hasOwnProperty.call(value, key))
}

function validBoundedText(value: unknown, maximum: number): value is string {
  return typeof value === 'string' && value.length >= 1 && value.length <= maximum
}

function parsePullEvent(value: unknown): EncryptedSyncPullEvent {
  const eventKeys = [...C9_EVENT_KEYS, 'device_id', 'server_sequence']
  if (typeof value !== 'object' || value === null || !exactKeys(value, eventKeys)) invalidEnvelope()
  const event = value as EncryptedSyncPullEvent
  if (!validBoundedText(event.event_id, 36) || !validBoundedText(event.device_id, 36)
    || !validBoundedText(event.project_id, 512) || !validBoundedText(event.entity_id, 512)
    || !validBoundedText(event.entity_type, 128) || !/^[a-z][a-z0-9_:-]*$/.test(event.entity_type)
    || !(['upsert', 'delete', 'event'] as readonly string[]).includes(event.operation)
    || !Number.isSafeInteger(event.revision) || event.revision < 1
    || !Number.isSafeInteger(event.server_sequence) || event.server_sequence < 1
    || typeof event.updated_at !== 'string' || !(event.deleted_at === null || typeof event.deleted_at === 'string')) invalidEnvelope()
  try {
    canonicalUuid(event.event_id)
    canonicalUuid(event.device_id)
    parseSyncTimestamp(event.updated_at)
    if (event.deleted_at !== null) parseSyncTimestamp(event.deleted_at)
  } catch {
    invalidEnvelope()
  }
  if ((event.operation === 'delete') !== (event.deleted_at !== null)) invalidEnvelope()
  return event
}

function parsePullResponse(response: unknown, since: number, limit: number): EncryptedSyncPullResponse {
  if (typeof response !== 'object' || response === null
    || !exactKeys(response, ['protocol_version', 'encrypted_sync_version', 'items', 'next_cursor', 'has_more'])) invalidEnvelope()
  const wire = response as WirePullResponse
  if (wire.protocol_version !== 1 || wire.encrypted_sync_version !== 1 || !Array.isArray(wire.items)
    || wire.items.length > limit || !Number.isSafeInteger(wire.next_cursor) || wire.next_cursor < 0
    || typeof wire.has_more !== 'boolean') invalidEnvelope()
  let aggregate = 0
  let previousSequence = since
  const eventIds = new Set<string>()
  const sequences = new Set<number>()
  const items = wire.items.map(item => {
    if (typeof item !== 'object' || item === null || !exactKeys(item, ['event', 'object'])) invalidEnvelope()
    const event = parsePullEvent(item.event)
    const eventId = event.event_id.toLowerCase()
    if (event.server_sequence <= since || event.server_sequence <= previousSequence
      || eventIds.has(eventId) || sequences.has(event.server_sequence)) invalidEnvelope()
    eventIds.add(eventId)
    sequences.add(event.server_sequence)
    previousSequence = event.server_sequence
    const object = item.object === null ? null : encryptedSyncObjectFromWire(item.object)
    if (event.entity_type === 'note' && object === null) invalidEnvelope()
    aggregate += object?.ciphertext.byteLength ?? 0
    if (aggregate > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES) invalidEnvelope()
    return { event, object }
  })
  if (items.length === 0) {
    if (wire.next_cursor !== since || wire.has_more) invalidEnvelope()
  } else if (wire.next_cursor !== previousSequence) invalidEnvelope()
  return { protocol_version: 1, encrypted_sync_version: 1, items, next_cursor: wire.next_cursor, has_more: wire.has_more }
}

export const encryptedSyncApi = {
  push(accessToken: string, request: EncryptedSyncPushRequest): Promise<EncryptedSyncPushResponse> {
    const body = encodePushBody(request)
    return apiRequest<EncryptedSyncPushResponse>('/api/v1/sync/encrypted/push', {
      method: 'POST', headers: authorization(accessToken), rawBody: body,
    }).then(parsePushResponse)
  },
  async pull(accessToken: string, deviceId: string, since: number, limit = 200): Promise<EncryptedSyncPullResponse> {
    if (!Number.isSafeInteger(since) || since < 0 || !Number.isSafeInteger(limit) || limit < 1 || limit > 200) {
      throw new RangeError('Invalid encrypted sync pagination.')
    }
    const query = new URLSearchParams({
      device_id: canonicalUuid(deviceId),
      since: String(since),
      limit: String(limit),
      protocol_version: '1',
      encrypted_sync_version: '1',
    })
    const response = await apiRequest<WirePullResponse>(`/api/v1/sync/encrypted/pull?${query}`, {
      headers: authorization(accessToken),
      maxResponseBytes: MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES,
    })
    return parsePullResponse(response, since, limit)
  },
}
