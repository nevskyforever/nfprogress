import {
  MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
  type EncryptedSyncPushItem,
} from '@/api/encryptedSync'
import {
  decryptObjectBytes,
  encryptObjectBytes,
  type AccountMasterKey,
  type ObjectCryptoContext,
  type ObjectCryptoEnvelope,
} from '@/crypto'
import type { SyncEventEnvelope } from './syncProtocol'
import {
  decodeNoteSyncPlaintext,
  encodeNoteSyncPlaintext,
  noteSyncEligibility,
  type NoteSyncPlaintext,
  type NoteSyncRecord,
  type NoteSyncTombstone,
} from './noteSyncCodec'
import { canonicalizeSyncTimestamp, syncTimestampsEqual } from './syncTimestamp'

export type EncryptedSyncProtocolErrorCode =
  | 'crypto_context_invalid'
  | 'invalid_sync_metadata'
  | 'invalid_envelope'
  | 'payload_too_large'
  | 'encrypted_sync_object_too_large'
  | 'metadata_mismatch'
  | 'dependency_not_synced'
  | 'unsupported_content_format'
  | 'decrypt_failed'

const ERROR_MESSAGES: Readonly<Record<EncryptedSyncProtocolErrorCode, string>> = {
  crypto_context_invalid: 'Invalid encrypted sync cryptographic context.',
  invalid_sync_metadata: 'Invalid encrypted sync metadata.',
  invalid_envelope: 'Invalid encrypted sync envelope.',
  payload_too_large: 'Encrypted sync plaintext exceeds size limit.',
  encrypted_sync_object_too_large: 'Encrypted sync object exceeds size limit.',
  metadata_mismatch: 'Encrypted sync metadata does not match its transport event.',
  dependency_not_synced: 'The note dependency is not synchronized.',
  unsupported_content_format: 'The note content format is not supported for sync.',
  decrypt_failed: 'Encrypted sync object authentication failed.',
}

export class EncryptedSyncProtocolError extends Error {
  readonly name = 'EncryptedSyncProtocolError'

  constructor(readonly code: EncryptedSyncProtocolErrorCode) {
    super(ERROR_MESSAGES[code])
  }
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const CANONICAL_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const ENTITY_TYPE = /^[a-z][a-z0-9_:-]*$/
const C9_EVENT_KEYS = [
  'event_id', 'project_id', 'entity_id', 'entity_type', 'operation', 'revision', 'updated_at', 'deleted_at',
] as const
const encoder = new TextEncoder()

function protocolError(code: EncryptedSyncProtocolErrorCode): never {
  throw new EncryptedSyncProtocolError(code)
}

function assertExactC9Event(value: SyncEventEnvelope): void {
  if (typeof value !== 'object' || value === null || Object.keys(value).length !== C9_EVENT_KEYS.length
    || !C9_EVENT_KEYS.every(key => Object.prototype.hasOwnProperty.call(value, key))) {
    protocolError('invalid_sync_metadata')
  }
}

export function normalizeSyncUuid(value: string): string {
  if (typeof value !== 'string' || !UUID.test(value)) protocolError('invalid_sync_metadata')
  return value.toLowerCase()
}

function canonicalHeaderUuid(value: string): string {
  if (typeof value !== 'string' || !CANONICAL_UUID.test(value)) protocolError('invalid_sync_metadata')
  return value
}

function validContextString(value: string, maximumBytes: number): boolean {
  if (typeof value !== 'string' || value.length === 0) return false
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1)
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false
      index += 1
    } else if (code >= 0xdc00 && code <= 0xdfff) return false
  }
  return encoder.encode(value).byteLength <= maximumBytes
}

export function validateEncryptedSyncCryptoContext(context: ObjectCryptoContext): void {
  if (typeof context !== 'object' || context === null
    || !validContextString(context.userId, 512)
    || !validContextString(context.projectId, 512)
    || !validContextString(context.entityId, 512)
    || !validContextString(context.entityType, 128)) protocolError('crypto_context_invalid')
}

export function normalizeC15SyncEvent(event: SyncEventEnvelope): SyncEventEnvelope {
  if (typeof event !== 'object' || event === null || typeof event.project_id !== 'string' || event.project_id.length === 0
    || typeof event.entity_id !== 'string' || event.entity_id.length === 0 || typeof event.entity_type !== 'string'
    || !ENTITY_TYPE.test(event.entity_type) || !Number.isSafeInteger(event.revision) || event.revision < 1
    || !['upsert', 'delete', 'event'].includes(event.operation)) {
    protocolError('invalid_sync_metadata')
  }
  let updatedAt: string
  let deletedAt: string | null
  try {
    updatedAt = canonicalizeSyncTimestamp(event.updated_at)
    deletedAt = event.deleted_at === null ? null : canonicalizeSyncTimestamp(event.deleted_at)
  } catch {
    protocolError('invalid_sync_metadata')
  }
  if ((event.operation === 'delete') !== (deletedAt !== null)) protocolError('invalid_sync_metadata')
  return {
    event_id: normalizeSyncUuid(event.event_id),
    project_id: event.project_id,
    entity_id: event.entity_id,
    entity_type: event.entity_type,
    operation: event.operation,
    revision: event.revision,
    updated_at: updatedAt,
    deleted_at: deletedAt,
  }
}

function context(userId: string, event: SyncEventEnvelope): ObjectCryptoContext {
  const value = { userId, projectId: event.project_id, entityId: event.entity_id, entityType: event.entity_type }
  validateEncryptedSyncCryptoContext(value)
  return value
}

function canonicalNote(note: NoteSyncRecord): NoteSyncRecord
function canonicalNote(note: NoteSyncTombstone): NoteSyncTombstone
function canonicalNote(note: NoteSyncRecord | NoteSyncTombstone): NoteSyncRecord | NoteSyncTombstone {
  if ('created_at' in note) {
    return { ...note, created_at: canonicalizeSyncTimestamp(note.created_at), updated_at: canonicalizeSyncTimestamp(note.updated_at) }
  }
  return { ...note, deleted_at: canonicalizeSyncTimestamp(note.deleted_at) }
}

export function createNoteSyncPlaintext(
  eventInput: SyncEventEnvelope,
  parentEventId: string | null,
  noteInput: NoteSyncRecord | NoteSyncTombstone,
): { event: SyncEventEnvelope; plaintext: NoteSyncPlaintext } {
  assertExactC9Event(eventInput)
  const event = normalizeC15SyncEvent(eventInput)
  if (event.entity_type !== 'note' || (event.operation !== 'upsert' && event.operation !== 'delete')) {
    protocolError('invalid_sync_metadata')
  }
  const parent = parentEventId === null ? null : normalizeSyncUuid(parentEventId)
  if ((event.revision === 1) !== (parent === null) || parent === event.event_id) protocolError('invalid_sync_metadata')
  const header = {
    event_id: event.event_id,
    parent_event_id: parent,
    project_id: event.project_id,
    entity_id: event.entity_id,
    entity_type: 'note' as const,
    operation: event.operation,
    revision: event.revision,
    updated_at: event.updated_at,
    deleted_at: event.deleted_at,
  }
  let plaintext: NoteSyncPlaintext
  if (event.operation === 'delete') {
    if (!('deleted_at' in noteInput)) protocolError('invalid_sync_metadata')
    plaintext = { version: 1, header, mutation: 'delete', note: canonicalNote(noteInput) }
  } else {
    if (!('created_at' in noteInput)) protocolError('invalid_sync_metadata')
    plaintext = {
      version: 1,
      header,
      mutation: event.revision === 1 ? 'create' : 'update',
      note: canonicalNote(noteInput),
    }
  }
  return { event, plaintext }
}

function assertMetadataBinding(eventInput: SyncEventEnvelope, plaintext: NoteSyncPlaintext): SyncEventEnvelope {
  const event = normalizeC15SyncEvent(eventInput)
  const header = plaintext.header
  canonicalHeaderUuid(header.event_id)
  if (header.parent_event_id !== null) canonicalHeaderUuid(header.parent_event_id)
  if ((header.revision === 1) !== (header.parent_event_id === null) || header.parent_event_id === header.event_id) {
    protocolError('invalid_sync_metadata')
  }
  let timestampsMatch = false
  try {
    timestampsMatch = syncTimestampsEqual(header.updated_at, event.updated_at)
      && (header.deleted_at === null
        ? event.deleted_at === null
        : event.deleted_at !== null && syncTimestampsEqual(header.deleted_at, event.deleted_at))
  } catch {
    protocolError('invalid_sync_metadata')
  }
  if (header.event_id !== event.event_id || header.project_id !== event.project_id
    || header.entity_id !== event.entity_id || header.entity_type !== event.entity_type
    || header.operation !== event.operation || header.revision !== event.revision || !timestampsMatch) {
    protocolError('metadata_mismatch')
  }
  return event
}

function eligibilityOrThrow(plaintext: NoteSyncPlaintext): void {
  const eligibility = noteSyncEligibility(plaintext)
  if (!eligibility.eligible) protocolError(eligibility.error)
}

export async function sealNoteSyncEvent(
  amk: AccountMasterKey,
  userId: string,
  eventInput: SyncEventEnvelope,
  parentEventId: string | null,
  note: NoteSyncRecord | NoteSyncTombstone,
): Promise<EncryptedSyncPushItem> {
  const { event, plaintext } = createNoteSyncPlaintext(eventInput, parentEventId, note)
  eligibilityOrThrow(plaintext)
  const cryptoContext = context(userId, event)
  let bytes: Uint8Array
  try {
    bytes = encodeNoteSyncPlaintext(plaintext)
  } catch (error) {
    if (error instanceof Error && error.name === 'payload_too_large') protocolError('payload_too_large')
    throw error
  }
  const object = await encryptObjectBytes(amk, cryptoContext, bytes)
  if (object.ciphertext.byteLength > MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES) protocolError('encrypted_sync_object_too_large')
  return { event, object }
}

export async function openNoteSyncEvent(
  amk: AccountMasterKey,
  userId: string,
  eventInput: SyncEventEnvelope,
  envelope: ObjectCryptoEnvelope,
): Promise<NoteSyncPlaintext> {
  const event = normalizeC15SyncEvent(eventInput)
  const cryptoContext = context(userId, event)
  if (!(envelope.ciphertext instanceof Uint8Array) || envelope.ciphertext.byteLength > MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES) {
    protocolError('encrypted_sync_object_too_large')
  }
  let bytes: Uint8Array
  try {
    bytes = await decryptObjectBytes(amk, cryptoContext, envelope)
  } catch {
    protocolError('decrypt_failed')
  }
  let plaintext: NoteSyncPlaintext
  try {
    plaintext = decodeNoteSyncPlaintext(bytes)
  } catch (error) {
    if (error instanceof Error && error.name === 'payload_too_large') protocolError('payload_too_large')
    protocolError('invalid_envelope')
  }
  assertMetadataBinding(eventInput, plaintext)
  eligibilityOrThrow(plaintext)
  return plaintext
}
