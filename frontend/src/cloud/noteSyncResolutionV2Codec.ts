import { MAX_NOTE_SYNC_PLAINTEXT_BYTES, type NoteSyncJson, type NoteSyncRecord, type NoteSyncTombstone } from './noteSyncCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'

export const NOTE_SYNC_RESOLUTION_V2_VERSION = 2 as const

export interface NoteSyncResolutionV2Header {
  event_id: string
  parent_event_id: string
  additional_parent_event_ids: string[]
  project_id: string
  entity_id: string
  entity_type: 'note'
  operation: 'resolution'
  revision: number
  updated_at: string
}

export type NoteSyncResolutionV2 = {
  version: typeof NOTE_SYNC_RESOLUTION_V2_VERSION
  header: NoteSyncResolutionV2Header
  mutation: 'resolution'
  resolution:
    | { conflict_group_id: string, conflict_generation: number, resolved_event_ids: string[], strategy: 'choose_version', selected_event_id: string }
    | { conflict_group_id: string, conflict_generation: number, resolved_event_ids: string[], strategy: 'manual_merge' }
    | { conflict_group_id: string, conflict_generation: number, resolved_event_ids: string[], strategy: 'keep_both', selected_event_id: string, retained_event_id: string, retained_note: NoteSyncRecord }
    | { conflict_group_id: string, conflict_generation: number, resolved_event_ids: string[], strategy: 'delete' }
  result:
    | { operation: 'upsert', note: NoteSyncRecord }
    | { operation: 'delete', note: NoteSyncTombstone }
}

const encoder = new TextEncoder()
const decoder = new TextDecoder('utf-8', { fatal: true })
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

function invalid(): never {
  const error = new TypeError('Invalid Note resolution v2 payload.')
  error.name = 'invalid_note_payload'
  throw error
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function exact(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort(); const expected = [...keys].sort()
  return actual.length === expected.length && actual.every((key, index) => key === expected[index])
}

function text(value: unknown): value is string { return typeof value === 'string' && value.length > 0 }
function nullableText(value: unknown): value is string | null { return value === null || text(value) }
function canonicalTime(value: unknown): value is string {
  if (!text(value)) return false
  try { return canonicalizeSyncTimestamp(value) === value } catch { return false }
}
function safe(value: unknown, minimum: number): value is number {
  return Number.isSafeInteger(value) && (value as number) >= minimum
}
function dense(value: readonly unknown[]): boolean {
  return value.every((_, index) => Object.prototype.hasOwnProperty.call(value, index))
}

function canonicalJson(value: NoteSyncJson): string {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'number') { if (!Number.isFinite(value)) invalid(); return JSON.stringify(value) }
  if (Array.isArray(value)) { if (!dense(value)) invalid(); return `[${value.map(item => canonicalJson(item)).join(',')}]` }
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key]!)}`).join(',')}}`
}

function route(value: Record<string, unknown>): boolean {
  return text(value.id) && text(value.project_id) && nullableText(value.stage_id)
    && (value.source_type === 'project' || value.source_type === 'mindmap')
    && nullableText(value.source_map_id) && nullableText(value.source_node_id)
    && (value.content_format === 'html' || value.content_format === 'plain')
}

function record(value: unknown): asserts value is NoteSyncRecord {
  if (!isObject(value) || !exact(value, ['id', 'project_id', 'stage_id', 'source_type', 'source_map_id', 'source_node_id', 'content_format', 'title', 'content', 'checklist', 'color', 'pinned', 'archived', 'sort_order', 'tags', 'created_at', 'updated_at', 'metadata'])
    || !route(value) || typeof value.title !== 'string' || typeof value.content !== 'string'
    || !Array.isArray(value.checklist) || !dense(value.checklist)
    || !value.checklist.every(item => isObject(item) && exact(item, ['id', 'text', 'checked']) && text(item.id) && typeof item.text === 'string' && typeof item.checked === 'boolean')
    || typeof value.color !== 'string' || typeof value.pinned !== 'boolean' || typeof value.archived !== 'boolean'
    || !Number.isSafeInteger(value.sort_order) || !Array.isArray(value.tags) || !dense(value.tags) || !value.tags.every(tag => typeof tag === 'string')
    || !canonicalTime(value.created_at) || !canonicalTime(value.updated_at) || !isObject(value.metadata)) invalid()
  try { canonicalJson(value.metadata as NoteSyncJson) } catch { invalid() }
}

function tombstone(value: unknown): asserts value is NoteSyncTombstone {
  if (!isObject(value) || !exact(value, ['id', 'project_id', 'stage_id', 'source_type', 'source_map_id', 'source_node_id', 'content_format', 'deleted_at'])
    || !route(value) || !canonicalTime(value.deleted_at)) invalid()
}

function ids(value: unknown, minimum: number, maximum: number): string[] {
  if (!Array.isArray(value) || !dense(value) || value.length < minimum || value.length > maximum || !value.every(item => typeof item === 'string' && UUID.test(item))) invalid()
  for (let index = 1; index < value.length; index += 1) if (value[index - 1]! >= value[index]!) invalid()
  return [...value] as string[]
}

export function validateNoteSyncResolutionV2(value: unknown): asserts value is NoteSyncResolutionV2 {
  if (!isObject(value) || !exact(value, ['version', 'header', 'mutation', 'resolution', 'result']) || value.version !== 2 || value.mutation !== 'resolution') invalid()
  if (!isObject(value.header) || !exact(value.header, ['event_id', 'parent_event_id', 'additional_parent_event_ids', 'project_id', 'entity_id', 'entity_type', 'operation', 'revision', 'updated_at'])) invalid()
  const header = value.header
  if (!text(header.event_id) || !UUID.test(header.event_id) || !text(header.parent_event_id) || !UUID.test(header.parent_event_id)
    || !Array.isArray(header.additional_parent_event_ids) || !text(header.project_id) || !text(header.entity_id)
    || header.entity_type !== 'note' || header.operation !== 'resolution' || !safe(header.revision, 2) || !canonicalTime(header.updated_at)) invalid()
  const additional = ids(header.additional_parent_event_ids, 1, 63)
  const parents = [header.parent_event_id, ...additional]

  if (!isObject(value.resolution) || !text(value.resolution.conflict_group_id) || !UUID.test(value.resolution.conflict_group_id)
    || !safe(value.resolution.conflict_generation, 1) || !Array.isArray(value.resolution.resolved_event_ids) || !text(value.resolution.strategy)) invalid()
  const resolution = value.resolution
  const resolved = ids(resolution.resolved_event_ids, 2, 64)
  if (parents.join('\u0000') !== resolved.join('\u0000') || header.parent_event_id !== resolved[0] || resolved.includes(header.event_id)) invalid()

  if (!isObject(value.result) || !exact(value.result, ['operation', 'note']) || (value.result.operation !== 'upsert' && value.result.operation !== 'delete')) invalid()
  const result = value.result
  if (result.operation === 'upsert') record(result.note); else tombstone(result.note)
  if (result.note.id !== header.entity_id || result.note.project_id !== header.project_id) invalid()

  if (resolution.strategy === 'choose_version') {
    if (!exact(resolution, ['conflict_group_id', 'conflict_generation', 'resolved_event_ids', 'strategy', 'selected_event_id']) || !text(resolution.selected_event_id) || !UUID.test(resolution.selected_event_id) || !resolved.includes(resolution.selected_event_id)) invalid()
  } else if (resolution.strategy === 'manual_merge') {
    if (!exact(resolution, ['conflict_group_id', 'conflict_generation', 'resolved_event_ids', 'strategy']) || result.operation !== 'upsert') invalid()
  } else if (resolution.strategy === 'delete') {
    if (!exact(resolution, ['conflict_group_id', 'conflict_generation', 'resolved_event_ids', 'strategy']) || result.operation !== 'delete') invalid()
  } else if (resolution.strategy === 'keep_both') {
    if (!exact(resolution, ['conflict_group_id', 'conflict_generation', 'resolved_event_ids', 'strategy', 'selected_event_id', 'retained_event_id', 'retained_note'])
      || resolved.length !== 2 || !text(resolution.selected_event_id) || !UUID.test(resolution.selected_event_id)
      || !text(resolution.retained_event_id) || !UUID.test(resolution.retained_event_id)
      || resolution.selected_event_id === resolution.retained_event_id || !resolved.includes(resolution.selected_event_id)
      || !resolved.includes(resolution.retained_event_id) || result.operation !== 'upsert') invalid()
    record(resolution.retained_note)
    if (resolution.retained_note.id === header.entity_id || resolution.retained_note.project_id !== header.project_id) invalid()
  } else invalid()
}

export function canonicalNoteSyncResolutionV2Json(value: NoteSyncResolutionV2): string {
  validateNoteSyncResolutionV2(value)
  return canonicalJson(value as unknown as NoteSyncJson)
}

export function encodeNoteSyncResolutionV2(value: NoteSyncResolutionV2): Uint8Array {
  const bytes = encoder.encode(canonicalNoteSyncResolutionV2Json(value))
  if (bytes.byteLength > MAX_NOTE_SYNC_PLAINTEXT_BYTES) invalid()
  return bytes
}

export function decodeNoteSyncResolutionV2(bytes: Uint8Array): NoteSyncResolutionV2 {
  if (Object.prototype.toString.call(bytes) !== '[object Uint8Array]' || bytes.byteLength > MAX_NOTE_SYNC_PLAINTEXT_BYTES) invalid()
  let textValue: string; let value: unknown
  try { textValue = decoder.decode(bytes); value = JSON.parse(textValue) } catch { invalid() }
  validateNoteSyncResolutionV2(value)
  const canonical = canonicalNoteSyncResolutionV2Json(value)
  const canonicalBytes = encoder.encode(canonical)
  if (canonical !== textValue || canonicalBytes.byteLength !== bytes.byteLength || canonicalBytes.some((byte, index) => byte !== bytes[index])) invalid()
  return value
}
