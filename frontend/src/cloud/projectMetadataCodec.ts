import { validateCoverReference, type ProjectCoverReference } from './projectCoverReference'
import { canonicalizeSyncTimestamp } from './syncTimestamp'
import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'

// C18.2 strict codec; C18.3.01 runtime writers require explicit mode-3 authority.
export const METADATA_CODEC_VERSION = 1 as const
export const MAX_METADATA_BYTES = 1024 * 1024
const MAGIC = new Uint8Array([0x57, 0x4f, 0x52, 0x54, 0x41, 0x2d, 0x43, 0x31]) // WORTA-C1
const encoder = new TextEncoder()
const decoder = new TextDecoder('utf-8', { fatal: true })
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const META_KEYS = ['auto_freeze', 'combine_stage_mindmaps', 'deadline', 'stages_enabled', 'goal', 'infinite', 'name', 'personal_goal', 'status', 'streak_enabled', 'unit', 'work_method'] as const
const HEADER_KEYS = ['account_id', 'bootstrap_id', 'device_id', 'entity_id', 'event_id', 'generation', 'operation', 'parent_event_ids', 'project_id', 'revision', 'updated_at'] as const

export const METADATA_COVER_CODEC_VERSION = 2 as const
export interface ProjectMetadata {
  cover_reference?: ProjectCoverReference | null
  name: string; goal: number | null; infinite: boolean; unit: string; deadline: string | null
  status: string; personal_goal: number; auto_freeze: boolean; streak_enabled: boolean
  work_method: string; stages_enabled: boolean; combine_stage_mindmaps: boolean
}
export interface MetadataHeader {
  account_id: string; bootstrap_id: string; device_id: string; entity_id: string; event_id: string
  generation: number; operation: 'create' | 'update' | 'delete' | 'genesis_resolution' | 'resolution'
  parent_event_ids: string[]; project_id: string; revision: number; updated_at: string
}
export type ProjectMetadataEvent = { version: 1 | 2; header: MetadataHeader; metadata: ProjectMetadata | null; deleted_at: string | null }

function fail(): never { throw new TypeError('invalid_project_metadata') }
function obj(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value) }
function exact(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort()
  return actual.length === keys.length && actual.every((key, i) => key === [...keys].sort()[i])
}
function positive(value: unknown): value is number { return Number.isSafeInteger(value) && (value as number) >= 1 }
function finiteNonnegative(value: unknown): value is number { return typeof value === 'number' && Number.isFinite(value) && value >= 0 }
function nonempty(value: unknown): value is string { return typeof value === 'string' && value.length > 0 && encoder.encode(value).length <= 512 }
export function timestamp(value: unknown): value is string {
  if (typeof value !== 'string') return false
  try { return canonicalizeSyncTimestamp(value) === value } catch { return false }
}
export function validateProjectMetadataEvent(value: unknown): asserts value is ProjectMetadataEvent {
  if (!obj(value) || !exact(value, ['version', 'header', 'metadata', 'deleted_at']) || ![1,2].includes(value.version as number) || !obj(value.header)) fail()
  const h = value.header
  if (!exact(h, HEADER_KEYS) || !UUID.test(String(h.account_id)) || !UUID.test(String(h.bootstrap_id))
    || !UUID.test(String(h.device_id)) || !UUID.test(String(h.event_id)) || !nonempty(h.project_id)
    || h.entity_id !== h.project_id || !positive(h.generation) || !positive(h.revision) || !timestamp(h.updated_at)
    || !['create', 'update', 'delete', 'genesis_resolution', 'resolution'].includes(String(h.operation))
    || !Array.isArray(h.parent_event_ids) || h.parent_event_ids.length > 64
    || !h.parent_event_ids.every((id: unknown) => typeof id === 'string' && UUID.test(id))
    || h.parent_event_ids.some((id: unknown, i: number, ids: unknown[]) => i > 0 && typeof id === 'string' && typeof ids[i - 1] === 'string' && id <= (ids[i - 1] as string))
    || h.parent_event_ids.includes(h.event_id)) fail()
  if (h.operation === 'create' && (h.revision !== 1 || h.generation !== 1 || h.parent_event_ids.length !== 0)) fail()
  if (h.operation === 'genesis_resolution' && (h.revision < 2 || h.parent_event_ids.length < 2)) fail()
  if (['update', 'delete'].includes(String(h.operation)) && h.parent_event_ids.length !== 1) fail()
  if (h.operation === 'resolution' && h.parent_event_ids.length < 2) fail()
  if (h.operation === 'delete') {
    if (value.metadata !== null || !timestamp(value.deleted_at) || value.deleted_at !== h.updated_at) fail()
  } else {
    if (value.deleted_at !== null || !obj(value.metadata) || !exact(value.metadata, value.version === 2 ? [...META_KEYS, 'cover_reference'] : META_KEYS)) fail()
    const m = value.metadata
    if (value.version === 2 && m.cover_reference !== null) validateCoverReference(m.cover_reference)
    if (!nonempty(m.name) || !(m.goal === null || finiteNonnegative(m.goal)) || typeof m.infinite !== 'boolean'
      || !nonempty(m.unit) || !(m.deadline === null || nonempty(m.deadline)) || !nonempty(m.status)
      || !finiteNonnegative(m.personal_goal) || typeof m.auto_freeze !== 'boolean'
      || typeof m.streak_enabled !== 'boolean' || !nonempty(m.work_method)
      || typeof m.stages_enabled !== 'boolean' || typeof m.combine_stage_mindmaps !== 'boolean') fail()
  }
}
export function canonical(value: unknown): string {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value)
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
  if (!obj(value)) fail()
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
}
export function encodeProjectMetadataEvent(value: ProjectMetadataEvent): Uint8Array {
  validateProjectMetadataEvent(value)
  const bytes = encoder.encode(canonical(value))
  if (bytes.length > MAX_METADATA_BYTES) fail()
  return bytes
}
export function decodeProjectMetadataEvent(bytes: Uint8Array): ProjectMetadataEvent {
  if (!(bytes instanceof Uint8Array) || bytes.length > MAX_METADATA_BYTES) fail()
  let parsed: unknown
  try { parsed = JSON.parse(decoder.decode(bytes)) } catch { fail() }
  validateProjectMetadataEvent(parsed)
  if (canonical(parsed) !== decoder.decode(bytes)) fail()
  return parsed
}
// Explicit 20-byte v1 frame: magic[8], version, codec, codec version, compression, length[4], payload length[4].
export function frameProjectMetadata(value: ProjectMetadataEvent): Uint8Array {
  const payload = encodeProjectMetadataEvent(value)
  const frame = new Uint8Array(20 + payload.length)
  frame.set(MAGIC); frame.set([1, 1, value.version, 0], 8)
  const sizes = new DataView(frame.buffer)
  sizes.setUint32(12, payload.length, false); sizes.setUint32(16, payload.length, false)
  frame.set(payload, 20)
  return frame
}
export function unframeProjectMetadata(frame: Uint8Array): ProjectMetadataEvent {
  if (!(frame instanceof Uint8Array) || frame.length < 20 || frame.length > MAX_METADATA_BYTES + 20
    || !MAGIC.every((byte, i) => frame[i] === byte) || frame[8] !== 1 || frame[9] !== 1
    || ![1,2].includes(frame[10]!) || frame[11] !== 0) fail()
  const sizes = new DataView(frame.buffer, frame.byteOffset, frame.byteLength)
  if (sizes.getUint32(12, false) !== frame.length - 20 || sizes.getUint32(16, false) !== frame.length - 20) fail()
  const event = decodeProjectMetadataEvent(frame.subarray(20))
  if (event.version !== frame[10]) fail()
  return event
}
export async function sealProjectMetadataEvent(amk: AccountMasterKey, event: ProjectMetadataEvent): Promise<ObjectCryptoEnvelope> {
  validateProjectMetadataEvent(event)
  return encryptObjectBytes(amk, { userId: event.header.account_id, projectId: event.header.project_id, entityId: event.header.entity_id, entityType: 'project_metadata' }, frameProjectMetadata(event))
}
export async function openProjectMetadataEvent(amk: AccountMasterKey, context: { account_id: string; project_id: string; entity_id: string; event_id: string }, envelope: ObjectCryptoEnvelope): Promise<ProjectMetadataEvent> {
  const bytes = await decryptObjectBytes(amk, { userId: context.account_id, projectId: context.project_id, entityId: context.entity_id, entityType: 'project_metadata' }, envelope)
  try {
    const event = unframeProjectMetadata(bytes)
    if (event.header.account_id !== context.account_id || event.header.project_id !== context.project_id
      || event.header.entity_id !== context.entity_id || event.header.event_id !== context.event_id) fail()
    return event
  } finally { bytes.fill(0) }
}
