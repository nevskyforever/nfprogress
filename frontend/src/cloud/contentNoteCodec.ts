import { normalizeAuthenticatedFrame } from './frameCompression'
import { canonical } from './projectMetadataCodec'
import { decodeNoteSyncPlaintext, encodeNoteSyncPlaintext, type NoteSyncPlaintext, type NoteSyncRecord, type NoteSyncTombstone } from './noteSyncCodec'
import { decodeNoteSyncResolutionV2, encodeNoteSyncResolutionV2, type NoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'
import { syncTimestampsEqual } from './syncTimestamp'
import { decryptObjectBytes, type AccountMasterKey, type ObjectCryptoEnvelope } from '@/crypto'

// Mode-3 note/operation=event is an explicit framed route, never legacy fallback.
export const CONTENT_NOTE_CODEC_ID = 8
export const MAX_CONTENT_NOTE_BYTES = 8 * 1024 * 1024 - 20
export type ContentNoteEvent = {
  version: 1; account_id: string; device_id: string
  dependencies: { bootstrap_id: string; metadata_event_id: string; stage_event_ids: string[] }
  event: NoteSyncPlaintext | NoteSyncResolutionV2
}
export class ContentNoteError extends Error {
  constructor(readonly code: string) { super(code) }
}
function fail(code = 'invalid_note_payload'): never { throw new ContentNoteError(code) }
const encoder = new TextEncoder(), decoder = new TextDecoder('utf-8', { fatal: true })
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const MAGIC = [87,79,82,84,65,45,67,49]
const obj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
const exact = (v: Record<string, unknown>, keys: string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v,k))
export function contentNoteRecord(e: ContentNoteEvent): NoteSyncRecord | NoteSyncTombstone {
  return e.event.version === 1 ? e.event.note : e.event.result.note
}
function boundedJson(v: unknown, depth = 0, budget = { left: 131072 }): void {
  if (--budget.left < 0 || depth > 12) fail('content_note_resource_limit')
  if (typeof v === 'string') {
    for (let i=0;i<v.length;i++) {
      const c=v.charCodeAt(i)
      if (c>=0xd800 && c<=0xdbff) { const n=v.charCodeAt(++i); if (!(n>=0xdc00 && n<=0xdfff)) fail() }
      else if (c>=0xdc00 && c<=0xdfff) fail()
    }
  } else if (Array.isArray(v)) v.forEach(x => boundedJson(x,depth+1,budget))
  else if (obj(v)) Object.values(v).forEach(x => boundedJson(x,depth+1,budget))
}
function portable(n: NoteSyncRecord | NoteSyncTombstone): void {
  if (n.source_type === 'mindmap') fail('content_note_map_owned')
  if (n.source_type !== 'project' || n.source_map_id !== null || n.source_node_id !== null) fail('content_note_unsupported_source')
  if (!['html','plain'].includes(n.content_format)) fail('unsupported_content_format')
  for (const id of [n.id,n.project_id,...(n.stage_id===null?[]:[n.stage_id])]) {
    if (typeof id !== 'string' || !id || encoder.encode(id).length>512) fail()
  }
  if ('content' in n) {
    if (Object.keys(n.metadata).length) fail('content_note_unsupported_source')
    if (encoder.encode(n.content).length>7*1024*1024 || encoder.encode(n.title).length>512*1024
      || n.tags.length>4096 || n.checklist.length>16384 || encoder.encode(n.color).length>512
      || n.tags.some(t=>encoder.encode(t).length>16384)
      || n.checklist.some(c=>encoder.encode(c.id).length>512 || encoder.encode(c.text).length>65536)) fail('content_note_resource_limit')
  }
}
export function validateContentNote(value: unknown): asserts value is ContentNoteEvent {
  if (!obj(value) || !exact(value,['version','account_id','device_id','dependencies','event']) || value.version!==1
    || typeof value.account_id!=='string' || !UUID.test(value.account_id) || typeof value.device_id!=='string' || !UUID.test(value.device_id)
    || !obj(value.dependencies) || !exact(value.dependencies,['bootstrap_id','metadata_event_id','stage_event_ids'])) fail()
  const d=value.dependencies
  if (![d.bootstrap_id,d.metadata_event_id].every(x=>typeof x==='string' && UUID.test(x)) || !Array.isArray(d.stage_event_ids)
    || d.stage_event_ids.length>64 || !d.stage_event_ids.every((x,i,a)=>typeof x==='string' && UUID.test(x) && (i===0 || x>a[i-1]))) fail()
  boundedJson(value)
  if (!obj(value.event)) fail()
  // Classify unsupported ownership/format before the frozen structural decoder.
  const raw = value.event.version===1 ? value.event.note : obj(value.event.result) ? value.event.result.note : null
  if (!obj(raw)) fail()
  if (raw.source_type==='mindmap') fail('content_note_map_owned')
  if (raw.source_type!=='project') fail('content_note_unsupported_source')
  if (!['html','plain'].includes(String(raw.content_format))) fail('unsupported_content_format')
  const bytes=encoder.encode(canonical(value.event))
  try {
    if (value.event.version===1) decodeNoteSyncPlaintext(bytes)
    else if (value.event.version===2) decodeNoteSyncResolutionV2(bytes)
    else fail('content_note_codec_unsupported')
  } catch (error) { if (error instanceof ContentNoteError) throw error; fail() }
  const e=value as unknown as ContentNoteEvent, n=contentNoteRecord(e)
  portable(n)
  if ((n.stage_id===null)!==(d.stage_event_ids.length===0)) fail()
  if (e.event.version===2 && e.event.resolution.strategy==='keep_both') {
    const retained=e.event.resolution.retained_note; portable(retained)
    if (retained.stage_id!==n.stage_id || retained.content_format!==n.content_format) fail('content_note_scope_mismatch')
  }
}
export function frameContentNote(e: ContentNoteEvent): Uint8Array {
  validateContentNote(e)
  // Keep embedded C15/C17 serializers byte-exact, including their validation.
  if (e.event.version===1) encodeNoteSyncPlaintext(e.event); else encodeNoteSyncResolutionV2(e.event)
  const payload=encoder.encode(canonical(e)); if (payload.length>MAX_CONTENT_NOTE_BYTES) fail('content_note_resource_limit')
  const frame=new Uint8Array(20+payload.length); frame.set(MAGIC); frame.set([1,8,1,0],8)
  const sizes=new DataView(frame.buffer); sizes.setUint32(12,payload.length); sizes.setUint32(16,payload.length); frame.set(payload,20)
  return frame
}
export function unframeContentNote(frame: Uint8Array): ContentNoteEvent {
  if (frame.length >= 20 && frame[11] !== 0 && [8].includes(frame[9]!) && [1].includes(frame[10]!)) frame = normalizeAuthenticatedFrame(frame, [8], [1], MAX_CONTENT_NOTE_BYTES)

  if (frame.length>MAX_CONTENT_NOTE_BYTES+20) fail('content_note_resource_limit')
  if (frame.length<20 || !MAGIC.every((b,i)=>frame[i]===b) || frame[8]!==1 || frame[9]!==8 || frame[10]!==1 || frame[11]!==0) fail('content_note_codec_unsupported')
  const sizes=new DataView(frame.buffer,frame.byteOffset,frame.byteLength)
  if (sizes.getUint32(12)!==frame.length-20 || sizes.getUint32(16)!==frame.length-20) fail()
  let text: string, value: unknown
  try { text=decoder.decode(frame.subarray(20)); value=JSON.parse(text) } catch { fail() }
  validateContentNote(value); if (canonical(value)!==text) fail(); return value
}
export async function openContentNote(amk: AccountMasterKey, context: { account_id:string; project_id:string; entity_id:string; event_id:string; device_id:string; revision:number; updated_at:string }, envelope: ObjectCryptoEnvelope): Promise<Uint8Array> {
  const frame=await decryptObjectBytes(amk,{userId:context.account_id,projectId:context.project_id,entityId:context.entity_id,entityType:'note'},envelope)
  try {
    const e=unframeContentNote(frame), h=e.event.header
    if (e.account_id!==context.account_id || e.device_id!==context.device_id || h.project_id!==context.project_id || h.entity_id!==context.entity_id
      || h.event_id!==context.event_id || h.revision!==context.revision || !syncTimestampsEqual(h.updated_at,context.updated_at)) fail('content_note_scope_mismatch')
    return frame
  } catch (error) { frame.fill(0); throw error }
}
