import { canonical, timestamp } from '@/cloud/projectMetadataCodec'
import { validateNoteSyncPlaintext, noteSyncEligibility, type NoteSyncRecord, type NoteSyncTombstone, type NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { decodeBase64Url } from '@/api/base64url'
import { BrowserPersistenceError } from './persistence'
import type { BrowserSyncScope } from './syncDurability'

export interface NativeLocalProject {
  id: string; name: string; goal: number | null; infinite: boolean; unit: string; status: string
  created_at: string | null; updated_at: string | null; payload: Record<string, unknown>
}
export interface NativeLegacyNote extends NoteSyncRecord { revision: number }
export type LocalNoteSource = { state: 'live'; note: NativeLegacyNote } | { state: 'tombstone'; note: NoteSyncTombstone; revision: number }
export interface LocalEnvelope { crypto_version: 1; aad_version: 1; nonce: string; ciphertext: string }
export interface LocalProjectRecord {
  record_version: 1; account_id: string; device_id: string; project_id: string
  source_revision: number; deleted: boolean; envelope: LocalEnvelope
}
export interface LocalNoteRecord {
  record_version: 1; account_id: string; device_id: string; project_id: string; note_id: string
  source_revision: number; note_revision: number; deleted: boolean; envelope: LocalEnvelope
}
export interface LocalProjectPayload {
  local_format: 1; kind: 'project'; account_id: string; device_id: string; project_id: string
  source_revision: number; deleted_at: string | null; project: NativeLocalProject; member_ids: string[]
}
export interface LocalNotePayload {
  local_format: 1; kind: 'note'; account_id: string; device_id: string; project_id: string; note_id: string
  source_revision: number; source: LocalNoteSource
}
export const MAX_LOCAL_SOURCE_BYTES = 8 * 1024 * 1024
export const MAX_LOCAL_NOTES = 4000
export function localFailure(code: 'invalid_local_source' | 'unsupported_local_source' | 'stale_source' | 'missing_local_source' | 'deleted_local_source' | 'conflicting_record' | 'corrupt_record' | 'source_limit' | 'closed' = 'invalid_local_source'): never { throw new BrowserPersistenceError(code) }
export function localExact(value: unknown, keys: string[]): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join(',') === [...keys].sort().join(',')
}
export function localId(value: unknown): asserts value is string {
  if (typeof value !== 'string' || !value.length || new TextEncoder().encode(value).length > 512 || /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)) localFailure()
}
export const localSafe = (value: unknown, min = 0): value is number => Number.isSafeInteger(value) && (value as number) >= min
function json(value: unknown, depth = 0): void {
  if (depth > 64) localFailure('source_limit')
  if (value === null || typeof value === 'string' || typeof value === 'boolean' || typeof value === 'number' && Number.isFinite(value)) return
  if (Array.isArray(value)) { for (let i = 0; i < value.length; i++) { if (!Object.hasOwn(value, i)) localFailure(); json(value[i], depth + 1) }; return }
  if (!value || typeof value !== 'object' || Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) localFailure()
  Object.values(value).forEach(v => json(v, depth + 1))
}
export function validateLocalProject(value: unknown): NativeLocalProject {
  if (!localExact(value, ['id','name','goal','infinite','unit','status','created_at','updated_at','payload'])) localFailure()
  const p = value as unknown as NativeLocalProject
  localId(p.id)
  if (![p.name,p.unit,p.status].every(v => typeof v === 'string' && v.length > 0) || typeof p.infinite !== 'boolean'
    || !(p.goal === null || typeof p.goal === 'number' && Number.isFinite(p.goal) && p.goal >= 0)
    || !(p.created_at === null || timestamp(p.created_at)) || !(p.updated_at === null || timestamp(p.updated_at))
    || !p.payload || typeof p.payload !== 'object' || Array.isArray(p.payload)) localFailure()
  json(p.payload)
  // A caller must not hide a partial import of another authority inside the project JSON.
  for (const key of ['notes','stages','mindmap','mind_map','documents','document','progress_entries','progress','game','game_data','cover_image','cover_reference','cover']) {
    const v = p.payload[key]
    if (v !== undefined && v !== null && v !== false && v !== 0 && v !== '' && !(Array.isArray(v) && v.length === 0) && !(typeof v === 'object' && Object.keys(v).length === 0)) localFailure('unsupported_local_source')
  }
  return structuredClone(p)
}
/** Content-only project HTML/plain route. Cloud codec and Legacy eligibility remain frozen. */
export function assertContentNoteRoute(note:NoteSyncRecord|NoteSyncTombstone):void {
 if(note.source_type!=='project'||note.source_map_id!==null||note.source_node_id!==null||!['html','plain'].includes(note.content_format))localFailure('unsupported_local_source')
 if(note.stage_id!==null)localId(note.stage_id)
}
export function validateLocalNote(value: unknown, project: string): LocalNoteSource {return validateNoteSource(value,project,false)}
export function validateContentLocalNote(value:unknown,project:string):LocalNoteSource{return validateNoteSource(value,project,true)}
/** Read existing encrypted source; write/capture callers still use validateLocalNote. No payload evolution. */
export function validatePersistedLocalNote(value:unknown,project:string):LocalNoteSource {
 const note=(value as LocalNoteSource)?.note
 // These routes cannot be produced by Legacy initialization, capture or mutation.
 return note?.stage_id!==null||note?.content_format==='plain'?validateContentLocalNote(value,project):validateLocalNote(value,project)
}
function validateNoteSource(value:unknown,project:string,content:boolean):LocalNoteSource {
  if (!value || typeof value !== 'object') localFailure()
  const s = value as LocalNoteSource
  if (!localExact(s, s.state === 'live' ? ['state','note'] : ['state','note','revision']) || !['live','tombstone'].includes(s.state)) localFailure()
  localId(s.note?.id); localId(project)
  if (s.note.project_id !== project) localFailure()
  const revision = s.state === 'live' ? s.note.revision : s.revision
  if (!localSafe(revision)) localFailure()
  let note: NoteSyncRecord | NoteSyncTombstone
  if (s.state === 'live') {
    if (!Object.hasOwn(s.note, 'revision')) localFailure()
    const { revision: _localRevision, ...record } = s.note
    note = record
    if (typeof record.title !== 'string' || typeof record.content !== 'string' || Array.from(record.title).length > 500 || Array.from(record.content).length > 300_000) localFailure()
    json(record.metadata)
  } else note = s.note
  const at = s.state === 'live' ? s.note.updated_at : s.note.deleted_at
  // Semantic validator view only. No cloud event is encoded, sealed, allocated or persisted.
  const view = { version: 1, header: { event_id: '00000000-0000-4000-8000-000000000000', parent_event_id: null, project_id: project, entity_id: s.note.id, entity_type: 'note', operation: s.state === 'live' ? 'upsert' : 'delete', revision: 1, updated_at: at, deleted_at: s.state === 'live' ? null : at }, mutation: s.state === 'live' ? 'create' : 'delete', note } as NoteSyncPlaintext
  try { validateNoteSyncPlaintext(view); if(content){assertContentNoteRoute(note);if(s.state==='live'&&Object.keys(s.note.metadata).length)localFailure('unsupported_local_source')}else if (!noteSyncEligibility(view).eligible) localFailure('unsupported_local_source') }
  catch (e) { if (e instanceof BrowserPersistenceError) throw e; localFailure() }
  return structuredClone(s)
}
export function validateLocalEnvelope(value: unknown): LocalEnvelope {
  if (!localExact(value, ['crypto_version','aad_version','nonce','ciphertext'])) localFailure('corrupt_record')
  const e = value as unknown as LocalEnvelope
  if (e.crypto_version !== 1 || e.aad_version !== 1) localFailure('corrupt_record')
  let nonce: Uint8Array | undefined, cipher: Uint8Array | undefined
  try { nonce = decodeBase64Url(e.nonce, { expectedLength: 24 }); cipher = decodeBase64Url(e.ciphertext, { minimumLength: 16, maximumLength: MAX_LOCAL_SOURCE_BYTES + 16 }) }
  catch { localFailure('corrupt_record') }
  finally { nonce?.fill(0); cipher?.fill(0) }
  return { ...e }
}
export function validateLocalProjectRecord(value: unknown, scope: BrowserSyncScope): LocalProjectRecord {
  if (!localExact(value, ['record_version','account_id','device_id','project_id','source_revision','deleted','envelope'])) localFailure('corrupt_record')
  const r = value as unknown as LocalProjectRecord
  localId(r.project_id)
  if (r.record_version !== 1 || r.account_id !== scope.accountId || r.device_id !== scope.deviceId || !localSafe(r.source_revision, 1) || typeof r.deleted !== 'boolean') localFailure('corrupt_record')
  return { ...r, envelope: validateLocalEnvelope(r.envelope) }
}
export function validateLocalNoteRecord(value: unknown, scope: BrowserSyncScope, project: string): LocalNoteRecord {
  if (!localExact(value, ['record_version','account_id','device_id','project_id','note_id','source_revision','note_revision','deleted','envelope'])) localFailure('corrupt_record')
  const r = value as unknown as LocalNoteRecord
  localId(r.note_id)
  if (r.record_version !== 1 || r.account_id !== scope.accountId || r.device_id !== scope.deviceId || r.project_id !== project || !localSafe(r.source_revision, 1) || !localSafe(r.note_revision) || typeof r.deleted !== 'boolean') localFailure('corrupt_record')
  return { ...r, envelope: validateLocalEnvelope(r.envelope) }
}
export function localCanonicalBytes(value: unknown): Uint8Array {
  json(value)
  const bytes = new TextEncoder().encode(canonical(value))
  if (bytes.length > MAX_LOCAL_SOURCE_BYTES) { bytes.fill(0); localFailure('source_limit') }
  return bytes
}
