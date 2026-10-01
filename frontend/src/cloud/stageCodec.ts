import { canonical, timestamp } from './projectMetadataCodec'
import { decryptObjectBytes, encryptObjectBytes, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'

export const STAGE_FIELDS = ['name', 'goal', 'infinite', 'unit', 'status', 'deadline', 'personal_goal', 'auto_freeze', 'streak_enabled', 'work_method', 'created_at', 'completed_at'] as const
export const MAX_STAGE_BYTES = 1024 * 1024
export interface StagePortable {
  name: string; goal: number | null; infinite: boolean; unit: string; status: string
  deadline: string | null; personal_goal: number; auto_freeze: boolean; streak_enabled: boolean
  work_method: string; created_at: string | null; completed_at: string | null
}
export interface StructuralHeader {
  account_id: string; project_id: string; bootstrap_id: string; device_id: string
  entity_id: string; entity_type: 'stage' | 'stage_order'; event_id: string
  operation: 'create' | 'update' | 'delete'; revision: number; generation: number
  parent_event_ids: string[]; updated_at: string; metadata_event_id: string
}
export type StructuralEvent = {
  version: 1 | 2; header: StructuralHeader; stage: StagePortable | null
  stage_ids: string[] | null; stage_heads: Record<string, string[]> | null; deleted_at: string | null
}
const encoder = new TextEncoder(), decoder = new TextDecoder('utf-8', { fatal: true })
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const MAGIC = [0x57, 0x4f, 0x52, 0x54, 0x41, 0x2d, 0x43, 0x31]
function fail(): never { throw new TypeError('invalid_stage_structure') }
const obj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
const exact = (v: Record<string, unknown>, keys: readonly string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k))
const text = (v: unknown): v is string => typeof v === 'string' && !/[\uD800-\uDFFF]/u.test(v) && encoder.encode(v).length > 0 && encoder.encode(v).length <= 512
const positive = (v: unknown) => Number.isSafeInteger(v) && (v as number) > 0
const number = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= Number.MAX_SAFE_INTEGER
export function validateStructuralEvent(value: unknown): asserts value is StructuralEvent {
  if (!obj(value) || !exact(value, ['version', 'header', 'stage', 'stage_ids', 'stage_heads', 'deleted_at']) || (value.version !== 1 && value.version !== 2) || !obj(value.header)) fail()
  const h = value.header
  if (!exact(h, ['account_id', 'project_id', 'bootstrap_id', 'device_id', 'entity_id', 'entity_type', 'event_id', 'operation', 'revision', 'generation', 'parent_event_ids', 'updated_at', 'metadata_event_id'])
    || !['account_id', 'bootstrap_id', 'device_id', 'event_id', 'metadata_event_id'].every(k => typeof h[k] === 'string' && UUID.test(h[k] as string))
    || !text(h.project_id) || !text(h.entity_id) || !['stage', 'stage_order'].includes(String(h.entity_type))
    || !['create', 'update', 'delete'].includes(String(h.operation)) || !positive(h.revision) || !positive(h.generation) || !timestamp(h.updated_at)
    || !Array.isArray(h.parent_event_ids)
    || (value.version === 1 ? h.parent_event_ids.length !== (h.operation === 'create' ? 0 : 1)
      : h.operation === 'create' || h.parent_event_ids.length < 1 || h.parent_event_ids.length > 64
        || h.parent_event_ids.some((id, i, ids) => i > 0 && id <= ids[i - 1]))
    || !h.parent_event_ids.every(p => typeof p === 'string' && UUID.test(p) && p !== h.event_id)
    || (h.operation === 'create' ? h.revision !== 1 || h.generation !== 1 : (h.revision as number) < 2 || (h.generation as number) < 2)) fail()
  if (h.entity_type === 'stage_order') {
    if (h.entity_id !== 'stage_order' || h.operation === 'delete' || value.stage !== null || value.deleted_at !== null
      || !Array.isArray(value.stage_ids) || value.stage_ids.length > 4096 || !value.stage_ids.every(text)
      || new Set(value.stage_ids).size !== value.stage_ids.length || !obj(value.stage_heads)
      || !exact(value.stage_heads, value.stage_ids as string[]) || !Object.values(value.stage_heads).every(v => Array.isArray(v) && v.length >= 1 && v.length <= 64 && v.every((id, i) => typeof id === 'string' && UUID.test(id) && (i === 0 || id > v[i - 1])))) fail()
  } else {
    if (value.stage_ids !== null || value.stage_heads !== null) fail()
    if (h.operation === 'delete') {
      if (value.stage !== null || value.deleted_at !== h.updated_at) fail()
    } else {
      if (value.deleted_at !== null || !obj(value.stage) || !exact(value.stage, STAGE_FIELDS)) fail()
      const s = value.stage
      if (!['name', 'unit', 'status', 'work_method'].every(k => text(s[k]))
        || !(s.goal === null || number(s.goal)) || !number(s.personal_goal)
        || !['infinite', 'auto_freeze', 'streak_enabled'].every(k => typeof s[k] === 'boolean')
        || !['deadline', 'created_at', 'completed_at'].every(k => s[k] === null || text(s[k]))) fail()
    }
  }
}
export function encodeStructuralEvent(value: StructuralEvent): Uint8Array {
  validateStructuralEvent(value)
  const bytes = encoder.encode(canonical(value))
  if (bytes.length > MAX_STAGE_BYTES) fail()
  return bytes
}
export function frameStructuralEvent(value: StructuralEvent): Uint8Array {
  const bytes = encodeStructuralEvent(value), frame = new Uint8Array(20 + bytes.length)
  frame.set(MAGIC); frame.set([1, value.header.entity_type === 'stage' ? 2 : 3, value.version, 0], 8)
  const sizes = new DataView(frame.buffer)
  sizes.setUint32(12, bytes.length); sizes.setUint32(16, bytes.length); frame.set(bytes, 20)
  return frame
}
export function unframeStructuralEvent(frame: Uint8Array): StructuralEvent {
  if (frame.length < 20 || frame.length > MAX_STAGE_BYTES + 20 || !MAGIC.every((b, i) => frame[i] === b)
    || frame[8] !== 1 || ![2, 3].includes(frame[9]!) || ![1, 2].includes(frame[10]!) || frame[11] !== 0) fail()
  const sizes = new DataView(frame.buffer, frame.byteOffset, frame.byteLength)
  if (sizes.getUint32(12) !== frame.length - 20 || sizes.getUint32(16) !== frame.length - 20) fail()
  let parsed: unknown
  try { parsed = JSON.parse(decoder.decode(frame.subarray(20))) } catch { fail() }
  validateStructuralEvent(parsed)
  if (frame[10] !== parsed.version || canonical(parsed) !== decoder.decode(frame.subarray(20)) || frame[9] !== (parsed.header.entity_type === 'stage' ? 2 : 3)) fail()
  return parsed
}
export async function sealStructuralEvent(amk: AccountMasterKey, event: StructuralEvent): Promise<ObjectCryptoEnvelope> {
  const h = event.header
  return encryptObjectBytes(amk, { userId: h.account_id, projectId: h.project_id, entityId: h.entity_id, entityType: h.entity_type }, frameStructuralEvent(event))
}
export async function openStructuralEvent(amk: AccountMasterKey, context: { account_id: string; project_id: string; entity_id: string; entity_type: 'stage' | 'stage_order'; event_id: string }, envelope: ObjectCryptoEnvelope): Promise<StructuralEvent> {
  const bytes = await decryptObjectBytes(amk, { userId: context.account_id, projectId: context.project_id, entityId: context.entity_id, entityType: context.entity_type }, envelope)
  try {
    const event = unframeStructuralEvent(bytes)
    if (!Object.entries(context).every(([key, v]) => event.header[key as keyof StructuralHeader] === v)) fail()
    return event
  } finally { bytes.fill(0) }
}
