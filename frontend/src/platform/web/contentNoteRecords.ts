import type { V3Descriptor } from '@/api/encryptedSyncV3'
import type { NoteSyncHeader } from '@/cloud/noteSyncCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { BrowserPersistenceError } from './persistence'
import { localExact,localId,localSafe } from './localAuthorityRecords'
import { canonicalNoteUuid,noteHistoryHash } from './noteHistoryRecords'
import type { BrowserSyncScope } from './syncDurability'
/** Dedicated final wrapper + shared ordinary Note outcome. No plaintext payload. */
export interface BrowserContentNoteProof {
 record_version:1;owner_kind:'content_note';outcome:'applied';account_id:string;bootstrap_id:string;protocol_version:3
 reference:V3Descriptor;server_sequence:number;codec_id:8;frame_version:1;codec_version:1
 header:NoteSyncHeader;mutation:'create'|'update'|'delete';history_event_id:string
 wire_digest:string;logical_digest:string;dependency_digest:string;candidate_digest:string;transport_proof_digest:string
 source_revision:number;local_note_digest:string;outcome_digest:string
}
function bad():never{throw new BrowserPersistenceError('corrupt_record')}
export function validateContentNoteProof(value:unknown,scope:BrowserSyncScope):BrowserContentNoteProof{
 if(!localExact(value,['record_version','owner_kind','outcome','account_id','bootstrap_id','protocol_version','reference','server_sequence','codec_id','frame_version','codec_version','header','mutation','history_event_id','wire_digest','logical_digest','dependency_digest','candidate_digest','transport_proof_digest','source_revision','local_note_digest','outcome_digest']))bad()
 const p=value as unknown as BrowserContentNoteProof,h=p.header,r=p.reference
 if(p.record_version!==1||p.owner_kind!=='content_note'||p.outcome!=='applied'||p.account_id!==scope.accountId||!canonicalNoteUuid(p.bootstrap_id)||p.protocol_version!==3||p.codec_id!==8||p.frame_version!==1||p.codec_version!==1||!localSafe(p.server_sequence,1)||!localSafe(p.source_revision,1)||![p.wire_digest,p.logical_digest,p.dependency_digest,p.candidate_digest,p.transport_proof_digest,p.local_note_digest,p.outcome_digest].every(noteHistoryHash))bad()
 if(!localExact(h,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||!localExact(r,['event_id','device_id','server_sequence','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at']))bad()
 localId(h.project_id);localId(h.entity_id)
 if(h.entity_type!=='note'||r.entity_type!=='note'||r.operation!=='event'||r.deleted_at!==null||!canonicalNoteUuid(r.device_id)||r.device_id===scope.deviceId||!canonicalNoteUuid(h.event_id)||h.parent_event_id!==null&&!canonicalNoteUuid(h.parent_event_id)||h.parent_event_id===h.event_id||!localSafe(h.revision,1)||(h.revision===1)!==(h.parent_event_id===null)||!['upsert','delete'].includes(h.operation)||!['create','update','delete'].includes(p.mutation)||(p.mutation==='create')!==(h.revision===1&&h.operation==='upsert')||(p.mutation==='delete')!==(h.operation==='delete')||(h.operation==='delete')!==(h.deleted_at!==null)||p.history_event_id!==h.event_id||h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.entity_id||h.revision!==r.revision||p.server_sequence!==r.server_sequence)bad()
 try{if(canonicalizeSyncTimestamp(h.updated_at)!==canonicalizeSyncTimestamp(r.updated_at))bad();if(h.deleted_at!==null)canonicalizeSyncTimestamp(h.deleted_at)}catch{bad()}
 return p
}

interface ContentConflictProofFields extends Omit<BrowserContentNoteProof,'record_version'|'outcome'|'mutation'|'source_revision'|'local_note_digest'> {
 outcome:'conflict_preserved';mutation:'update'|'delete';group_id:string;conflict_generation:number;common_parent_event_id:string
}
export type BrowserContentNoteConflictProof=ContentConflictProofFields & ({record_version:1}|{record_version:2;local_version_id:string;local_mutation_generation:number;local_version_digest:string})
export function validateContentNoteConflictProof(value:unknown,scope:BrowserSyncScope):BrowserContentNoteConflictProof{
 if(!localExact(value,['record_version','owner_kind','outcome','account_id','bootstrap_id','protocol_version','reference','server_sequence','codec_id','frame_version','codec_version','header','mutation','history_event_id','wire_digest','logical_digest','dependency_digest','candidate_digest','transport_proof_digest','outcome_digest','group_id','conflict_generation','common_parent_event_id',...((value as BrowserContentNoteConflictProof)?.record_version===2?['local_version_id','local_mutation_generation','local_version_digest']:[])]))bad()
 const p=value as unknown as BrowserContentNoteConflictProof
 if(![1,2].includes(p.record_version))bad()
 if(p.record_version===2&&(!localSafe(p.local_mutation_generation,1)||!noteHistoryHash(p.local_version_digest)||typeof p.local_version_id!=='string'||p.local_version_id.split(':').length!==4||!p.local_version_id.startsWith(`local:${scope.accountId}:`)||!canonicalNoteUuid(p.local_version_id.split(':')[2])||p.local_version_id.split(':')[2]![14]!=='4'||!p.local_version_id.endsWith(`:${p.local_mutation_generation}`)))bad()
 if(p.outcome!=='conflict_preserved'||!['update','delete'].includes(p.mutation)||!canonicalNoteUuid(p.group_id)||p.group_id[14]!=='4'||!localSafe(p.conflict_generation,1)||!canonicalNoteUuid(p.common_parent_event_id)||p.header?.parent_event_id!==p.common_parent_event_id)bad()
 // Structural view only. Never store or use as an applied local projection.
 const {group_id:_g,conflict_generation:_n,common_parent_event_id:_parent,...body}=p
 const view={...body} as Record<string,unknown>;delete view.local_version_id;delete view.local_mutation_generation;delete view.local_version_digest
 validateContentNoteProof({...view,record_version:1,outcome:'applied',source_revision:1,local_note_digest:'0'.repeat(64)},scope)
 return p
}
