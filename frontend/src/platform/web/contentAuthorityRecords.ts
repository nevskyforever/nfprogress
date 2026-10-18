import type {NoteSyncHeader} from '@/cloud/noteSyncCodec'
import type {V3Descriptor} from '@/api/encryptedSyncV3'
import {timestamp,canonical} from '@/cloud/projectMetadataCodec'
import {BrowserPersistenceError} from './persistence'
import {localExact,localId,localSafe,validateLocalEnvelope,validateLocalNoteRecord,MAX_LOCAL_SOURCE_BYTES,type LocalEnvelope} from './localAuthorityRecords'
import {canonicalNoteUuid,noteHistoryHash} from './noteHistoryRecords'
import {sealFailureState,type BrowserNoteIntent} from './noteIntentRecords'
import {validateBrowserSealedBody,validateBrowserUploadPair,immutableWireIdentity,type BrowserSyncScope,type BrowserOutboxRecord,type BrowserUploadReceipt} from './syncDurability'

export interface BrowserContentIntent2 extends Omit<BrowserNoteIntent,'record_version'> {
 record_version:2;transport_kind:'content_note_v1'
 dependencies:{bootstrap_id:string;metadata_event_id:string;stage_event_ids:string[]}
}
export interface BrowserContentCandidate3 {
 record_version:3;record_kind:'candidate';record_id:string;account_id:string;device_id:string;project_id:string;note_id:string;bootstrap_id:string;event_id:string
 source_device_id:string;protocol_version:3;transport_kind:'content_note_v1';origin:'local_sealed';codec_id:8;frame_version:1;codec_version:1;compression_id:0|1
 header:NoteSyncHeader;intent:BrowserContentIntent2;wire_item:string;wire_digest:string;raw_body_digest:string;logical_digest:string;authorship_envelope:LocalEnvelope;record_digest:string
 // These old-family fields are deliberately absent, never synthesized in storage.
 projection?:never;projection_digest?:never;mutation_generation?:never;transport_proof?:never;server_sequence?:never
}
export interface BrowserContentReceipt2 {
 record_version:2;owner_kind:'content_note_acceptance';account_id:string;device_id:string;event_id:string;protocol_version:3;server_sequence:number;duplicate:boolean
 candidate_digest:string;wire_digest:string;acceptance_envelope:LocalEnvelope;receipt_digest:string
}
export interface BrowserContentSelfEchoProof2 {
 record_version:2;owner_kind:'content_note_self_echo';outcome:'acknowledged';account_id:string;device_id:string;bootstrap_id:string;protocol_version:3
 reference:V3Descriptor;server_sequence:number;codec_id:8;frame_version:1;codec_version:1;header:NoteSyncHeader;mutation:'create'|'update'|'delete'
 history_event_id:string;candidate_digest:string;wire_digest:string;receipt_digest:string;outcome_digest:string
}
export type BrowserAnyNoteIntent=BrowserNoteIntent|BrowserContentIntent2
export type BrowserAnyUploadReceipt=BrowserUploadReceipt|BrowserContentReceipt2
export function contentAuthorityCorrupt():never{throw new BrowserPersistenceError('corrupt_record')}
function bad():never{return contentAuthorityCorrupt()}
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
export function boundedContentRecord(value:unknown):void{try{if(new TextEncoder().encode(canonical(value)).length>MAX_LOCAL_SOURCE_BYTES)bad()}catch{bad()}}
function identity(r:{account_id:string;device_id:string;event_id:string},s:BrowserSyncScope){if(r.account_id!==s.accountId||r.device_id!==s.deviceId||!canonicalNoteUuid(r.event_id)||r.event_id[14]!=='4')bad()}
function header(v:unknown):NoteSyncHeader{
 if(!localExact(v,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at']))bad()
 const h=v as unknown as NoteSyncHeader;localId(h.project_id);localId(h.entity_id)
 if(!canonicalNoteUuid(h.event_id)||h.event_id[14]!=='4'||h.entity_type!=='note'||!localSafe(h.revision,1)||(h.revision===1)!==(h.parent_event_id===null)||h.parent_event_id!==null&&(!canonicalNoteUuid(h.parent_event_id)||h.parent_event_id===h.event_id)||!['upsert','delete'].includes(h.operation)||h.operation==='delete'&&h.revision===1||!timestamp(h.updated_at)||(h.operation==='delete')!==(h.deleted_at!==null)||h.deleted_at!==null&&h.deleted_at!==h.updated_at)bad()
 return h
}
export function contentIntentIdentity(r:BrowserContentIntent2){const {seal_state:_s,seal_attempt_count:_a,last_error_code:_e,next_attempt_at:_n,intent_envelope:_i,...value}=r;return value}
export function validateContentIntent2(value:unknown,s:BrowserSyncScope):BrowserContentIntent2{
 boundedContentRecord(value)
 if(!localExact(value,['record_version','transport_kind','account_id','device_id','project_id','note_id','bootstrap_id','event_id','operation','revision','parent_event_id','updated_at','deleted_at','local_ordinal','mutation_generation','dependencies','snapshot','snapshot_digest','intent_envelope','seal_state','seal_attempt_count','last_error_code','next_attempt_at']))bad()
 const r=value as unknown as BrowserContentIntent2;identity(r,s);localId(r.project_id);localId(r.note_id)
 if(r.record_version!==2||r.transport_kind!=='content_note_v1'||!canonicalNoteUuid(r.bootstrap_id)||r.bootstrap_id[14]!=='4'||!localSafe(r.local_ordinal,1)||!localSafe(r.mutation_generation,1)||!localSafe(r.seal_attempt_count)||!noteHistoryHash(r.snapshot_digest)||r.next_attempt_at!==null)bad()
 header({event_id:r.event_id,parent_event_id:r.parent_event_id,project_id:r.project_id,entity_id:r.note_id,entity_type:'note',operation:r.operation,revision:r.revision,updated_at:r.updated_at,deleted_at:r.deleted_at})
 const d=r.dependencies
 if(!localExact(d,['bootstrap_id','metadata_event_id','stage_event_ids'])||d.bootstrap_id!==r.bootstrap_id||!canonicalNoteUuid(d.metadata_event_id)||!Array.isArray(d.stage_event_ids)||d.stage_event_ids.length>64||d.stage_event_ids.some((id,i)=>!canonicalNoteUuid(id)||i>0&&id<=d.stage_event_ids[i-1]!))bad()
 if(r.seal_state==='pending'){if(r.seal_attempt_count!==0||r.last_error_code!==null)bad()}else if(!r.last_error_code||r.seal_attempt_count<1||sealFailureState(r.last_error_code)!==r.seal_state)bad()
 const snapshot=validateLocalNoteRecord(r.snapshot,s,r.project_id)
 if(snapshot.note_id!==r.note_id||snapshot.deleted!==(r.operation==='delete'))bad()
 validateLocalEnvelope(r.intent_envelope);return r
}
export function validateContentCandidate3(value:unknown,s:BrowserSyncScope):BrowserContentCandidate3{
 boundedContentRecord(value)
 if(!localExact(value,['record_version','record_kind','record_id','account_id','device_id','project_id','note_id','bootstrap_id','event_id','source_device_id','protocol_version','transport_kind','origin','codec_id','frame_version','codec_version','compression_id','header','intent','wire_item','wire_digest','raw_body_digest','logical_digest','authorship_envelope','record_digest']))bad()
 const r=value as unknown as BrowserContentCandidate3;identity(r,s)
 if(r.record_version!==3||r.record_kind!=='candidate'||r.record_id!==r.event_id||r.source_device_id!==s.deviceId||r.protocol_version!==3||r.transport_kind!=='content_note_v1'||r.origin!=='local_sealed'||r.codec_id!==8||r.frame_version!==1||r.codec_version!==1||![0,1].includes(r.compression_id)||![r.wire_digest,r.raw_body_digest,r.logical_digest,r.record_digest].every(noteHistoryHash))bad()
 const h=header(r.header),i=validateContentIntent2(r.intent,s)
 if(r.project_id!==i.project_id||r.note_id!==i.note_id||r.bootstrap_id!==i.bootstrap_id||r.event_id!==i.event_id||!same(h,{event_id:i.event_id,parent_event_id:i.parent_event_id,project_id:i.project_id,entity_id:i.note_id,entity_type:'note',operation:i.operation,revision:i.revision,updated_at:i.updated_at,deleted_at:i.deleted_at}))bad()
 let w:any;try{w=JSON.parse(r.wire_item)}catch{bad()}
 validateBrowserSealedBody(JSON.stringify({protocol_version:3,encrypted_sync_version:3,device_id:s.deviceId,items:[w]}),s)
 const e=w.event
 if(!localExact(w,['event','object'])||e.event_id!==r.event_id||e.project_id!==r.project_id||e.entity_id!==r.note_id||e.entity_type!=='note'||e.operation!=='event'||e.deleted_at!==null||e.revision!==h.revision||e.updated_at!==h.updated_at)bad()
 validateLocalEnvelope(r.authorship_envelope);return r
}
export function contentBaseReceipt(r:BrowserContentReceipt2):BrowserUploadReceipt{return{record_version:1,account_id:r.account_id,device_id:r.device_id,event_id:r.event_id,protocol_version:3,server_sequence:r.server_sequence,duplicate:r.duplicate}}
export function validateContentReceipt2(value:unknown,s:BrowserSyncScope):BrowserContentReceipt2{
 boundedContentRecord(value)
 if(!localExact(value,['record_version','owner_kind','account_id','device_id','event_id','protocol_version','server_sequence','duplicate','candidate_digest','wire_digest','acceptance_envelope','receipt_digest']))bad()
 const r=value as unknown as BrowserContentReceipt2;identity(r,s)
 if(r.record_version!==2||r.owner_kind!=='content_note_acceptance'||r.protocol_version!==3||!localSafe(r.server_sequence,1)||typeof r.duplicate!=='boolean'||![r.candidate_digest,r.wire_digest,r.receipt_digest].every(noteHistoryHash))bad()
 validateLocalEnvelope(r.acceptance_envelope);return r
}
/** Structural join only. Callers must separately authenticate C3 and R2 after unlock. */
export function joinContentReceipt2(s:BrowserSyncScope,value:unknown,candidate:unknown,out:BrowserOutboxRecord):BrowserContentReceipt2{
 const r=validateContentReceipt2(value,s),c=validateContentCandidate3(candidate,s)
 validateBrowserUploadPair(out,contentBaseReceipt(r),s)
 if(out.state!=='accepted'||out.account_id!==s.accountId||out.device_id!==s.deviceId||out.protocol_version!==3||out.event_id!==r.event_id||c.event_id!==r.event_id||c.record_digest!==r.candidate_digest||c.wire_digest!==r.wire_digest||!same(JSON.parse(out.raw_body).items[0],JSON.parse(c.wire_item)))bad()
 return r
}
export function validateContentSelfEchoProof2(value:unknown,s:BrowserSyncScope):BrowserContentSelfEchoProof2{
 boundedContentRecord(value)
 if(!localExact(value,['record_version','owner_kind','outcome','account_id','device_id','bootstrap_id','protocol_version','reference','server_sequence','codec_id','frame_version','codec_version','header','mutation','history_event_id','candidate_digest','wire_digest','receipt_digest','outcome_digest']))bad()
 const p=value as unknown as BrowserContentSelfEchoProof2,r=p.reference,h=header(p.header);identity({account_id:p.account_id,device_id:p.device_id,event_id:h.event_id},s)
 if(p.record_version!==2||p.owner_kind!=='content_note_self_echo'||p.outcome!=='acknowledged'||p.protocol_version!==3||p.codec_id!==8||p.frame_version!==1||p.codec_version!==1||!canonicalNoteUuid(p.bootstrap_id)||p.bootstrap_id[14]!=='4'||!localSafe(p.server_sequence,1)||p.history_event_id!==h.event_id||![p.candidate_digest,p.wire_digest,p.receipt_digest,p.outcome_digest].every(noteHistoryHash))bad()
 if(!localExact(r,['event_id','device_id','server_sequence','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||r.device_id!==s.deviceId||r.event_id!==h.event_id||r.server_sequence!==p.server_sequence||r.entity_type!=='note'||r.operation!=='event'||r.deleted_at!==null||r.project_id!==h.project_id||r.entity_id!==h.entity_id||r.revision!==h.revision||r.updated_at!==h.updated_at||p.mutation!==(h.operation==='delete'?'delete':h.revision===1?'create':'update'))bad()
 return p
}
