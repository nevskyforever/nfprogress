import {validateContentCandidate3,type BrowserContentCandidate3} from './contentAuthorityRecords'
import { validateNoteIntent,type BrowserNoteIntent } from './noteIntentRecords'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import type { NoteSyncHeader } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError } from './persistence'
import { localExact,localId,localSafe,validateLocalNoteRecord,type LocalNoteRecord } from './localAuthorityRecords'
import { immutableWireIdentity,validateBrowserSealedBody,type BrowserSyncScope } from './syncDurability'
export const NOTE_HISTORY_STORE='legacyNoteHistory'
interface Base {record_version:1;account_id:string;device_id:string;project_id:string;note_id:string;bootstrap_id:string;record_kind:'candidate'|'head'|'group'|'local_version';record_id:string}
interface NoteCandidateFields extends Omit<Base,'record_version'> {
 record_kind:'candidate';event_id:string;source_device_id:string;protocol_version:2|3
 origin:'initial_capture'|'initial_backfill'|'peer'|'local_sealed';mutation_generation:number|null
 header:NoteSyncHeader;wire_item:string;wire_digest:string;record_digest:string
 projection:LocalNoteRecord|null;projection_digest:string|null
}
export type BrowserNoteCandidate = (NoteCandidateFields & (
 {record_version:1;transport_kind?:never;server_sequence?:never;transport_proof?:never} |
 {record_version:2;transport_kind:'content_note_v1';server_sequence:number;transport_proof:BrowserNoteTransportProof}
)) | BrowserContentCandidate3
/** Internal transport evidence; final applied/conflict inbox proof is additionally required. */
interface NoteTransportProofFields {
 proof_kind:'content_note_v1_prerequisite';logical_digest:string;wire_digest:string;
 dependency_digest:string;proof_digest:string
}
export type BrowserNoteTransportProof=NoteTransportProofFields & ({outcome:'applied';source_revision:number;local_note_digest:string}|{outcome:'conflict_preserved';source_revision:null;local_note_digest:null})
export interface BrowserNoteLocalVersion extends Base {record_kind:'local_version';version_id:string;header:NoteSyncHeader;intent:BrowserNoteIntent;local_outbox_lifecycle:'unsealed';record_digest:string}
export interface BrowserNoteHead extends Base {record_kind:'head';record_id:'head';head_revision:number;linear_head_event_id:string;tip_event_ids:string[]}
export type BrowserNoteConflictMember={version_id:string;event_id:string;source:'remote_applied'|'remote';server_sequence:number;conflict_generation:number}|{version_id:string;event_id:string;source:'local_unsealed';server_sequence:null;conflict_generation:1;local_mutation_generation:number}
export interface BrowserNoteConflictGroup extends Base {record_kind:'group';group_id:string;common_parent_event_id:string;tip_revision:number;conflict_generation:number;lifecycle:'open';members:BrowserNoteConflictMember[];tip_event_ids:string[]}
export type BrowserNoteHistoryRecord=BrowserNoteCandidate|BrowserNoteHead|BrowserNoteConflictGroup|BrowserNoteLocalVersion
const base=['record_version','account_id','device_id','project_id','note_id','bootstrap_id','record_kind','record_id']
export const canonicalNoteUuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v)
export const noteHistoryHash=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
function bad():never{throw new BrowserPersistenceError('corrupt_record')}
function tips(v:unknown):v is string[]{return Array.isArray(v)&&v.length>0&&v.every(canonicalNoteUuid)&&v.every((id,i)=>i===0||v[i-1]!<id)}
export function validateNoteHistoryRecord(value:unknown,scope:BrowserSyncScope):BrowserNoteHistoryRecord {
 if((value as {record_version?:number})?.record_version===3)return validateContentCandidate3(value,scope)
 const r=value as Exclude<BrowserNoteHistoryRecord,BrowserContentCandidate3>
 if(!r||![1,2].includes(r.record_version)||r.record_version===2&&r.record_kind!=='candidate'||r.account_id!==scope.accountId||r.device_id!==scope.deviceId||!canonicalNoteUuid(r.bootstrap_id))bad();localId(r.project_id);localId(r.note_id)
 if(r.record_kind==='candidate'){
  if(!localExact(r,[...base,'event_id','source_device_id','protocol_version','origin','mutation_generation','header','wire_item','wire_digest','record_digest','projection','projection_digest',...(r.record_version===2?['transport_kind','server_sequence','transport_proof']:[])])||r.record_id!==r.event_id||!canonicalNoteUuid(r.event_id)||!canonicalNoteUuid(r.source_device_id)||![2,3].includes(r.protocol_version)||!['initial_capture','initial_backfill','peer','local_sealed'].includes(r.origin)||!noteHistoryHash(r.wire_digest)||!noteHistoryHash(r.record_digest))bad()
  if(r.origin==='peer'?r.source_device_id===scope.deviceId||r.mutation_generation!==null:r.source_device_id!==scope.deviceId||(r.origin==='local_sealed'?!localSafe(r.mutation_generation,1):r.mutation_generation!==1))bad()
  const h=r.header
  if(!localExact(h,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.note_id||h.entity_type!=='note'||!localSafe(h.revision,1)||(h.revision===1)!==(h.parent_event_id===null)||h.parent_event_id!==null&&!canonicalNoteUuid(h.parent_event_id)||h.parent_event_id===h.event_id)bad()
  if(['initial_capture','initial_backfill'].includes(r.origin)&&(h.revision!==1||h.parent_event_id!==null||h.operation!=='upsert'))bad()
  let wire:unknown;try{wire=JSON.parse(r.wire_item)}catch{bad()}
  const retained=wire as {event:NoteSyncHeader&{device_id?:string;server_sequence?:number};object:unknown},event=retained.event
  if(r.record_version===2){
   const p=r.transport_proof
   if(r.transport_kind!=='content_note_v1'||r.protocol_version!==3||r.origin!=='peer'||!localSafe(r.server_sequence,1)||event.device_id!==r.source_device_id||event.server_sequence!==r.server_sequence||(event.operation as string)!=='event'||event.deleted_at!==null||!p||!localExact(p,['proof_kind','logical_digest','wire_digest','dependency_digest','outcome','source_revision','local_note_digest','proof_digest'])||p.proof_kind!=='content_note_v1_prerequisite'||!['applied','conflict_preserved'].includes(p.outcome)||![p.logical_digest,p.wire_digest,p.dependency_digest,p.proof_digest].every(noteHistoryHash)||p.wire_digest!==r.wire_digest)bad()
   if(p.outcome==='applied'){if(!localSafe(p.source_revision,1)||!noteHistoryHash(p.local_note_digest)||p.local_note_digest!==r.projection_digest||r.projection?.source_revision!==p.source_revision)bad()}else if(r.projection!==null||r.projection_digest!==null||p.source_revision!==null||p.local_note_digest!==null||h.revision<2)bad()
   const {device_id:_device,server_sequence:_seq,...descriptor}=event
   validateBrowserSealedBody(JSON.stringify({protocol_version:3,encrypted_sync_version:3,device_id:r.source_device_id,items:[{event:descriptor,object:retained.object}]}),{...scope,deviceId:r.source_device_id})
  }else{
   validateBrowserSealedBody(JSON.stringify({protocol_version:r.protocol_version,encrypted_sync_version:r.protocol_version,device_id:r.source_device_id,items:[wire]}),{...scope,deviceId:r.source_device_id})
   if(!['upsert','delete'].includes(event.operation)||event.operation!==h.operation||(event.deleted_at===null)!==(h.deleted_at===null)||event.deleted_at!==null&&canonicalizeSyncTimestamp(event.deleted_at)!==canonicalizeSyncTimestamp(h.deleted_at!))bad()
  }
  if(event.entity_type!=='note'||event.event_id!==h.event_id||event.project_id!==h.project_id||event.entity_id!==h.entity_id||event.revision!==h.revision||canonicalizeSyncTimestamp(event.updated_at)!==canonicalizeSyncTimestamp(h.updated_at)||!['upsert','delete'].includes(h.operation)||(h.operation==='delete')!==(h.deleted_at!==null))bad()
  if(r.projection!==null){const p=validateLocalNoteRecord(r.projection,scope,r.project_id);if(p.note_id!==r.note_id||!noteHistoryHash(r.projection_digest))bad()}else if(r.projection_digest!==null&&!noteHistoryHash(r.projection_digest))bad()
  if(['initial_capture','local_sealed'].includes(r.origin)&&r.projection===null||r.origin==='initial_backfill'&&(r.projection!==null||r.projection_digest!==null))bad()
 }else if(r.record_kind==='local_version'){
  if(!localExact(r,[...base,'version_id','header','intent','local_outbox_lifecycle','record_digest'])||r.record_id!==r.version_id||r.local_outbox_lifecycle!=='unsealed'||!noteHistoryHash(r.record_digest))bad()
  const i=validateNoteIntent(r.intent,scope),h=r.header
  if(i.project_id!==r.project_id||i.note_id!==r.note_id||i.bootstrap_id!==r.bootstrap_id||r.version_id!==`local:${scope.accountId}:${i.event_id}:${i.mutation_generation}`||!localExact(h,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||h.event_id!==i.event_id||h.parent_event_id!==i.parent_event_id||h.project_id!==i.project_id||h.entity_id!==i.note_id||h.entity_type!=='note'||h.operation!==i.operation||h.revision!==i.revision||h.revision<2||h.parent_event_id===null||canonicalizeSyncTimestamp(h.updated_at)!==canonicalizeSyncTimestamp(i.updated_at)||(h.deleted_at===null)!==(i.deleted_at===null)||h.deleted_at!==null&&canonicalizeSyncTimestamp(h.deleted_at)!==canonicalizeSyncTimestamp(i.deleted_at!))bad()
 }else if(r.record_kind==='head'){
  if(!localExact(r,[...base,'head_revision','linear_head_event_id','tip_event_ids'])||r.record_id!=='head'||!localSafe(r.head_revision,1)||!canonicalNoteUuid(r.linear_head_event_id)||!tips(r.tip_event_ids))bad()
 }else if(r.record_kind==='group'){
  if(!localExact(r,[...base,'group_id','common_parent_event_id','tip_revision','conflict_generation','lifecycle','members','tip_event_ids'])||r.record_id!==r.group_id||!canonicalNoteUuid(r.group_id)||r.group_id[14]!=='4'||!canonicalNoteUuid(r.common_parent_event_id)||!localSafe(r.tip_revision,2)||!localSafe(r.conflict_generation,1)||r.lifecycle!=='open'||!tips(r.tip_event_ids)||r.tip_event_ids.length<2||!Array.isArray(r.members)||r.members.length!==r.tip_event_ids.length)bad()
  r.members.forEach((m,i)=>{if(m.source==='local_unsealed'){if(!localExact(m,['version_id','event_id','source','server_sequence','conflict_generation','local_mutation_generation'])||m.server_sequence!==null||m.conflict_generation!==1||!localSafe(m.local_mutation_generation,1)||m.version_id!==`local:${scope.accountId}:${m.event_id}:${m.local_mutation_generation}`)bad()}else if(!localExact(m,['version_id','event_id','source','server_sequence','conflict_generation'])||!['remote_applied','remote'].includes(m.source)||!localSafe(m.server_sequence,1)||m.version_id!==`${m.source==='remote'?'remote':'applied'}:${scope.accountId}:${m.event_id}`)bad();if(m.event_id!==r.tip_event_ids[i]||!canonicalNoteUuid(m.event_id)||!localSafe(m.conflict_generation,1)||m.conflict_generation>r.conflict_generation)bad()})
  if(r.members.filter(m=>m.source!=='remote').length!==1||r.members.filter(m=>m.conflict_generation===1).length!==2||r.members.length!==r.conflict_generation+1||r.members.some(m=>m.source!=='remote'&&m.conflict_generation!==1))bad()
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
  if(r.record_kind==='local_version'){const parent=own.find(c=>c.event_id===r.header.parent_event_id);if(!parent||parent.header.revision!==r.header.revision-1)bad()}
  if(r.record_kind==='group'){if(!own.some(c=>c.event_id===r.common_parent_event_id))bad();for(const m of r.members){const c=m.source==='local_unsealed'?rows.find((v):v is BrowserNoteLocalVersion=>v.record_kind==='local_version'&&v.version_id===m.version_id&&v.project_id===r.project_id&&v.note_id===r.note_id&&v.bootstrap_id===r.bootstrap_id):own.find(c=>c.event_id===m.event_id);if(!c||c.record_kind==='candidate'&&c.record_version===3||c.header.parent_event_id!==r.common_parent_event_id||c.header.revision!==r.tip_revision)bad()}}
 }
 return rows
}
