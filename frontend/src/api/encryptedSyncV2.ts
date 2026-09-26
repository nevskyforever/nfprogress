import { decodeBase64Url, encodeBase64Url } from './base64url'
import { apiRequest } from './client'
import { MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES, MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES, MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES } from './encryptedSync'
import { parseSyncTimestamp } from '@/cloud/syncTimestamp'

export const V2_SYNC_PROTOCOL_VERSION = 2 as const
const MAX_SAFE = Number.MAX_SAFE_INTEGER
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
export interface V2Capabilities { supported_transport_version: 2, writer_transport_version: 1 | 2, cutover_epoch: number }
export interface V2ResolutionPushItem { event: { event_id:string, project_id:string, entity_id:string, entity_type:'note', operation:'resolution', revision:number, updated_at:string, deleted_at:null }, object: { crypto_version:1, aad_version:1, nonce:string, ciphertext:string } }
export interface V2PushRequest { protocol_version:2, encrypted_sync_version:2, device_id:string, items: V2ResolutionPushItem[] }
export interface V2PushResponse { protocol_version:2, encrypted_sync_version:2, results:Array<{event_id:string,server_sequence:number,duplicate:boolean}>, current_cursor:number }
const fail = (): never => { throw new TypeError('Invalid encrypted sync v2 payload.') }
const keys = (v: unknown, k: readonly string[]) => typeof v === 'object' && v !== null && Object.keys(v).length === k.length && k.every(key => Object.prototype.hasOwnProperty.call(v, key))
function uuid(v: unknown): string { if (typeof v !== 'string') throw new TypeError('Invalid encrypted sync v2 UUID.'); if (!UUID.test(v)) throw new TypeError('Invalid encrypted sync v2 UUID.'); return v.toLowerCase() }
const safe = (v: unknown, min: number): number => { if (!Number.isSafeInteger(v)) fail(); const number = v as number; if (number < min || number > MAX_SAFE) fail(); return number }
const boundedText = (v: unknown, maximum: number): v is string => typeof v === 'string' && v.length >= 1 && v.length <= maximum
const headers = (token:string) => new Headers({ Authorization:`Bearer ${token}`, 'Content-Type':'application/json' })

export function parseV2Capabilities(value: unknown): V2Capabilities {
  if (!keys(value,['supported_transport_version','writer_transport_version','cutover_epoch'])) fail()
  const v=value as V2Capabilities
  if (v.supported_transport_version!==2 || (v.writer_transport_version!==1 && v.writer_transport_version!==2)) fail()
  safe(v.cutover_epoch,0); return v
}
export function encodeV2Push(request: V2PushRequest): string {
  if (request.protocol_version!==2 || request.encrypted_sync_version!==2 || !Array.isArray(request.items) || request.items.length<1 || request.items.length>100) fail()
  if(uuid(request.device_id)!==request.device_id)fail(); let total=0; const eventIds=new Set<string>()
  for (const item of request.items) {
    if (!keys(item,['event','object']) || !keys(item.event,['event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at']) || !keys(item.object,['crypto_version','aad_version','nonce','ciphertext'])) fail()
    const e=item.event; const eventId=uuid(e.event_id); if (eventId!==e.event_id || eventIds.has(eventId) || !boundedText(e.project_id,512) || !boundedText(e.entity_id,512) || e.entity_type!=='note' || e.operation!=='resolution' || !Number.isSafeInteger(e.revision) || e.revision<2 || typeof e.updated_at!=='string' || e.deleted_at!==null) fail()
    eventIds.add(eventId); try { parseSyncTimestamp(e.updated_at) } catch { fail() }
    const o=item.object; if (o.crypto_version!==1 || o.aad_version!==1) fail()
    const nonce=decodeBase64Url(o.nonce,{expectedLength:24}); const ciphertext=decodeBase64Url(o.ciphertext,{minimumLength:16,maximumLength:MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES});
    if (encodeBase64Url(nonce)!==o.nonce || encodeBase64Url(ciphertext)!==o.ciphertext) fail(); total+=ciphertext.byteLength; if(total>MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES) fail()
  }
  const body=JSON.stringify(request); if(new TextEncoder().encode(body).byteLength>MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES) throw new RangeError('Encrypted sync v2 request exceeds wire limit.'); return body
}
export function parseV2PushResponse(value: unknown, expected: readonly string[]): V2PushResponse {
  if(!keys(value,['protocol_version','encrypted_sync_version','results','current_cursor'])) fail(); const r=value as V2PushResponse
  if(r.protocol_version!==2||r.encrypted_sync_version!==2||!Array.isArray(r.results)) fail(); safe(r.current_cursor,0)
  const want=new Set(expected.map(uuid)); if(r.results.length!==want.size) fail(); const seq=new Set<number>()
  for(const row of r.results){if(!keys(row,['event_id','server_sequence','duplicate']))fail();const id=uuid(row.event_id);const n=safe(row.server_sequence,1);if(id!==row.event_id||!want.delete(id)||seq.has(n)||typeof row.duplicate!=='boolean'||r.current_cursor<n)fail();seq.add(n)}
  if(want.size)fail(); return r
}
export const encryptedSyncV2Api={
  capabilities:(token:string)=>apiRequest<unknown>('/api/v2/sync/encrypted/capabilities',{headers:headers(token)}).then(parseV2Capabilities),
  push:(token:string,request:V2PushRequest)=>apiRequest<unknown>('/api/v2/sync/encrypted/push',{method:'POST',headers:headers(token),rawBody:encodeV2Push(request)}).then(value=>parseV2PushResponse(value,request.items.map(i=>i.event.event_id))),
}
