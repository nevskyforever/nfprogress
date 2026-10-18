// Synthetic format/authentication specimens only. No production authorship or writer activation claim.
import {scope,amk,at} from './bootstrap.testFixture'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {canonical} from '@/cloud/projectMetadataCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {noteProofDigest} from './legacyNoteApply'
import {contentIntentIdentity,contentBaseReceipt,type BrowserContentIntent2,type BrowserContentCandidate3,type BrowserContentReceipt2,type BrowserContentSelfEchoProof2} from './contentAuthorityRecords'
export async function authorityEnvelope(value:unknown){const bytes=new TextEncoder().encode(canonical(value)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes);try{return{crypto_version:1 as const,aad_version:1 as const,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}}
export async function contentAuthorityFixture(compressed=false,kind:'intent'|'sealed'|'accepted'|'echo'='echo'){
 const f=await routeSetup(),root=await contentRow(f,2);await new BrowserContentNoteApplyRuntime(f.notes).apply(scope,2)
 const snapshot=structuredClone(f.db.localNotes![0]) as BrowserContentIntent2['snapshot'],eventId=crypto.randomUUID(),ordinal=1
 const intent:BrowserContentIntent2={record_version:2,transport_kind:'content_note_v1',account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:'content-note',bootstrap_id:f.b.bootstrap_id,event_id:eventId,operation:'upsert',revision:2,parent_event_id:root.row.event_id,updated_at:at,deleted_at:null,local_ordinal:ordinal,mutation_generation:1,dependencies:structuredClone(root.e.dependencies),snapshot,snapshot_digest:await noteProofDigest(snapshot),intent_envelope:snapshot.envelope,seal_state:'pending',seal_attempt_count:0,last_error_code:null,next_attempt_at:null}
 intent.intent_envelope=await authorityEnvelope({intent_format:2,identity:contentIntentIdentity(intent)})
 const e=structuredClone(root.e);if(e.event.version!==1)throw Error('ordinary fixture required');e.device_id=scope.deviceId;Object.assign(e.event.header,{event_id:eventId,parent_event_id:root.row.event_id,revision:2});e.event.mutation='update'
 const id0=frameContentNote(e),frame=compressed?compressCanonicalFrame(id0):id0,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
 const wire={event:{event_id:eventId,project_id:'p',entity_id:'content-note',entity_type:'note',operation:'event',revision:2,updated_at:at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}
 const raw=JSON.stringify({protocol_version:3,encrypted_sync_version:3,device_id:scope.deviceId,items:[wire]})
 const candidate:BrowserContentCandidate3={record_version:3,record_kind:'candidate',record_id:eventId,account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:'content-note',bootstrap_id:f.b.bootstrap_id,event_id:eventId,source_device_id:scope.deviceId,protocol_version:3,transport_kind:'content_note_v1',origin:'local_sealed',codec_id:8,frame_version:1,codec_version:1,compression_id:frame[11] as 0|1,header:structuredClone(e.event.header),intent:structuredClone(intent),wire_item:JSON.stringify(wire),wire_digest:await noteProofDigest({protocol_version:3,item:wire}),raw_body_digest:await noteProofDigest(raw),logical_digest:await noteProofDigest(e),authorship_envelope:snapshot.envelope,record_digest:''}
 const {authorship_envelope:_a,record_digest:_r,...body}=candidate;candidate.authorship_envelope=await authorityEnvelope({content_outbound_format:1,kind:'sealed_authorship',candidate_body_digest:await noteProofDigest(body)})
 const {record_digest:_d,...record}=candidate;candidate.record_digest=await noteProofDigest(record)
 const out={record_version:1 as const,account_id:scope.accountId,device_id:scope.deviceId,event_id:eventId,local_ordinal:1,protocol_version:3 as const,state:kind==='accepted'||kind==='echo'?'accepted' as const:'sealed' as const,raw_body:raw}
 const receipt:BrowserContentReceipt2={record_version:2,owner_kind:'content_note_acceptance',account_id:scope.accountId,device_id:scope.deviceId,event_id:eventId,protocol_version:3,server_sequence:3,duplicate:false,candidate_digest:candidate.record_digest,wire_digest:candidate.wire_digest,acceptance_envelope:snapshot.envelope,receipt_digest:''}
 receipt.acceptance_envelope=await authorityEnvelope({content_receipt_format:1,receipt:contentBaseReceipt(receipt),candidate_digest:candidate.record_digest,wire_digest:candidate.wire_digest})
 const {receipt_digest:_receipt,...receiptBody}=receipt;receipt.receipt_digest=await noteProofDigest(receiptBody)
 const reference={...wire.event,device_id:scope.deviceId,server_sequence:3} as BrowserContentSelfEchoProof2['reference']
 const proof:BrowserContentSelfEchoProof2={record_version:2,owner_kind:'content_note_self_echo',outcome:'acknowledged',account_id:scope.accountId,device_id:scope.deviceId,bootstrap_id:f.b.bootstrap_id,protocol_version:3,reference,server_sequence:3,codec_id:8,frame_version:1,codec_version:1,header:structuredClone(candidate.header),mutation:'update',history_event_id:eventId,candidate_digest:candidate.record_digest,wire_digest:candidate.wire_digest,receipt_digest:receipt.receipt_digest,outcome_digest:''}
 const {outcome_digest:_p,...proofBody}=proof;proof.outcome_digest=await noteProofDigest(proofBody)
 const row={record_version:9 as const,state:'content_note_self_echo_proven' as const,account_id:scope.accountId,device_id:scope.deviceId,event_id:eventId,server_sequence:3,protocol_version:3 as const,wire_item:JSON.stringify({event:reference,object:wire.object}),content_note_self_echo_proof:proof}
 ;(f.db.cursors[0] as any).next_local_ordinal=2
 if(kind==='intent')f.db.legacyNoteIntents!.push(intent)
 else{f.db.legacyNoteHistory!.push(candidate);const head=f.db.legacyNoteHistory!.find((h:any)=>h.record_kind==='head') as any;head.head_revision++;head.linear_head_event_id=eventId;head.tip_event_ids=[eventId];f.db.outbox.push(out);if(kind!=='sealed')f.db.receipts.push(receipt);if(kind==='echo'){f.db.inbox.push(row);(f.db.cursors[0] as any).pull_cursor=3}}
 id0.fill(0);frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)
 return{...f,intent,candidate,receipt,proof,row,out,event:e,inventory:()=>({history:f.db.legacyNoteHistory!,intents:f.db.legacyNoteIntents!,out:f.db.outbox,receipts:f.db.receipts,rows:f.db.inbox,bindings:f.db.projectBindings,localNotes:f.db.localNotes!,cursor:f.db.cursors[0] as any})}
}
