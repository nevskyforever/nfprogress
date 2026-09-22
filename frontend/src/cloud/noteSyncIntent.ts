import {
  CryptoError,
  type ObjectCryptoEnvelope,
} from '@/crypto'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { StaleAuthContextError } from '@/auth/userAuth'
import {
  EncryptedSyncProtocolError,
  createNoteSyncPlaintext,
  normalizeC15SyncEvent,
  sealNoteSyncEvent,
} from './encryptedSyncProtocol'
import {
  noteSyncEligibility,
  type NoteSyncJson,
  type NoteSyncRecord,
  type NoteSyncTombstone,
} from './noteSyncCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'
import type { SyncEventEnvelope } from './syncProtocol'

export const DEFAULT_NOTE_SEALING_BATCH_LIMIT = 8
export const MAX_NOTE_SEALING_BATCH_LIMIT = 32

export type NoteSyncSealState = 'pending' | 'retryable_error' | 'blocked' | 'invariant_error'

export type NoteSyncSealErrorCode =
  | 'key_unavailable'
  | 'payload_too_large'
  | 'encrypted_sync_object_too_large'
  | 'dependency_not_synced'
  | 'unsupported_content_format'
  | 'invalid_note_payload'
  | 'crypto_context_invalid'
  | 'invalid_sync_metadata'
  | 'invalid_envelope'
  | 'metadata_mismatch'
  | 'runtime_unavailable'

export interface UnsealedNoteSyncIntent {
  event_id: string
  account_id: string
  device_id: string
  project_id: string
  entity_id: string
  entity_type: string
  operation: 'upsert' | 'delete'
  revision: number
  parent_event_id: string | null
  updated_at: string
  deleted_at: string | null
  local_ordinal: number
  mutation_generation: number
  snapshot_json: string
  seal_state: NoteSyncSealState
  seal_attempt_count: number
  last_error_code: string | null
  next_attempt_at: string | null
}

export type RecordNoteSyncSealFailureResult = 'recorded' | 'stale_generation' | 'already_sealed'
export type CommitSealedNoteSyncEventResult = 'sealed' | 'stale_generation' | 'already_sealed'

export interface RecordNoteSyncSealFailureInput {
  eventId: string
  expectedMutationGeneration: number
  errorCode: NoteSyncSealErrorCode
}

export interface CommitSealedNoteSyncEventInput {
  eventId: string
  expectedMutationGeneration: number
  envelope: ObjectCryptoEnvelope
}

export interface NoteSyncIntentRepository {
  list(limit: number, retryBlocked: boolean): Promise<UnsealedNoteSyncIntent[]>
  recordSealFailure(input: RecordNoteSyncSealFailureInput): Promise<RecordNoteSyncSealFailureResult>
  commitSealedEvent(input: CommitSealedNoteSyncEventInput): Promise<CommitSealedNoteSyncEventResult>
}

export interface NoteSyncSealingPassOptions {
  limit?: number
  retryBlocked?: boolean
}

export type NoteSyncSealingItemStatus =
  | 'sealed'
  | 'already_sealed'
  | 'stale_generation'
  | 'failure_recorded'
  | 'failure_stale_generation'
  | 'failure_already_sealed'
  | 'blocked_skipped'
  | 'failure_record_failed'
  | 'commit_failed'
  | 'unclassified_error'

export interface NoteSyncSealingItemResult {
  event_id: string
  mutation_generation: number
  status: NoteSyncSealingItemStatus
  error_code?: NoteSyncSealErrorCode
}

export interface NoteSyncSealingPassResult {
  listed: number
  results: NoteSyncSealingItemResult[]
}

class NoteIntentPreparationError extends Error {
  readonly name = 'NoteIntentPreparationError'

  constructor(readonly code: NoteSyncSealErrorCode) {
    super('Note sync intent cannot be prepared for sealing.')
  }
}

function preparationError(code: NoteSyncSealErrorCode): never {
  throw new NoteIntentPreparationError(code)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index])
}

function requiredString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function nullableString(value: unknown): value is string | null {
  return value === null || requiredString(value)
}

function noteSyncJson(value: unknown): value is NoteSyncJson {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true
  if (typeof value === 'number') return Number.isFinite(value)
  if (Array.isArray(value)) return value.every(noteSyncJson)
  return isRecord(value) && Object.values(value).every(noteSyncJson)
}

function normalizedTimestamp(value: unknown): string {
  if (!requiredString(value)) preparationError('invalid_note_payload')
  try {
    return canonicalizeSyncTimestamp(value)
  } catch {
    preparationError('invalid_note_payload')
  }
}

const ROUTE_KEYS = [
  'id', 'project_id', 'stage_id', 'source_type', 'source_map_id', 'source_node_id', 'content_format',
] as const
const RECORD_KEYS = [
  ...ROUTE_KEYS, 'title', 'content', 'checklist', 'color', 'pinned', 'archived', 'sort_order', 'tags',
  'created_at', 'updated_at', 'metadata', 'revision',
] as const
const TOMBSTONE_KEYS = [...ROUTE_KEYS, 'deleted_at'] as const

function validateRoute(snapshot: Record<string, unknown>): void {
  if (!requiredString(snapshot.id) || !requiredString(snapshot.project_id)
    || !nullableString(snapshot.stage_id)
    || (snapshot.source_type !== 'project' && snapshot.source_type !== 'mindmap')
    || !nullableString(snapshot.source_map_id) || !nullableString(snapshot.source_node_id)
    || (snapshot.content_format !== 'html' && snapshot.content_format !== 'plain')) {
    preparationError('invalid_note_payload')
  }
}

function validateIdentity(
  snapshot: Record<string, unknown>,
  event: SyncEventEnvelope,
): void {
  if (snapshot.id !== event.entity_id || snapshot.project_id !== event.project_id) {
    preparationError('metadata_mismatch')
  }
}

function mapRecord(snapshot: Record<string, unknown>, event: SyncEventEnvelope): NoteSyncRecord {
  if (!hasExactKeys(snapshot, RECORD_KEYS)) preparationError('invalid_note_payload')
  validateRoute(snapshot)
  validateIdentity(snapshot, event)
  if (typeof snapshot.title !== 'string' || typeof snapshot.content !== 'string'
    || !Array.isArray(snapshot.checklist)
    || !snapshot.checklist.every(item => isRecord(item)
      && hasExactKeys(item, ['id', 'text', 'checked'])
      && requiredString(item.id) && typeof item.text === 'string' && typeof item.checked === 'boolean')
    || typeof snapshot.color !== 'string' || typeof snapshot.pinned !== 'boolean'
    || typeof snapshot.archived !== 'boolean' || !Number.isSafeInteger(snapshot.sort_order)
    || !Array.isArray(snapshot.tags) || !snapshot.tags.every(tag => typeof tag === 'string')
    || !isRecord(snapshot.metadata) || !noteSyncJson(snapshot.metadata)
    || !Number.isSafeInteger(snapshot.revision) || (snapshot.revision as number) < 0) {
    preparationError('invalid_note_payload')
  }
  const createdAt = normalizedTimestamp(snapshot.created_at)
  const updatedAt = normalizedTimestamp(snapshot.updated_at)
  if (updatedAt !== event.updated_at) preparationError('metadata_mismatch')
  return {
    id: snapshot.id as string,
    project_id: snapshot.project_id as string,
    stage_id: snapshot.stage_id as string | null,
    source_type: snapshot.source_type as 'project' | 'mindmap',
    source_map_id: snapshot.source_map_id as string | null,
    source_node_id: snapshot.source_node_id as string | null,
    content_format: snapshot.content_format as 'html' | 'plain',
    title: snapshot.title,
    content: snapshot.content,
    checklist: snapshot.checklist as NoteSyncRecord['checklist'],
    color: snapshot.color,
    pinned: snapshot.pinned,
    archived: snapshot.archived,
    sort_order: snapshot.sort_order as number,
    tags: snapshot.tags as string[],
    created_at: createdAt,
    updated_at: updatedAt,
    metadata: snapshot.metadata as NoteSyncRecord['metadata'],
  }
}

function mapTombstone(snapshot: Record<string, unknown>, event: SyncEventEnvelope): NoteSyncTombstone {
  if (!hasExactKeys(snapshot, TOMBSTONE_KEYS)) preparationError('invalid_note_payload')
  validateRoute(snapshot)
  validateIdentity(snapshot, event)
  const deletedAt = normalizedTimestamp(snapshot.deleted_at)
  if (deletedAt !== event.deleted_at) preparationError('metadata_mismatch')
  return {
    id: snapshot.id as string,
    project_id: snapshot.project_id as string,
    stage_id: snapshot.stage_id as string | null,
    source_type: snapshot.source_type as 'project' | 'mindmap',
    source_map_id: snapshot.source_map_id as string | null,
    source_node_id: snapshot.source_node_id as string | null,
    content_format: snapshot.content_format as 'html' | 'plain',
    deleted_at: deletedAt,
  }
}

function eventFromIntent(intent: UnsealedNoteSyncIntent): SyncEventEnvelope {
  try {
    const event = normalizeC15SyncEvent({
      event_id: intent.event_id,
      project_id: intent.project_id,
      entity_id: intent.entity_id,
      entity_type: intent.entity_type,
      operation: intent.operation,
      revision: intent.revision,
      updated_at: intent.updated_at,
      deleted_at: intent.deleted_at,
    })
    if (event.entity_type !== 'note' || (event.operation !== 'upsert' && event.operation !== 'delete')) {
      preparationError('invalid_sync_metadata')
    }
    if (event.operation === 'delete' && event.updated_at !== event.deleted_at) {
      preparationError('invalid_sync_metadata')
    }
    return event
  } catch (error) {
    if (error instanceof NoteIntentPreparationError) throw error
    preparationError('invalid_sync_metadata')
  }
}

function parseSnapshot(intent: UnsealedNoteSyncIntent, event: SyncEventEnvelope): NoteSyncRecord | NoteSyncTombstone {
  let snapshot: unknown
  try {
    snapshot = JSON.parse(intent.snapshot_json)
  } catch {
    preparationError('invalid_note_payload')
  }
  if (!isRecord(snapshot)) preparationError('invalid_note_payload')
  return event.operation === 'delete' ? mapTombstone(snapshot, event) : mapRecord(snapshot, event)
}

function prepareIntent(intent: UnsealedNoteSyncIntent): {
  event: SyncEventEnvelope
  note: NoteSyncRecord | NoteSyncTombstone
} {
  const event = eventFromIntent(intent)
  const note = parseSnapshot(intent, event)
  try {
    const { plaintext } = createNoteSyncPlaintext(event, intent.parent_event_id, note)
    const eligibility = noteSyncEligibility(plaintext)
    if (!eligibility.eligible) preparationError(eligibility.error)
  } catch (error) {
    const classified = classifySealingError(error)
    if (classified !== null) preparationError(classified)
    throw error
  }
  return { event, note }
}

function classifySealingError(error: unknown): NoteSyncSealErrorCode | null {
  if (error instanceof NoteIntentPreparationError) return error.code
  if (error instanceof EncryptedSyncProtocolError && error.code !== 'decrypt_failed') return error.code
  if (error instanceof CryptoError) {
    if (error.code === 'runtime_unavailable') return 'runtime_unavailable'
    if (error.code === 'invalid_format' || error.code === 'invalid_key_length'
      || error.code === 'unsupported_version') return 'crypto_context_invalid'
    return null
  }
  if (error instanceof Error && (error.name === 'invalid_note_payload' || error.name === 'payload_too_large')) {
    return error.name
  }
  return null
}

async function recordFailure(
  repository: NoteSyncIntentRepository,
  intent: UnsealedNoteSyncIntent,
  errorCode: NoteSyncSealErrorCode,
): Promise<NoteSyncSealingItemResult> {
  try {
    const result = await repository.recordSealFailure({
      eventId: intent.event_id,
      expectedMutationGeneration: intent.mutation_generation,
      errorCode,
    })
    const status: NoteSyncSealingItemStatus = result === 'recorded'
      ? 'failure_recorded'
      : result === 'stale_generation'
        ? 'failure_stale_generation'
        : 'failure_already_sealed'
    return {
      event_id: intent.event_id,
      mutation_generation: intent.mutation_generation,
      status,
      error_code: errorCode,
    }
  } catch {
    return {
      event_id: intent.event_id,
      mutation_generation: intent.mutation_generation,
      status: 'failure_record_failed',
      error_code: errorCode,
    }
  }
}

function diagnosticResult(
  intent: UnsealedNoteSyncIntent,
  status: 'commit_failed' | 'unclassified_error',
): NoteSyncSealingItemResult {
  return {
    event_id: intent.event_id,
    mutation_generation: intent.mutation_generation,
    status,
  }
}

async function sealIntent(
  intent: UnsealedNoteSyncIntent,
  repository: NoteSyncIntentRepository,
  keyContext: RuntimeKeyContext,
): Promise<NoteSyncSealingItemResult> {
  let prepared: ReturnType<typeof prepareIntent>
  try {
    prepared = prepareIntent(intent)
  } catch (error) {
    const errorCode = classifySealingError(error)
    return errorCode === null
      ? diagnosticResult(intent, 'unclassified_error')
      : recordFailure(repository, intent, errorCode)
  }

  let lease
  try {
    lease = keyContext.leaseForAccount(intent.account_id)
  } catch {
    return diagnosticResult(intent, 'unclassified_error')
  }
  if (lease === null) {
    return recordFailure(repository, intent, 'key_unavailable')
  }
  if (lease.localAccountId !== intent.account_id || !requiredString(lease.canonicalUserId)) {
    return recordFailure(repository, intent, 'crypto_context_invalid')
  }
  if (!lease.isCurrent()) return recordFailure(repository, intent, 'key_unavailable')

  try {
    // The lease spans both encryption and the complete Tauri commit IPC. Logout,
    // account switch, and key lock cannot finish between these two operations.
    return await lease.use(async masterKey => {
      let encrypted: Awaited<ReturnType<typeof sealNoteSyncEvent>>
      try {
        encrypted = await sealNoteSyncEvent(
          masterKey,
          lease.canonicalUserId,
          prepared.event,
          intent.parent_event_id,
          prepared.note,
        )
      } catch (error) {
        const errorCode = classifySealingError(error)
        return errorCode === null
          ? diagnosticResult(intent, 'unclassified_error')
          : recordFailure(repository, intent, errorCode)
      }

      try {
        const result = await repository.commitSealedEvent({
          eventId: intent.event_id,
          expectedMutationGeneration: intent.mutation_generation,
          envelope: encrypted.object,
        })
        return {
          event_id: intent.event_id,
          mutation_generation: intent.mutation_generation,
          status: result,
        }
      } catch {
        return diagnosticResult(intent, 'commit_failed')
      }
    })
  } catch (error) {
    if (error instanceof StaleAuthContextError) {
      return recordFailure(repository, intent, 'key_unavailable')
    }
    const errorCode = classifySealingError(error)
    return errorCode === null
      ? diagnosticResult(intent, 'unclassified_error')
      : recordFailure(repository, intent, errorCode)
  }
}

export async function sealPendingNoteSyncIntents(
  repository: NoteSyncIntentRepository,
  keyContext: RuntimeKeyContext,
  options: NoteSyncSealingPassOptions = {},
): Promise<NoteSyncSealingPassResult> {
  const limit = options.limit ?? DEFAULT_NOTE_SEALING_BATCH_LIMIT
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_NOTE_SEALING_BATCH_LIMIT) {
    throw new RangeError('Invalid Note sealing batch limit.')
  }
  const intents = await repository.list(limit, options.retryBlocked === true)
  const results: NoteSyncSealingItemResult[] = []
  for (const intent of intents) {
    if (intent.seal_state === 'blocked' && options.retryBlocked !== true) {
      results.push({
        event_id: intent.event_id,
        mutation_generation: intent.mutation_generation,
        status: 'blocked_skipped',
      })
      continue
    }
    results.push(await sealIntent(intent, repository, keyContext))
  }
  return { listed: intents.length, results }
}
