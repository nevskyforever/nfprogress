import {openFrozenLocalVersion} from './noteUnsealedVersion'
import {validateNoteIntent} from './noteIntentRecords'
import type {AccountMasterKey} from '@/crypto'
import {BrowserPersistenceError} from './persistence'
import {immutableWireIdentity,validateBrowserInboxRecord,type BrowserInboxRecord,type BrowserSyncScope} from './syncDurability'
import {validateNoteHistorySet,type BrowserNoteCandidate,type BrowserNoteConflictGroup,type BrowserNoteHistoryRecord,type BrowserNoteLocalVersion} from './noteHistoryRecords'
import {openHistoryCandidate} from './noteHistory'
import {noteProofDigest,noteOutcomeDigest,verifyStoredNoteProof,openRetainedNote} from './legacyNoteApply'
import {verifyStoredContentNoteProof} from './contentNoteProof'
import {validateContentNoteConflictProof,type BrowserContentNoteConflictProof} from './contentNoteRecords'
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const route=['id','project_id','stage_id','source_type','source_map_id','source_node_id','content_format'] as const
function bad():never{throw new BrowserPersistenceError('corrupt_record')}
export async function contentConflictProofFor(scope:BrowserSyncScope,row:BrowserInboxRecord,c:BrowserNoteCandidate,g:BrowserNoteConflictGroup,mutation:'update'|'delete',versions:BrowserNoteLocalVersion[]=[]):Promise<BrowserContentNoteConflictProof>{
 if(c.record_version!==2||c.transport_proof.outcome!=='conflict_preserved')bad();const t=c.transport_proof
 let p:BrowserContentNoteConflictProof={record_version:1,owner_kind:'content_note',outcome:'conflict_preserved',account_id:scope.accountId,bootstrap_id:c.bootstrap_id,protocol_version:3,reference:JSON.parse(row.wire_item).event,server_sequence:row.server_sequence,codec_id:8,frame_version:1,codec_version:1,header:structuredClone(c.header),mutation,history_event_id:c.event_id,wire_digest:c.wire_digest,logical_digest:t.logical_digest,dependency_digest:t.dependency_digest,candidate_digest:c.record_digest,transport_proof_digest:t.proof_digest,group_id:g.group_id,conflict_generation:g.conflict_generation,common_parent_event_id:g.common_parent_event_id,outcome_digest:''}
 const local=g.members.find(m=>m.source==='local_unsealed');if(local){const v=versions.find(v=>v.version_id===local.version_id);if(!v)bad();p={...p,record_version:2,local_version_id:v.version_id,local_mutation_generation:v.intent.mutation_generation,local_version_digest:v.record_digest}}
 p.outcome_digest=await noteOutcomeDigest(p);return validateContentNoteConflictProof(p,scope)
}
/** Structural exact join; only authenticated group verification may qualify prefix. */
export function contentConflictHistoryJoin(scope:BrowserSyncScope,raw:BrowserInboxRecord,history:BrowserNoteHistoryRecord[]){
 const row=validateBrowserInboxRecord(raw,scope);if(row.state!=='content_note_conflict_preserved')bad();const p=row.content_note_conflict_proof,rows=validateNoteHistorySet(scope,history),c=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===row.event_id),g=rows.find((r):r is BrowserNoteConflictGroup=>r.record_kind==='group'&&r.group_id===p.group_id),m=g?.members.find(m=>m.event_id===row.event_id)
 if(!c||c.record_version!==2||c.transport_proof.outcome!=='conflict_preserved'||c.projection!==null||c.projection_digest!==null||c.origin!=='peer'||c.bootstrap_id!==p.bootstrap_id||c.project_id!==p.header.project_id||c.note_id!==p.header.entity_id||c.server_sequence!==row.server_sequence||c.source_device_id!==p.reference.device_id||c.wire_item!==row.wire_item||!same(c.header,p.header)||c.record_digest!==p.candidate_digest||c.wire_digest!==p.wire_digest||c.transport_proof.logical_digest!==p.logical_digest||c.transport_proof.dependency_digest!==p.dependency_digest||c.transport_proof.proof_digest!==p.transport_proof_digest||!g||g.bootstrap_id!==c.bootstrap_id||g.project_id!==c.project_id||g.note_id!==c.note_id||g.common_parent_event_id!==p.common_parent_event_id||g.tip_revision!==p.header.revision||!m||m.source!=='remote'||m.server_sequence!==row.server_sequence||m.conflict_generation!==p.conflict_generation)bad()
 const local=g.members.find(m=>m.source==='local_unsealed'),v=local&&rows.find((r):r is BrowserNoteLocalVersion=>r.record_kind==='local_version'&&r.version_id===local.version_id)
 if(local){if(p.record_version!==2||!v||p.local_version_id!==v.version_id||p.local_version_digest!==v.record_digest||p.local_mutation_generation!==v.intent.mutation_generation||local.local_mutation_generation!==p.local_mutation_generation)bad()}else if(p.record_version!==1)bad()
 return {candidate:c,group:g}
}
/** One shared peer group. Validate actual retained transport, not event-ID guesses. No dependency/HTTP side effects. */
export async function verifyPeerNoteGroup(scope:BrowserSyncScope,g:BrowserNoteConflictGroup,history:BrowserNoteHistoryRecord[],inbox:BrowserInboxRecord[],amk:AccountMasterKey):Promise<void>{
 const rows=validateNoteHistorySet(scope,history),parent=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===g.common_parent_event_id&&r.project_id===g.project_id&&r.note_id===g.note_id),head=rows.find(r=>r.record_kind==='head'&&r.project_id===g.project_id&&r.note_id===g.note_id),winner=g.members.find(m=>m.source==='remote_applied')
 if(!parent||!head||head.record_kind!=='head'||!winner||head.linear_head_event_id!==winner.event_id||g.members.some(m=>m.source==='local_unsealed'))bad()
 const base=await openHistoryCandidate(scope,parent,amk)
 for(const m of g.members){const c=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===m.event_id),r=inbox.find(r=>r.event_id===m.event_id)
  if(!c||c.origin!=='peer'||c.source_device_id===scope.deviceId||!r||r.server_sequence!==m.server_sequence||c.header.parent_event_id!==g.common_parent_event_id||c.header.revision!==g.tip_revision||g.bootstrap_id!==c.bootstrap_id)bad()
  const value=await openHistoryCandidate(scope,c,amk),wire=JSON.parse(r.wire_item),{device_id:_device,server_sequence:_seq,...descriptor}=wire.event
  if(c.source_device_id!==wire.event.device_id||c.protocol_version!==r.protocol_version||!same(JSON.parse(c.wire_item),c.record_version===2?wire:{event:descriptor,object:wire.object}))bad()
  if(route.some(k=>!same(base.note[k],value.note[k])))bad()
  if(m.source==='remote_applied'){
   if(r.state==='content_note_proven'){if(c.record_version!==2||c.transport_proof.outcome!=='applied')bad();await verifyStoredContentNoteProof(scope,amk,r,rows)}
   else if(r.state==='note_proven'){if(c.record_version!==1||r.note_proof.outcome!=='applied'||r.note_proof.bootstrap_id!==g.bootstrap_id||!same(c.header,r.note_proof.header)||c.projection_digest!==r.note_proof.local_note_digest)bad();await verifyStoredNoteProof(scope,amk,r)}else bad()
  }else if(r.state==='content_note_conflict_preserved'){
   const p=r.content_note_conflict_proof;contentConflictHistoryJoin(scope,r,rows)
   if(p.group_id!==g.group_id||p.conflict_generation!==m.conflict_generation||await noteOutcomeDigest(p)!==p.outcome_digest||await noteProofDigest(value)!==p.logical_digest||value.mutation!==p.mutation)bad()
  }else if(r.state==='note_conflict_preserved'){
   const p=r.note_conflict_proof,w=JSON.parse(r.wire_item),opened=await openRetainedNote(scope,amk,r),{device_id:_d,server_sequence:_s,...event}=w.event
   if(c.record_version!==1||p.record_version!==1||p.group_id!==g.group_id||p.bootstrap_id!==g.bootstrap_id||p.conflict_generation!==m.conflict_generation||!same(p.header,c.header)||!same(opened,value)||!same(JSON.parse(c.wire_item),{event,object:w.object})||await noteProofDigest({protocol_version:r.protocol_version,event:w.event,object:w.object})!==p.wire_digest||await noteOutcomeDigest(p)!==p.outcome_digest)bad()
  }else bad()
 }
}
/** Narrow project-HTML local-unsealed mode; accepted peer verifier remains unchanged. */
export async function verifyLocalContentGroup(scope:BrowserSyncScope,g:BrowserNoteConflictGroup,history:BrowserNoteHistoryRecord[],inbox:BrowserInboxRecord[],amk:AccountMasterKey,intents:readonly unknown[],localNotes:readonly unknown[]):Promise<void>{
 const rows=validateNoteHistorySet(scope,history),member=g.members.find(m=>m.source==='local_unsealed'),v=member&&rows.find((r):r is BrowserNoteLocalVersion=>r.record_kind==='local_version'&&r.version_id===member.version_id),parent=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===g.common_parent_event_id&&r.project_id===g.project_id&&r.note_id===g.note_id),head=rows.find(r=>r.record_kind==='head'&&r.project_id===g.project_id&&r.note_id===g.note_id)
 if(!v||!member||!parent||!head||head.record_kind!=='head'||head.linear_head_event_id!==g.common_parent_event_id||g.members.some(m=>m.source==='remote_applied')||v.intent.bootstrap_id!==g.bootstrap_id||v.header.parent_event_id!==g.common_parent_event_id||v.header.revision!==g.tip_revision||member.local_mutation_generation!==v.intent.mutation_generation)bad()
 const current=intents.map(i=>validateNoteIntent(i,scope)).filter(i=>i.project_id===g.project_id&&i.note_id===g.note_id)
 const currentNotes=localNotes.filter(n=>(n as {account_id:string;project_id:string;note_id:string}).account_id===scope.accountId&&(n as {project_id:string}).project_id===g.project_id&&(n as {note_id:string}).note_id===g.note_id)
 if(current.length!==1||!same(current[0],v.intent)||currentNotes.length!==1||!same(currentNotes[0],v.intent.snapshot))bad()
 const local=await openFrozenLocalVersion(scope,v,amk),base=await openHistoryCandidate(scope,parent,amk)
 if(local.note.stage_id!==null||local.note.source_type!=='project'||local.note.source_map_id!==null||local.note.source_node_id!==null||local.note.content_format!=='html'||route.some(k=>!same(base.note[k],local.note[k])))bad()
 for(const m of g.members){if(m.source==='local_unsealed')continue
  const c=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===m.event_id),r=inbox.find(r=>r.event_id===m.event_id)
  if(!c||c.origin!=='peer'||c.source_device_id===scope.deviceId||!r||r.server_sequence!==m.server_sequence||c.header.parent_event_id!==g.common_parent_event_id||c.header.revision!==g.tip_revision||c.bootstrap_id!==g.bootstrap_id)bad()
  const value=await openHistoryCandidate(scope,c,amk),wire=JSON.parse(r.wire_item),{device_id:_d,server_sequence:_s,...event}=wire.event
  if(route.some(k=>!same(local.note[k],value.note[k]))||c.source_device_id!==wire.event.device_id||c.protocol_version!==r.protocol_version||!same(JSON.parse(c.wire_item),c.record_version===2?wire:{event,object:wire.object}))bad()
  if(r.state==='content_note_conflict_preserved'){const p=r.content_note_conflict_proof;contentConflictHistoryJoin(scope,r,rows);if(p.record_version!==2||p.group_id!==g.group_id||p.conflict_generation!==m.conflict_generation||await noteOutcomeDigest(p)!==p.outcome_digest||await noteProofDigest(value)!==p.logical_digest||value.mutation!==p.mutation)bad()}
  else if(r.state==='note_conflict_preserved'){const p=r.note_conflict_proof;if(c.record_version!==1||p.record_version!==2||p.local_version_id!==v.version_id||p.local_version_digest!==v.record_digest||p.local_mutation_generation!==v.intent.mutation_generation||p.group_id!==g.group_id||p.bootstrap_id!==g.bootstrap_id||p.conflict_generation!==m.conflict_generation||!same(p.header,c.header)||await noteProofDigest({protocol_version:r.protocol_version,event:wire.event,object:wire.object})!==p.wire_digest||await noteOutcomeDigest(p)!==p.outcome_digest)bad()}else bad()
 }
}
export async function verifyContentGroup(scope:BrowserSyncScope,g:BrowserNoteConflictGroup,history:BrowserNoteHistoryRecord[],inbox:BrowserInboxRecord[],amk:AccountMasterKey,intents:readonly unknown[]=[],localNotes:readonly unknown[]=[]){
 if(g.members.some(m=>m.source==='local_unsealed'))await verifyLocalContentGroup(scope,g,history,inbox,amk,intents,localNotes);else await verifyPeerNoteGroup(scope,g,history,inbox,amk)
}
export async function verifyStoredContentConflictProof(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord,history:BrowserNoteHistoryRecord[],inbox:BrowserInboxRecord[],intents:readonly unknown[]=[],localNotes:readonly unknown[]=[]){
 const {group}=contentConflictHistoryJoin(scope,row,history);await verifyContentGroup(scope,group,history,inbox,amk,intents,localNotes)
}
