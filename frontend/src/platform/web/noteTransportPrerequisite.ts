import {requireContentStageDependency} from './contentStageDependency'
import type { BrowserPrefixInventory } from './provenPrefixRecords'
import type { AccountMasterKey } from '@/crypto'
import type { NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError } from './persistence'
import { openNoteTransport } from './noteTransport'
import { readStageInventory } from './stageApply'
import { prepareMetadataPrefix, verifiedMetadataSequences } from './metadataPrefixProof'
import { validateBrowserMetadataHead } from './metadataApplyRecords'
import { immutableWireIdentity, snapshotBrowserSyncScope, validateBrowserInboxRecord, type BrowserInboxRecord, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { NOTE_HISTORY_STORE, validateNoteHistoryRecord, type BrowserNoteCandidate, type BrowserNoteHistoryRecord } from './noteHistoryRecords'
import type { LocalNoteRecord } from './localAuthorityRecords'
import { candidateDigest } from './noteHistory'
import { noteProofDigest } from './legacyNoteApply'
export interface VerifiedNotePrerequisite { readonly verifiedNotePrerequisite: unique symbol }
export interface VerifiedNoteTransportCommit { readonly verifiedNoteTransportCommit: unique symbol }
interface Certificate {scope:BrowserSyncScope;row:BrowserInboxRecord;binding:BrowserProjectBinding;owners:unknown[];bindings:unknown[];dependency_digest:string;logical_material_digest:string;current:()=>boolean}
const certificates=new WeakMap<object,Certificate>()
const commits=new WeakMap<object,{certificate:Certificate;candidate:BrowserNoteCandidate}>()
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
function fail():never{throw new BrowserPersistenceError('stale_authority')}
/** Content-only prerequisite. Minted from original AEAD + authenticated Metadata/Stage, never a caller DTO. */
export async function prepareNotePrerequisite(scope:BrowserSyncScope,row:BrowserInboxRecord,binding:BrowserProjectBinding,amk:AccountMasterKey,current:()=>boolean,transaction:BrowserSyncTransaction|undefined,inventory?:BrowserPrefixInventory):Promise<{certificate:VerifiedNotePrerequisite;plaintext:NoteSyncPlaintext}>{
 scope=snapshotBrowserSyncScope(scope);row=validateBrowserInboxRecord(structuredClone(row),scope);binding=validateBrowserProjectBinding(structuredClone(binding),scope)
 const {plaintext,content}=await openNoteTransport(scope,amk,row.protocol_version,row.wire_item,'content_note_v1')
 if(!content||content.dependencies.bootstrap_id!==binding.bootstrap_id||content.event.version!==1||content.device_id===scope.deviceId)throw new BrowserPersistenceError('unsupported_local_source')
 const v=inventory??await transaction!<BrowserPrefixInventory>(scope,['inbox','outbox','receipts','projectBindings','ownerHeads','legacyNoteHistory','cursors'],'readonly',(tx,result,abort)=>readStageInventory(tx,scope,result,abort))
 if(!same(v.rows.find(r=>(r as BrowserInboxRecord).server_sequence===row.server_sequence),row)||!v.bindings.some(b=>same(b,binding)))fail()
 const cert=await prepareMetadataPrefix(scope,v,amk,current,true),sequences=verifiedMetadataSequences(cert,scope,v)
 const raw=v.owners.find(r=>(r as {owner_kind:string;owner_id:string}).owner_kind==='project_metadata'&&(r as {owner_id:string}).owner_id===binding.project_id)
 if(!raw)fail()
 const head=validateBrowserMetadataHead(raw,scope),dependency=head.history.find(p=>p.event_id===content.dependencies.metadata_event_id),tip=head.history.find(p=>p.event_id===head.tip_event_ids[0])
 if(head.bootstrap_id!==binding.bootstrap_id||!dependency||dependency.operation==='delete'||!sequences.has(dependency.server_sequence)||head.tip_event_ids.length!==1||!tip||tip.operation==='delete'||!sequences.has(tip.server_sequence))fail()
 await requireContentStageDependency(scope,row,content,v,amk,current,cert)
 if(!current())throw new BrowserPersistenceError('closed')
 const dependency_digest=await noteProofDigest({scope,bootstrap_id:binding.bootstrap_id,project_id:binding.project_id,note_id:plaintext.header.entity_id,event_id:plaintext.header.event_id,transport:row,dependencies:content.dependencies,owners:v.owners,bindings:v.bindings})
 const logical_material_digest=await noteProofDigest(plaintext);if(!current())throw new BrowserPersistenceError('closed')
 const certificate=Object.freeze({}) as VerifiedNotePrerequisite
 certificates.set(certificate,{scope:structuredClone(scope),row:structuredClone(row),binding:structuredClone(binding),owners:structuredClone(v.owners),bindings:structuredClone(v.bindings),dependency_digest,logical_material_digest,current})
 return {certificate,plaintext}
}
/** Bind the actual encrypted source result to its original transport before scheduling. */
export async function prepareNoteTransportCommit(token:VerifiedNotePrerequisite,plaintext:NoteSyncPlaintext,projection:LocalNoteRecord):Promise<{candidate:BrowserNoteCandidate;hook:VerifiedNoteTransportCommit}>{
 plaintext=structuredClone(plaintext);projection=structuredClone(projection)
 const p=certificates.get(token);if(!p||!p.current())fail()
 if(await noteProofDigest(plaintext)!==p.logical_material_digest)fail()
 const opened=JSON.parse(p.row.wire_item),h=plaintext.header
 if(h.event_id!==p.row.event_id||h.project_id!==p.binding.project_id||h.entity_id!==opened.event.entity_id)fail()
 const wire_digest=await noteProofDigest({protocol_version:p.row.protocol_version,item:opened}),local_note_digest=await noteProofDigest(projection)
 const proof={proof_kind:'content_note_v1_prerequisite' as const,logical_digest:await noteProofDigest(plaintext),wire_digest,dependency_digest:p.dependency_digest,outcome:'applied' as const,source_revision:projection.source_revision,local_note_digest,proof_digest:''}
 const {proof_digest:_digest,...body}=proof;proof.proof_digest=await noteProofDigest(body)
 const candidate:BrowserNoteCandidate={record_version:2,transport_kind:'content_note_v1',server_sequence:p.row.server_sequence,transport_proof:proof,account_id:p.scope.accountId,device_id:p.scope.deviceId,project_id:h.project_id,note_id:h.entity_id,bootstrap_id:p.binding.bootstrap_id,record_kind:'candidate',record_id:h.event_id,event_id:h.event_id,source_device_id:opened.event.device_id,protocol_version:3,origin:'peer',mutation_generation:null,header:structuredClone(h),wire_item:p.row.wire_item,wire_digest,record_digest:'',projection:structuredClone(projection),projection_digest:local_note_digest}
 candidate.record_digest=await candidateDigest(candidate);validateNoteHistoryRecord(candidate,p.scope)
 if(!p.current())fail();const hook=Object.freeze({}) as VerifiedNoteTransportCommit
 commits.set(hook,{certificate:p,candidate:structuredClone(candidate)});return{candidate,hook}
}
export function isDeferredNoteTransportCandidate(token:VerifiedNoteTransportCommit|undefined,r:BrowserNoteHistoryRecord):boolean{
 if(!token)return false;const p=commits.get(token);if(!p||!p.certificate.current())fail()
 if(r.record_kind!=='candidate'||r.event_id!==p.candidate.event_id)return false
 if(!same(r,p.candidate))fail();return true
}
/** Actual IDB lifecycle: dependency CAS and immutable wrapper write share Note/source/head transaction. */
export function scheduleNoteTransportCommit(tx:IDBTransaction,token:VerifiedNoteTransportCommit,done:()=>void,abort:(e:unknown)=>void):void{
 try{
  const p=commits.get(token);if(!p||!p.certificate.current())fail();const c=p.certificate,range=IDBKeyRange.bound([c.scope.accountId],[c.scope.accountId,[]])
  const owners=tx.objectStore('ownerHeads').getAll(range),bindings=tx.objectStore('projectBindings').getAll(range),store=tx.objectStore(NOTE_HISTORY_STORE),candidate=store.get([c.scope.accountId,p.candidate.project_id,p.candidate.note_id,'candidate',p.candidate.event_id]);let count=0
  const finish=()=>{if(++count!==3)return;try{if(!c.current()||!same(owners.result,c.owners)||!same(bindings.result,c.bindings))fail();if(candidate.result){if(!same(candidate.result,p.candidate))fail();done();return}
   const write=store.add(p.candidate);write.onsuccess=()=>{try{if(!c.current())fail();done()}catch(e){abort(e)}}
  }catch(e){abort(e)}};[owners,bindings,candidate].forEach(r=>r.onsuccess=finish)
 }catch(e){abort(e)}
}

/** Exact replay retains original candidate/proof while a fresh certificate rechecks current dependencies in the final transaction. */
export function prepareNoteTransportReplay(token:VerifiedNotePrerequisite,candidate:BrowserNoteCandidate):VerifiedNoteTransportCommit{
 const p=certificates.get(token);if(!p||!p.current()||candidate.record_version!==2||candidate.wire_item!==p.row.wire_item||candidate.event_id!==p.row.event_id||candidate.bootstrap_id!==p.binding.bootstrap_id)fail()
 validateNoteHistoryRecord(candidate,p.scope);const hook=Object.freeze({}) as VerifiedNoteTransportCommit
 commits.set(hook,{certificate:p,candidate:structuredClone(candidate)});return hook
}
