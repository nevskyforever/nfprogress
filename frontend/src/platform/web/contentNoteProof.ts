import type { AccountMasterKey } from '@/crypto'
import { BrowserPersistenceError } from './persistence'
import { noteProofDigest } from './legacyNoteApply'
import { openHistoryCandidate } from './noteHistory'
import { validateNoteHistorySet,type BrowserNoteCandidate,type BrowserNoteHistoryRecord } from './noteHistoryRecords'
import { validateContentNoteProof,type BrowserContentNoteProof } from './contentNoteRecords'
import { immutableWireIdentity,validateBrowserInboxRecord,type BrowserSyncScope,type BrowserInboxRecord } from './syncDurability'
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
function bad():never{throw new BrowserPersistenceError('corrupt_record')}
export async function contentNoteOutcomeDigest(p:BrowserContentNoteProof){const {outcome_digest:_digest,...body}=p;return noteProofDigest(body)}
export async function contentProofFor(scope:BrowserSyncScope,row:BrowserInboxRecord,c:BrowserNoteCandidate,mutation:BrowserContentNoteProof['mutation']):Promise<BrowserContentNoteProof>{
 if(c.record_version!==2||c.transport_proof.outcome!=='applied')bad();const t=c.transport_proof
 const p:BrowserContentNoteProof={record_version:1,owner_kind:'content_note',outcome:'applied',account_id:scope.accountId,bootstrap_id:c.bootstrap_id,protocol_version:3,reference:JSON.parse(row.wire_item).event,server_sequence:row.server_sequence,codec_id:8,frame_version:1,codec_version:1,header:structuredClone(c.header),mutation,history_event_id:c.event_id,wire_digest:c.wire_digest,logical_digest:t.logical_digest,dependency_digest:t.dependency_digest,candidate_digest:c.record_digest,transport_proof_digest:t.proof_digest,source_revision:t.source_revision,local_note_digest:t.local_note_digest,outcome_digest:''}
 p.outcome_digest=await contentNoteOutcomeDigest(p);return validateContentNoteProof(p,scope)
}
/** Pure exact immutable join; crypto and current Metadata certificate are additionally mandatory for prefix qualification. */
export function contentHistoryJoin(scope:BrowserSyncScope,raw:BrowserInboxRecord,history:BrowserNoteHistoryRecord[]):BrowserNoteCandidate & {record_version:2}{
 const row=validateBrowserInboxRecord(raw,scope);if(row.state!=='content_note_proven')bad();const p=row.content_note_proof,rows=validateNoteHistorySet(scope,history),c=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===row.event_id)
 if(!c||c.record_version!==2||c.transport_proof.outcome!=='applied'||c.transport_kind!=='content_note_v1'||c.origin!=='peer'||c.protocol_version!==3||c.server_sequence!==row.server_sequence||c.source_device_id!==p.reference.device_id||c.bootstrap_id!==p.bootstrap_id||c.project_id!==p.header.project_id||c.note_id!==p.header.entity_id||c.wire_item!==row.wire_item||!same(c.header,p.header)||c.record_digest!==p.candidate_digest||c.wire_digest!==p.wire_digest||c.projection_digest!==p.local_note_digest||!c.projection||c.projection.source_revision!==p.source_revision||c.transport_proof.logical_digest!==p.logical_digest||c.transport_proof.dependency_digest!==p.dependency_digest||c.transport_proof.proof_digest!==p.transport_proof_digest||c.transport_proof.local_note_digest!==p.local_note_digest)bad()
 const head=rows.find(r=>r.record_kind==='head'&&r.project_id===c.project_id&&r.note_id===c.note_id&&r.bootstrap_id===c.bootstrap_id);if(!head||head.record_kind!=='head')bad()
 let event:string|null=head.linear_head_event_id,found=false
 for(let n=0;event!==null&&n<=rows.length;n++){if(event===c.event_id){found=true;break}const parent=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.project_id===c.project_id&&r.note_id===c.note_id&&r.bootstrap_id===c.bootstrap_id&&r.event_id===event);if(!parent)bad();event=parent.header.parent_event_id}
 if(!found)bad();return c
}
export async function verifyStoredContentNoteProof(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord,history:BrowserNoteHistoryRecord[]):Promise<void>{
 const c=contentHistoryJoin(scope,row,history);if(row.state!=='content_note_proven')bad()
 const value=await openHistoryCandidate(scope,c,amk),p=row.content_note_proof
 if(!same(value.header,p.header)||value.mutation!==p.mutation||await noteProofDigest(value)!==p.logical_digest||await contentNoteOutcomeDigest(p)!==p.outcome_digest)bad()
}
