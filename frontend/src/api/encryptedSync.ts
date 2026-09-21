import type { ObjectCryptoEnvelope } from '@/crypto'
import type { SyncEventEnvelope } from '@/cloud/syncProtocol'
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

function canonicalUuid(value: string): string {
  if (typeof value !== 'string' || !UUID.test(value)) throw new TypeError('Invalid encrypted sync UUID.')
  return value.toLowerCase()
}

function invalidEnvelope(): never {
  throw new TypeError('Invalid encrypted sync envelope.')
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
      event: { ...item.event, event_id: canonicalUuid(item.event.event_id) },
      object: objectToWire(item.object),
    })),
  })
  if (new TextEncoder().encode(body).byteLength > MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES) {
    throw new RangeError('Encrypted sync request exceeds wire size limit.')
  }
  return body
}

function parsePullResponse(response: WirePullResponse): EncryptedSyncPullResponse {
  if (response.protocol_version !== 1 || response.encrypted_sync_version !== 1 || !Array.isArray(response.items)) invalidEnvelope()
  let aggregate = 0
  const items = response.items.map(item => {
    if (typeof item !== 'object' || item === null || typeof item.event !== 'object' || item.event === null) invalidEnvelope()
    const object = item.object === null ? null : encryptedSyncObjectFromWire(item.object)
    aggregate += object?.ciphertext.byteLength ?? 0
    if (aggregate > MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES) invalidEnvelope()
    return { event: item.event, object }
  })
  return { ...response, items }
}

export const encryptedSyncApi = {
  push(accessToken: string, request: EncryptedSyncPushRequest): Promise<EncryptedSyncPushResponse> {
    return apiRequest('/api/v1/sync/encrypted/push', {
      method: 'POST', headers: authorization(accessToken), rawBody: encodePushBody(request),
    })
  },
  async pull(accessToken: string, deviceId: string, since: number, limit = 200): Promise<EncryptedSyncPullResponse> {
    if (!Number.isSafeInteger(since) || since < 0 || !Number.isSafeInteger(limit) || limit < 1 || limit > 500) {
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
    })
    return parsePullResponse(response)
  },
}
