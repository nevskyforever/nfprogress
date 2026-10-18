import {decryptObjectBytes,type AccountMasterKey} from '@/crypto'
import {decodeBase64Url} from '@/api/base64url'
import {canonical} from '@/cloud/projectMetadataCodec'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {unframeContentNote,validateContentNote,type ContentNoteEvent} from '@/cloud/contentNoteCodec'
import {BrowserPersistenceError} from './persistence'
import {validateContentLocalNote,localExact,type LocalEnvelope} from './localAuthorityRecords'
import {noteProofDigest} from './legacyNoteApply'
import {immutableWireIdentity,validateBrowserUploadPair,type BrowserSyncScope,type BrowserOutboxRecord,type BrowserInboxRecord} from './syncDurability'
import {validateContentIntent2,validateContentCandidate3,validateContentSelfEchoProof2,contentIntentIdentity,contentBaseReceipt,joinContentReceipt2,contentAuthorityCorrupt as bad,type BrowserContentCandidate3,type BrowserContentReceipt2} from './contentAuthorityRecords'
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const check=(current:()=>boolean)=>{if(!current())throw new BrowserPersistenceError('closed')}
async function open(s:BrowserSyncScope,project:string,note:string,e:LocalEnvelope,amk:AccountMasterKey,current:()=>boolean){
 check(current);let bytes:Uint8Array|undefined;const nonce=decodeBase64Url(e.nonce),ciphertext=decodeBase64Url(e.ciphertext)
 try{bytes=await decryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:note,entityType:'note'},{...e,nonce,ciphertext});check(current);return bytes.slice()}finally{bytes?.fill(0);nonce.fill(0);ciphertext.fill(0)}
}
async function json(s:BrowserSyncScope,project:string,note:string,e:LocalEnvelope,amk:AccountMasterKey,current:()=>boolean){const bytes=await open(s,project,note,e,amk,current);try{const raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes),value=JSON.parse(raw);if(canonical(value)!==raw)bad();return value}finally{bytes.fill(0)}}
/** Read-only authentication. Never creates an intent, candidate, receipt, proof or authority token. */
export async function authenticateContentIntent2(s:BrowserSyncScope,value:unknown,amk:AccountMasterKey,current:()=>boolean):Promise<ContentNoteEvent>{
 check(current);const r=validateContentIntent2(value,s)
 if(!same(await json(s,r.project_id,r.note_id,r.intent_envelope,amk,current),{intent_format:2,identity:contentIntentIdentity(r)})||await noteProofDigest(r.snapshot)!==r.snapshot_digest)bad()
 const p=await json(s,r.project_id,r.note_id,r.snapshot.envelope,amk,current)
 if(!localExact(p,['local_format','kind','account_id','device_id','project_id','note_id','source_revision','source'])||p.local_format!==1||p.kind!=='note'||p.account_id!==s.accountId||p.device_id!==s.deviceId||p.project_id!==r.project_id||p.note_id!==r.note_id||p.source_revision!==r.snapshot.source_revision)bad()
 const source=validateContentLocalNote(p.source,r.project_id)
 if(source.note.id!==r.note_id||(source.state==='tombstone')!==r.snapshot.deleted||(source.state==='live'?source.note.revision:source.revision)!==r.snapshot.note_revision||(source.note.stage_id===null)!==(r.dependencies.stage_event_ids.length===0))bad()
 const note={...source.note} as any;delete note.revision
 const {plaintext}=createNoteSyncPlaintext({event_id:r.event_id,project_id:r.project_id,entity_id:r.note_id,entity_type:'note',operation:r.operation,revision:r.revision,updated_at:r.updated_at,deleted_at:r.deleted_at},r.parent_event_id,note)
 const event:ContentNoteEvent={version:1,account_id:s.canonicalUserId,device_id:s.deviceId,dependencies:structuredClone(r.dependencies),event:plaintext};validateContentNote(event);check(current);return event
}
export async function authenticateContentCandidate3(s:BrowserSyncScope,value:unknown,amk:AccountMasterKey,current:()=>boolean){
 check(current);const c=validateContentCandidate3(value,s),{authorship_envelope:_envelope,record_digest:_digest,...body}=c
 if(!same(await json(s,c.project_id,c.note_id,c.authorship_envelope,amk,current),{content_outbound_format:1,kind:'sealed_authorship',candidate_body_digest:await noteProofDigest(body)}))bad()
 const {record_digest:_record,...record}=c;if(await noteProofDigest(record)!==c.record_digest)bad()
 const expected=await authenticateContentIntent2(s,c.intent,amk,current),item=JSON.parse(c.wire_item)
 if(await noteProofDigest({protocol_version:3,item})!==c.wire_digest)bad()
 const bytes=await open(s,c.project_id,c.note_id,item.object,amk,current)
 try{const event=unframeContentNote(bytes);if(event.event.version!==1)bad();if(bytes[8]!==1||bytes[9]!==8||bytes[10]!==1||bytes[11]!==c.compression_id||!same(event,expected)||!same(event.event.header,c.header)||await noteProofDigest(event)!==c.logical_digest)bad();check(current);return event.event}finally{bytes.fill(0)}
}
export async function authenticateContentReceipt2(s:BrowserSyncScope,value:unknown,candidate:unknown,out:BrowserOutboxRecord,amk:AccountMasterKey,current:()=>boolean){
 check(current);const r=joinContentReceipt2(s,value,candidate,out),c=validateContentCandidate3(candidate,s)
 await authenticateContentCandidate3(s,c,amk,current)
 validateBrowserUploadPair(out,contentBaseReceipt(r),s)
 if(out.local_ordinal!==c.intent.local_ordinal||await noteProofDigest(out.raw_body)!==c.raw_body_digest)bad()
 const {receipt_digest:_digest,...body}=r
 if(await noteProofDigest(body)!==r.receipt_digest||!same(await json(s,c.project_id,c.note_id,r.acceptance_envelope,amk,current),{content_receipt_format:1,receipt:contentBaseReceipt(r),candidate_digest:c.record_digest,wire_digest:c.wire_digest}))bad()
 check(current)
}
/** Validates stored proof evidence only; does NOT qualify its sequence for prefix/ACK. */
export async function authenticateContentSelfEcho2(s:BrowserSyncScope,row:BrowserInboxRecord,c:BrowserContentCandidate3,r:BrowserContentReceipt2,out:BrowserOutboxRecord,amk:AccountMasterKey,current:()=>boolean){
 check(current);if(row.state!=='content_note_self_echo_proven')bad()
 const p=validateContentSelfEchoProof2(row.content_note_self_echo_proof,s),{outcome_digest:_digest,...body}=p
 await authenticateContentReceipt2(s,r,c,out,amk,current)
 const wire=JSON.parse(row.wire_item),{device_id,server_sequence,...event}=wire.event
 if(device_id!==s.deviceId||server_sequence!==r.server_sequence||row.event_id!==r.event_id||p.server_sequence!==row.server_sequence||p.bootstrap_id!==c.bootstrap_id||p.candidate_digest!==c.record_digest||p.wire_digest!==c.wire_digest||p.receipt_digest!==r.receipt_digest||!same(p.header,c.header)||!same(p.reference,wire.event)||!same({event,object:wire.object},JSON.parse(c.wire_item))||await noteProofDigest(body)!==p.outcome_digest)bad()
 check(current)
}
