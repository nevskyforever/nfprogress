import { routeSetup } from './noteTransport.testFixture'
import { received as receiveLegacy } from './legacyNoteApply.testFixture'
import { encodeNoteSyncResolutionV2 } from '@/cloud/noteSyncResolutionV2Codec'
import { contentLocalConflict } from './contentLocalConflict.testFixture'
import { contentConflictSetup,conflictGroup } from './contentConflict.testFixture'
import { scope,amk,at } from './bootstrap.testFixture'
import { frameContentNote,type ContentNoteEvent } from '@/cloud/contentNoteCodec'
import type { NoteSyncResolutionV2 } from '@/cloud/noteSyncResolutionV2Codec'
import { encryptObjectBytes,decryptObjectBytes } from '@/crypto'
import { encodeBase64Url,decodeBase64Url } from '@/api/base64url'
import { canonical } from '@/cloud/projectMetadataCodec'
import { noteProofDigest } from './legacyNoteApply'
import { openHistoryCandidate } from './noteHistory'
import type { BrowserNoteCandidate } from './noteHistoryRecords'
import type { LocalEnvelope,LocalProjectPayload,LocalNoteRecord } from './localAuthorityRecords'
import type { BrowserResolution4,BrowserResolutionProof1,BrowserResolutionInbox10,BrowserResolutionHead2,BrowserGroupTransition2 } from './resolutionRecords'
import { resolutionBytesDigest,type ResolutionInventory } from './resolutionAuthentication'

export async function sealResolutionFixture(value:unknown,entity='content-note',type:'note'|'project_metadata'='note'):Promise<LocalEnvelope>{
 const b=new TextEncoder().encode(canonical(value)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:entity,entityType:type},b)
 try{return{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{b.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
}
export async function fixtureDigest(r:unknown,field='record_digest'){const body={...r as Record<string,unknown>};delete body[field];return noteProofDigest(body)}
/** Genuine protected ordinary parent history + real AEAD; future Resolution rows exist only in memory. */
export async function resolutionFixture(strategy:NoteSyncResolutionV2['resolution']['strategy']='choose_version',parentCount=2,localAccepted=false,legacyRecords=false){
 let f:any
 if(legacyRecords){const base=await routeSetup(),root=await receiveLegacy(base,2,1,null,'upsert',undefined,'content-note');await base.notes.apply(scope,2);await receiveLegacy(base,3,2,root.event_id,'upsert',undefined,'content-note');await base.notes.apply(scope,3);await receiveLegacy(base,4,2,root.event_id,'upsert',undefined,'content-note');f={...base,content:base.notes}}
 else f=localAccepted?await contentLocalConflict():await contentConflictSetup()
 if(localAccepted){await f.content.apply(scope,3);await f.writer.seal(scope,'p',f.intent.event_id);await f.accept(f.db.outbox[0],4)}else await f.content.apply(scope,4)
 for(let i=2;i<parentCount;i++){await f.incoming(i+3,{mutation:'update',parent:f.parent.row.event_id});await f.content.apply(scope,i+3)}
 const sequence=parentCount+3,protocol=legacyRecords?2 as const:3 as const
 const group=structuredClone(conflictGroup(f)),head=structuredClone(f.db.legacyNoteHistory!.find((h:any)=>h.record_kind==='head')) as any
 const parents=f.db.legacyNoteHistory!.filter((c:any)=>c.record_kind==='candidate'&&group.tip_event_ids.includes(c.event_id)) as BrowserNoteCandidate[]
 parents.sort((a,b)=>a.event_id.localeCompare(b.event_id))
 const opened=await Promise.all(parents.map(c=>openHistoryCandidate(scope,c,amk))),chosen=opened[0]!,retained=opened[1]!,id=crypto.randomUUID()
 const selected=structuredClone(chosen.note) as any,clone={...structuredClone(retained.note),id:'retained-note',created_at:at,updated_at:at} as any
 const decision:NoteSyncResolutionV2['resolution']=strategy==='choose_version'?{conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:group.tip_event_ids,strategy,selected_event_id:parents[0]!.event_id}:strategy==='keep_both'?{conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:group.tip_event_ids,strategy,selected_event_id:parents[0]!.event_id,retained_event_id:parents[1]!.event_id,retained_note:clone}:{conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:group.tip_event_ids,strategy}
 const result:NoteSyncResolutionV2['result']=strategy==='delete'?{operation:'delete',note:{id:'content-note',project_id:'p',stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:at}}:{operation:'upsert',note:strategy==='manual_merge'?{...selected,content:'PRIVATE_AUTHENTIC_MERGED'}:selected}
 const resolution:NoteSyncResolutionV2={version:2,header:{event_id:id,parent_event_id:group.tip_event_ids[0]!,additional_parent_event_ids:group.tip_event_ids.slice(1),project_id:'p',entity_id:'content-note',entity_type:'note',operation:'resolution',revision:3,updated_at:at},mutation:'resolution',resolution:decision,result}
 const content:ContentNoteEvent={version:1,account_id:scope.canonicalUserId,device_id:'44444444-4444-4444-8444-444444444444',dependencies:{bootstrap_id:f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:resolution},frame=legacyRecords?encodeNoteSyncResolutionV2(resolution):frameContentNote(content),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
 const reference={event_id:id,device_id:content.device_id,server_sequence:sequence,project_id:'p',entity_id:'content-note',entity_type:'note' as const,operation:legacyRecords?'resolution' as const:'event' as const,revision:3,updated_at:at,deleted_at:null}
 const wire={event:reference,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}
 const received={record_version:1,state:'received',account_id:scope.accountId,device_id:scope.deviceId,event_id:id,server_sequence:sequence,protocol_version:protocol,wire_item:JSON.stringify(wire)}
 const before={project:structuredClone(f.db.localProjects![0]) as any,notes:[structuredClone(f.db.localNotes!.find((n:any)=>n.note_id==='content-note')) as LocalNoteRecord]}
 const b=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'p',entityType:'project_metadata'},{...before.project.envelope,nonce:decodeBase64Url(before.project.envelope.nonce),ciphertext:decodeBase64Url(before.project.envelope.ciphertext)})
 const project=JSON.parse(new TextDecoder().decode(b)) as LocalProjectPayload;b.fill(0);project.source_revision++
 if(strategy==='keep_both')project.member_ids.push('retained-note');project.member_ids.sort()
 const afterProject={...before.project,source_revision:project.source_revision,envelope:await sealResolutionFixture(project,'p','project_metadata')}
 const outputs=[result,...(strategy==='keep_both'?[{operation:'upsert' as const,note:clone}]:[])]
 const notes:LocalNoteRecord[]=[]
 for(const output of outputs){const n=output.note,deleted=output.operation==='delete';const source=deleted?{state:'tombstone',note:n,revision:0}:{state:'live',note:{...n,revision:0}};notes.push({record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:n.id,source_revision:project.source_revision,note_revision:0,deleted,envelope:await sealResolutionFixture({local_format:1,kind:'note',account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:n.id,source_revision:project.source_revision,source},n.id)})}
 notes.sort((a,b)=>a.note_id.localeCompare(b.note_id))
 const after={project:afterProject,notes}
 const r:BrowserResolution4={record_version:4,record_kind:'resolution',record_id:id,account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:'content-note',bootstrap_id:f.b.bootstrap_id,event_id:id,source_device_id:content.device_id,protocol_version:protocol,transport_kind:legacyRecords?'legacy_resolution_v2':'content_note_resolution_v2',server_sequence:sequence,header:resolution.header,wire_item:received.wire_item,wire_digest:await noteProofDigest({protocol_version:protocol,item:wire}),payload_digest:await noteProofDigest(resolution),dependency_digest:await noteProofDigest({scope,bootstrap_id:f.b.bootstrap_id,project_id:'p',note_id:'content-note',event_id:id,transport:received,dependencies:content.dependencies,owners:f.db.ownerHeads,bindings:f.db.projectBindings}),remote_group_id:decision.conflict_group_id,remote_generation:77,local_group_id:group.group_id,local_generation:group.conflict_generation,group_digest:await noteProofDigest(group),parent_event_ids:group.tip_event_ids,strategy,result_operation:result.operation,retained_note_id:strategy==='keep_both'?'retained-note':null,evidence_envelope:before.notes[0]!.envelope,record_digest:''}
 const {evidence_envelope:_e,record_digest:_d,...identity}=r
 const evidence={resolution_format:1,kind:'resolution_apply',identity,authenticated_payload:{wire_frame_digest:await resolutionBytesDigest(frame),wrapper_payload_digest:legacyRecords?null:await noteProofDigest(content),resolution_payload_digest:r.payload_digest},parents:await Promise.all(parents.map(async(c,i)=>{const m=group.members.find(m=>m.event_id===c.event_id)!,local=m.source==='local_unsealed',frozen=local?f.db.legacyNoteHistory.find((r:any)=>r.record_kind==='local_version'):null;return{event_id:c.event_id,revision:c.header.revision,operation:c.header.operation,history_digest:c.record_digest,inbox_digest:await noteProofDigest(f.db.inbox.find((r:any)=>r.event_id===c.event_id)??null),publication_source:local?'local_accepted':m.source,server_sequence:local?4:m.server_sequence,local_mutation_generation:local?c.mutation_generation:null,frozen_version_digest:frozen?.record_digest??null,snapshot_digest:await noteProofDigest(opened[i]!.note)}})),group_snapshot:group,head_before:head,source_before:before,source_after:after}
 r.evidence_envelope=await sealResolutionFixture(evidence);r.record_digest=await fixtureDigest(r)
 const transition:BrowserGroupTransition2={record_version:2,record_kind:'group_transition',record_id:group.group_id,account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:'content-note',bootstrap_id:f.b.bootstrap_id,group_id:group.group_id,from_generation:group.conflict_generation,from_digest:r.group_digest,resolution_event_id:id,resolution_digest:r.record_digest,resolved_parent_ids:r.parent_event_ids,effective_lifecycle:'resolved',record_digest:''};transition.record_digest=await fixtureDigest(transition)
 const h:BrowserResolutionHead2={...head,record_version:2,head_revision:head.head_revision+1,linear_head_event_id:id,tip_event_ids:[id],node_ref:{kind:'resolution_result',resolution_event_id:id,result_role:'original',resolution_digest:r.record_digest}}
 const cloneHead:BrowserResolutionHead2|undefined=r.retained_note_id?{...h,note_id:r.retained_note_id,head_revision:1,node_ref:{kind:'resolution_result',resolution_event_id:id,result_role:'retained',resolution_digest:r.record_digest}}:undefined
 const proof:BrowserResolutionProof1={record_version:1,owner_kind:'note_resolution',outcome:'applied',account_id:scope.accountId,bootstrap_id:f.b.bootstrap_id,protocol_version:protocol,reference,server_sequence:sequence,header:r.header,wire_digest:r.wire_digest,payload_digest:r.payload_digest,dependency_digest:r.dependency_digest,resolution_digest:r.record_digest,transition_digest:transition.record_digest,output_digests:{original:await noteProofDigest(notes.find(n=>n.note_id===r.note_id)),retained:r.retained_note_id?await noteProofDigest(notes.find(n=>n.note_id===r.retained_note_id)):null},outcome_digest:''};proof.outcome_digest=await fixtureDigest(proof,'outcome_digest')
 const row:BrowserResolutionInbox10={...received,protocol_version:protocol,record_version:10,state:'note_resolution_proven',resolution_proof:proof}
 const inventory:ResolutionInventory={history:[...f.db.legacyNoteHistory!.filter((h:any)=>h.record_kind!=='head'),r,transition,h,...(cloneHead?[cloneHead]:[])],rows:[...f.db.inbox,row],owners:f.db.ownerHeads!,bindings:f.db.projectBindings,out:f.db.outbox,receipts:f.db.receipts,intents:f.db.legacyNoteIntents,localNotes:f.db.localNotes,cursor:{...(f.db.cursors[0] as any),pull_cursor:sequence}}
 frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)
 return{f,r,h,cloneHead,transition,proof,row,evidence,inventory,content,resolution,parents}
}

export async function refreshResolutionFixture(f:Awaited<ReturnType<typeof resolutionFixture>>){
 f.r.evidence_envelope=await sealResolutionFixture(f.evidence);f.r.record_digest=await fixtureDigest(f.r)
 f.transition.resolution_digest=f.r.record_digest;f.transition.record_digest=await fixtureDigest(f.transition)
 if(f.h.node_ref.kind==='resolution_result')f.h.node_ref.resolution_digest=f.r.record_digest
 if(f.cloneHead?.node_ref.kind==='resolution_result')f.cloneHead.node_ref.resolution_digest=f.r.record_digest
 f.proof.resolution_digest=f.r.record_digest;f.proof.transition_digest=f.transition.record_digest;f.proof.outcome_digest=await fixtureDigest(f.proof,'outcome_digest')
}

/** Re-seal the original retained test wire, never a production writer. */
export async function reframeResolutionFixture(f:Awaited<ReturnType<typeof resolutionFixture>>,mode:'legacy'|'id1'){
 const {encodeNoteSyncResolutionV2}=await import('@/cloud/noteSyncResolutionV2Codec'),{compressCanonicalFrame}=await import('@/cloud/frameCompression')
 const frame=mode==='legacy'?encodeNoteSyncResolutionV2(f.resolution):compressCanonicalFrame(frameContentNote(f.content)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
 try{
  if(mode==='legacy'){f.r.protocol_version=2;f.r.transport_kind='legacy_resolution_v2';f.row.protocol_version=2;f.proof.protocol_version=2;f.proof.reference.operation='resolution'}
  const wire={event:structuredClone(f.proof.reference),object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}
  f.r.wire_item=f.row.wire_item=JSON.stringify(wire);f.r.wire_digest=await noteProofDigest({protocol_version:f.r.protocol_version,item:wire});f.proof.wire_digest=f.r.wire_digest
  const {evidence_envelope:_e,record_digest:_d,...identity}=f.r;f.evidence.identity=identity
  f.evidence.authenticated_payload={wire_frame_digest:await resolutionBytesDigest(frame),wrapper_payload_digest:mode==='legacy'?null:await noteProofDigest(f.content),resolution_payload_digest:f.r.payload_digest}
  await refreshResolutionFixture(f)
 }finally{frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
}
