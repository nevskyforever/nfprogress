import { canonicalizeSyncTimestamp } from './syncTimestamp'

export const NOTE_SYNC_PLAINTEXT_VERSION = 1 as const
export const MAX_NOTE_SYNC_PLAINTEXT_BYTES = 8 * 1024 * 1024

export type NoteSyncMutation = 'create' | 'update' | 'delete'
export type NoteSyncSourceType = 'project' | 'mindmap'
export type NoteSyncJson = null | boolean | number | string | NoteSyncJson[] | { [key: string]: NoteSyncJson }

export interface NoteSyncHeader {
  event_id: string
  parent_event_id: string | null
  project_id: string
  entity_id: string
  entity_type: 'note'
  operation: 'upsert' | 'delete'
  revision: number
  updated_at: string
  deleted_at: string | null
}

export interface NoteSyncRoute {
  id: string
  project_id: string
  stage_id: string | null
  source_type: NoteSyncSourceType
  source_map_id: string | null
  source_node_id: string | null
  content_format: 'html' | 'plain'
}

export interface NoteSyncRecord extends NoteSyncRoute {
  title: string
  content: string
  checklist: Array<{ id: string; text: string; checked: boolean }>
  color: string
  pinned: boolean
  archived: boolean
  sort_order: number
  tags: string[]
  created_at: string
  updated_at: string
  metadata: { [key: string]: NoteSyncJson }
}

export interface NoteSyncTombstone extends NoteSyncRoute {
  deleted_at: string
}

export type NoteSyncPlaintext =
  | { version: typeof NOTE_SYNC_PLAINTEXT_VERSION; header: NoteSyncHeader; mutation: 'create' | 'update'; note: NoteSyncRecord }
  | { version: typeof NOTE_SYNC_PLAINTEXT_VERSION; header: NoteSyncHeader; mutation: 'delete'; note: NoteSyncTombstone }

export type NoteSyncEligibility = { eligible: true } | {
  eligible: false
  error: 'dependency_not_synced' | 'unsupported_content_format'
}

const encoder = new TextEncoder()
const decoder = new TextDecoder('utf-8', { fatal: true })
const CANONICAL_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

function codecError(code: 'invalid_note_payload' | 'payload_too_large'): never {
  const error = new TypeError(code === 'payload_too_large' ? 'Note sync payload exceeds size limit.' : 'Invalid note sync payload.')
  error.name = code
  throw error
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  return actual.length === expected.length && actual.every((key, index) => key === expected[index])
}

function isDenseArray(value: readonly unknown[]): boolean {
  for (let index = 0; index < value.length; index += 1) {
    if (!Object.prototype.hasOwnProperty.call(value, index)) return false
  }
  return true
}

function canonicalJson(value: NoteSyncJson): string {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) codecError('invalid_note_payload')
    return JSON.stringify(value)
  }
  if (Array.isArray(value)) {
    if (!isDenseArray(value)) codecError('invalid_note_payload')
    return `[${value.map(item => canonicalJson(item)).join(',')}]`
  }
  const entries = Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key]!)}`)
  return `{${entries.join(',')}}`
}

function requiredString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function nullableString(value: unknown): value is string | null {
  return value === null || requiredString(value)
}

function validateRoute(value: Record<string, unknown>): void {
  if (!requiredString(value.id) || !requiredString(value.project_id) || !nullableString(value.stage_id)
    || (value.source_type !== 'project' && value.source_type !== 'mindmap')
    || !nullableString(value.source_map_id) || !nullableString(value.source_node_id)
    || (value.content_format !== 'html' && value.content_format !== 'plain')) codecError('invalid_note_payload')
}

function validateHeader(value: unknown): asserts value is NoteSyncHeader {
  if (!isObject(value) || !hasExactKeys(value, [
    'event_id', 'parent_event_id', 'project_id', 'entity_id', 'entity_type', 'operation',
    'revision', 'updated_at', 'deleted_at',
  ])) codecError('invalid_note_payload')
  if (typeof value.event_id !== 'string' || !CANONICAL_UUID.test(value.event_id)
    || !(value.parent_event_id === null || (typeof value.parent_event_id === 'string' && CANONICAL_UUID.test(value.parent_event_id)))
    || !requiredString(value.project_id) || !requiredString(value.entity_id) || value.entity_type !== 'note'
    || (value.operation !== 'upsert' && value.operation !== 'delete')
    || !Number.isSafeInteger(value.revision) || (value.revision as number) < 1
    || !requiredString(value.updated_at) || !(value.deleted_at === null || requiredString(value.deleted_at))) {
    codecError('invalid_note_payload')
  }
  try {
    if (canonicalizeSyncTimestamp(value.updated_at as string) !== value.updated_at) codecError('invalid_note_payload')
    if (value.deleted_at !== null && canonicalizeSyncTimestamp(value.deleted_at as string) !== value.deleted_at) codecError('invalid_note_payload')
  } catch {
    codecError('invalid_note_payload')
  }
  if ((value.operation === 'delete') !== (value.deleted_at !== null)) codecError('invalid_note_payload')
  if (((value.revision as number) === 1) !== (value.parent_event_id === null)
    || value.parent_event_id === value.event_id) codecError('invalid_note_payload')
}

function validateRecord(value: unknown): asserts value is NoteSyncRecord {
  if (!isObject(value) || !hasExactKeys(value, [
    'id', 'project_id', 'stage_id', 'source_type', 'source_map_id', 'source_node_id', 'content_format',
    'title', 'content', 'checklist', 'color', 'pinned', 'archived', 'sort_order', 'tags',
    'created_at', 'updated_at', 'metadata',
  ])) codecError('invalid_note_payload')
  validateRoute(value)
  if (typeof value.title !== 'string' || typeof value.content !== 'string' || !Array.isArray(value.checklist)
    || !isDenseArray(value.checklist)
    || !value.checklist.every(item => isObject(item) && hasExactKeys(item, ['id', 'text', 'checked'])
      && requiredString(item.id) && typeof item.text === 'string' && typeof item.checked === 'boolean')
    || typeof value.color !== 'string' || typeof value.pinned !== 'boolean' || typeof value.archived !== 'boolean'
    || !Number.isSafeInteger(value.sort_order) || !Array.isArray(value.tags) || !isDenseArray(value.tags)
    || !value.tags.every(tag => typeof tag === 'string')
    || !requiredString(value.created_at) || !requiredString(value.updated_at) || !isObject(value.metadata)) {
    codecError('invalid_note_payload')
  }
  try {
    if (canonicalizeSyncTimestamp(value.created_at) !== value.created_at
      || canonicalizeSyncTimestamp(value.updated_at) !== value.updated_at) codecError('invalid_note_payload')
    canonicalJson(value.metadata as NoteSyncJson)
  } catch {
    codecError('invalid_note_payload')
  }
}

function validateTombstone(value: unknown): asserts value is NoteSyncTombstone {
  if (!isObject(value) || !hasExactKeys(value, [
    'id', 'project_id', 'stage_id', 'source_type', 'source_map_id', 'source_node_id', 'content_format', 'deleted_at',
  ])) codecError('invalid_note_payload')
  validateRoute(value)
  if (!requiredString(value.deleted_at)) codecError('invalid_note_payload')
  try {
    if (canonicalizeSyncTimestamp(value.deleted_at) !== value.deleted_at) codecError('invalid_note_payload')
  } catch {
    codecError('invalid_note_payload')
  }
}

export function validateNoteSyncPlaintext(value: unknown): asserts value is NoteSyncPlaintext {
  if (!isObject(value) || !hasExactKeys(value, ['version', 'header', 'mutation', 'note']) || value.version !== 1) {
    codecError('invalid_note_payload')
  }
  validateHeader(value.header)
  if (value.mutation === 'create' || value.mutation === 'update') validateRecord(value.note)
  else if (value.mutation === 'delete') validateTombstone(value.note)
  else codecError('invalid_note_payload')

  const plaintext = value as unknown as NoteSyncPlaintext
  const expectedMutation = plaintext.header.operation === 'delete'
    ? 'delete'
    : plaintext.header.revision === 1 ? 'create' : 'update'
  if (plaintext.mutation !== expectedMutation || plaintext.note.id !== plaintext.header.entity_id
    || plaintext.note.project_id !== plaintext.header.project_id
    || (plaintext.mutation === 'delete'
      ? plaintext.note.deleted_at !== plaintext.header.deleted_at
      : plaintext.note.updated_at !== plaintext.header.updated_at)) {
    codecError('invalid_note_payload')
  }
}

export function canonicalNoteSyncJson(value: NoteSyncPlaintext): string {
  validateNoteSyncPlaintext(value)
  return canonicalJson(value as unknown as NoteSyncJson)
}

export function encodeNoteSyncPlaintext(value: NoteSyncPlaintext): Uint8Array {
  const bytes = encoder.encode(canonicalNoteSyncJson(value))
  if (bytes.byteLength > MAX_NOTE_SYNC_PLAINTEXT_BYTES) codecError('payload_too_large')
  return bytes
}

export function decodeNoteSyncPlaintext(bytes: Uint8Array): NoteSyncPlaintext {
  if (Object.prototype.toString.call(bytes) !== '[object Uint8Array]') codecError('invalid_note_payload')
  if (bytes.byteLength > MAX_NOTE_SYNC_PLAINTEXT_BYTES) codecError('payload_too_large')
  let parsed: unknown
  let text: string
  try {
    text = decoder.decode(bytes)
    parsed = JSON.parse(text)
  } catch {
    codecError('invalid_note_payload')
  }
  validateNoteSyncPlaintext(parsed)
  if (encoder.encode(canonicalNoteSyncJson(parsed)).byteLength !== bytes.byteLength
    || canonicalNoteSyncJson(parsed) !== text) codecError('invalid_note_payload')
  return parsed
}

export function noteSyncEligibility(value: NoteSyncPlaintext): NoteSyncEligibility {
  const note = value.note
  if (note.stage_id !== null || note.source_type !== 'project'
    || note.source_map_id !== null || note.source_node_id !== null) {
    return { eligible: false, error: 'dependency_not_synced' }
  }
  if (note.content_format !== 'html') return { eligible: false, error: 'unsupported_content_format' }
  return { eligible: true }
}
