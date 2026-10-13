import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import type { NoteSyncHeader } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError } from './persistence'
import { localExact,localId,localSafe,validateLocalNoteRecord,type LocalNoteRecord } from './localAuthorityRecords'
import { immutableWireIdentity,validateBrowserSealedBody,type BrowserSyncScope } from './syncDurability'
export const NOTE_HISTORY_STORE='legacyNoteHistory'
interface Base {record_version:1;account_id:string;device_id:string;project_id:string;note_id:string;bootstrap_id:string;record_kind:'candidate'|'head'|'group';record_id:string}
export interface BrowserNoteCandidate extends Base {
 record_kind:'candidate';event_id:string;source_device_id:string;protocol_version:2|3
 origin:'initial_capture'|'initial_backfill'|'peer'|'local_sealed';mutation_generation:number|null
 header:NoteSyncHeader;wire_item:string;wire_digest:string;record_digest:string
 projection:LocalNoteRecord|null;projection_digest:string|null
}
export interface BrowserNoteHead extends Base {record_kind:'head';record_id:'head';head_revision:number;linear_head_event_id:string;tip_event_ids:string[]}
export interface BrowserNoteConflictMember {version_id:string;event_id:string;source:'remote_applied'|'remote';server_sequence:number;conflict_generation:number}
export interface BrowserNoteConflictGroup extends Base {record_kind:'group';group_id:string;common_parent_event_id:string;tip_revision:number;conflict_generation:number;lifecycle:'open';members:BrowserNoteConflictMember[];tip_event_ids:string[]}
export type BrowserNoteHistoryRecord=BrowserNoteCandidate|BrowserNoteHead|BrowserNoteConflictGroup
const base=['record_version','account_id','device_id','project_id','note_id','bootstrap_id','record_kind','record_id']
export const canonicalNoteUuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
export const noteHistoryHash=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
function bad():never{throw new BrowserPersistenceError('corrupt_record')}
function tips(v:unknown):v is string[]{return Array.isArray(v)&&v.length>0&&v.every(canonicalNoteUuid)&&v.every((id,i)=>i===0||v[i-1]!<id)}
export function validateNoteHistoryRecord(value:unknown,scope:BrowserSyncScope):BrowserNoteHistoryRecord {
 const r=value as BrowserNoteHistoryRecord
 if(!r||r.record_version!==1||r.account_id!==scope.accountId||r.device_id!==scope.deviceId||!canonicalNoteUuid(r.bootstrap_id))bad();localId(r.project_id);localId(r.note_id)
 if(r.record_kind==='candidate'){
  if(!localExact(r,[...base,'event_id','source_device_id','protocol_version','origin','mutation_generation','header','wire_item','wire_digest','record_digest','projection','projection_digest'])||r.record_id!==r.event_id||!canonicalNoteUuid(r.event_id)||!canonicalNoteUuid(r.source_device_id)||![2,3].includes(r.protocol_version)||!['initial_capture','initial_backfill','peer','local_sealed'].includes(r.origin)||!noteHistoryHash(r.wire_digest)||!noteHistoryHash(r.record_digest))bad()
  if(r.origin==='peer'?r.source_device_id===scope.deviceId||r.mutation_generation!==null:r.source_device_id!==scope.deviceId||(r.origin==='local_sealed'?!localSafe(r.mutation_generation,1):r.mutation_generation!==1))bad()
  const h=r.header
  if(!localExact(h,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.note_id||h.entity_type!=='note'||!localSafe(h.revision,1)||(h.revision===1)!==(h.parent_event_id===null)||h.parent_event_id!==null&&!canonicalNoteUuid(h.parent_event_id)||h.parent_event_id===h.event_id)bad()
  if(['initial_capture','initial_backfill'].includes(r.origin)&&(h.revision!==1||h.parent_event_id!==null||h.operation!=='upsert'))bad()
  let wire:unknown;try{wire=JSON.parse(r.wire_item)}catch{bad()}
  validateBrowserSealedBody(JSON.stringify({protocol_version:r.protocol_version,encrypted_sync_version:r.protocol_version,device_id:r.source_device_id,items:[wire]}),{...scope,deviceId:r.source_device_id})
  const event=(wire as {event:NoteSyncHeader}).event
  if(event.entity_type!=='note'||!['upsert','delete'].includes(event.operation)||event.event_id!==h.event_id||event.project_id!==h.project_id||event.entity_id!==h.entity_id||event.revision!==h.revision||event.operation!==h.operation||canonicalizeSyncTimestamp(event.updated_at)!==canonicalizeSyncTimestamp(h.updated_at)||(event.deleted_at===null)!==(h.deleted_at===null)||event.deleted_at!==null&&canonicalizeSyncTimestamp(event.deleted_at)!==canonicalizeSyncTimestamp(h.deleted_at!))bad()
  if(r.projection!==null){const p=validateLocalNoteRecord(r.projection,scope,r.project_id);if(p.note_id!==r.note_id||!noteHistoryHash(r.projection_digest))bad()}else if(r.projection_digest!==null&&!noteHistoryHash(r.projection_digest))bad()
  if(['initial_capture','local_sealed'].includes(r.origin)&&r.projection===null||r.origin==='initial_backfill'&&(r.projection!==null||r.projection_digest!==null))bad()
 }else if(r.record_kind==='head'){
  if(!localExact(r,[...base,'head_revision','linear_head_event_id','tip_event_ids'])||r.record_id!=='head'||!localSafe(r.head_revision,1)||!canonicalNoteUuid(r.linear_head_event_id)||!tips(r.tip_event_ids))bad()
 }else if(r.record_kind==='group'){
  if(!localExact(r,[...base,'group_id','common_parent_event_id','tip_revision','conflict_generation','lifecycle','members','tip_event_ids'])||r.record_id!==r.group_id||!canonicalNoteUuid(r.group_id)||r.group_id[14]!=='4'||!canonicalNoteUuid(r.common_parent_event_id)||!localSafe(r.tip_revision,2)||!localSafe(r.conflict_generation,1)||r.lifecycle!=='open'||!tips(r.tip_event_ids)||r.tip_event_ids.length<2||!Array.isArray(r.members)||r.members.length!==r.tip_event_ids.length)bad()
  r.members.forEach((m,i)=>{if(!localExact(m,['version_id','event_id','source','server_sequence','conflict_generation'])||m.event_id!==r.tip_event_ids[i]||!['remote_applied','remote'].includes(m.source)||!localSafe(m.server_sequence,1)||!localSafe(m.conflict_generation,1)||m.conflict_generation>r.conflict_generation||m.version_id!==`${m.source==='remote'?'remote':'applied'}:${scope.accountId}:${m.event_id}`)bad()})
  if(r.members.filter(m=>m.source==='remote_applied').length!==1||r.members.filter(m=>m.conflict_generation===1).length!==2||r.members.length!==r.conflict_generation+1||r.members.filter(m=>m.source==='remote_applied').some(m=>m.conflict_generation!==1))bad()
  for(let n=2;n<=r.conflict_generation;n++)if(r.members.filter(m=>m.conflict_generation===n).length!==1)bad()
 }else bad()
 return r
}
export function noteFrontier(candidates:BrowserNoteCandidate[]):string[]{const parents=new Set(candidates.map(c=>c.header.parent_event_id));return candidates.filter(c=>!parents.has(c.event_id)).map(c=>c.event_id).sort()}
export function validateNoteHistorySet(scope:BrowserSyncScope,values:unknown[]):BrowserNoteHistoryRecord[]{
 const rows=values.map(v=>validateNoteHistoryRecord(v,scope)),keys=new Set<string>(),events=new Set<string>(),groupNotes=new Set<string>()
 for(const r of rows){const key=immutableWireIdentity([r.project_id,r.note_id,r.record_kind,r.record_id]);if(keys.has(key))bad();keys.add(key);if(r.record_kind==='group'){const owner=immutableWireIdentity([r.project_id,r.note_id]);if(groupNotes.has(owner))bad();groupNotes.add(owner)}if(r.record_kind==='candidate'){if(events.has(r.event_id))bad();events.add(r.event_id)}}
 const candidates=rows.filter((r):r is BrowserNoteCandidate=>r.record_kind==='candidate')
 for(const r of rows){const own=candidates.filter(c=>c.project_id===r.project_id&&c.note_id===r.note_id&&c.bootstrap_id===r.bootstrap_id)
  if(r.record_kind==='candidate'&&r.header.revision>1){const parent=own.find(c=>c.event_id===r.header.parent_event_id);if(!parent||parent.header.revision!==r.header.revision-1)bad()}
  if(r.record_kind==='head'){if(!own.some(c=>c.event_id===r.linear_head_event_id)||immutableWireIdentity(noteFrontier(own))!==immutableWireIdentity(r.tip_event_ids))bad()}
  if(r.record_kind==='group'){if(!own.some(c=>c.event_id===r.common_parent_event_id))bad();for(const m of r.members){const c=own.find(c=>c.event_id===m.event_id);if(!c||c.header.parent_event_id!==r.common_parent_event_id||c.header.revision!==r.tip_revision)bad()}}
 }
 return rows
}
