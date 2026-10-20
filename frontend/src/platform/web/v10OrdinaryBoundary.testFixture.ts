import {scope,amk,at,note} from './bootstrap.testFixture'
import {recoveryFixture} from './v10Recovery.testFixture'
import {BrowserLegacyNoteApply} from './legacyNoteApply'
import {BrowserContentNoteApply} from './contentNoteApply'
import {BrowserImportedMetadataApply} from './importedMetadataApply'
import {BrowserStageApply} from './stageApply'
import {BrowserStageOrderApply} from './stageOrderApply'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Transport} from './v10Transport'
import {BrowserSyncDurability} from './syncDurability'
import {authenticateContinuationHistory,verifyContinuationSources,openHistoricalJson} from './resolutionHistorical'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {encodeNoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {canonical,frameProjectMetadata,type ProjectMetadataEvent} from '@/cloud/projectMetadataCodec'
import {frameStructuralEvent,type StructuralEvent} from '@/cloud/stageCodec'
import golden from '@/cloud/__fixtures__/stageCodecV1.json'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'

/** Audit only: genuine K/F/H/G creates every positive history/proof. No new
 * ordinary route is enabled, and no future history is hidden from any owner. */
export async function ordinaryBoundaryFixture(...args:Parameters<typeof recoveryFixture>){
 const f=await recoveryFixture(...args);await f.runtime.run(scope,{maxEvents:32})
 const tx=f.transaction,notes=new BrowserLegacyNoteApply(tx,f.f.localOwner,()=>true),legacy=notes.bind(f.f.auth,f.f.bindings as never,f.f.keys as never)
 const content=new BrowserContentNoteApply(notes).bind(f.f.auth,f.f.bindings as never,f.f.keys as never),sync=new BrowserSyncDurability(tx)
 const metadata=new BrowserImportedMetadataApply(tx,sync),stage=new BrowserStageApply(tx,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never),order=new BrowserStageOrderApply(tx,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never)
 const h=new BrowserResolutionContinuation(tx,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),g=new BrowserResolutionPrefix(tx,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),j=new BrowserV10Transport(tx,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const load=()=>tx<ResolutionInventorySnapshot>(scope,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,scope,()=>true,result,abort))
 const history=async(currentSource=true)=>{const v=await load(),verified=await authenticateContinuationHistory(scope,v,amk,()=>true);if(currentSource)await verifyContinuationSources(scope,v,verified,amk,()=>true);return{resolutions:verified.resolutions.size,rows:verified.rows.length}}
 const receive=(type:string,id:string,projectId='p',protocol:2|3=3,operation='upsert',revision=1)=>{
  const sequence=(f.f.db.cursors[0] as any).pull_cursor+1,event={event_id:crypto.randomUUID(),device_id:'44444444-4444-4444-8444-444444444444',server_sequence:sequence,project_id:projectId,entity_id:id,entity_type:type,operation,revision,updated_at:at,deleted_at:null}
  return{sequence,event,protocol}
 }
 const retain=async(event:Record<string,any>,frame:Uint8Array,protocol:2|3)=>{
  const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:event.project_id,entityId:event.entity_id,entityType:event.entity_type},frame)
  const page=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:event.server_sequence,has_more:false})
  try{await sync.commitInboundPage(scope,event.server_sequence-1,page)}finally{frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  return{sequence:event.server_sequence as number,page,since:event.server_sequence-1,event}
 }
 const incomingNote=async(protocol:2|3,compressed=false,projectId='p')=>{
  const id=`independent-${projectId}`,p=receive('note',id,projectId,protocol,protocol===3?'event':'upsert'),h={event_id:p.event.event_id,project_id:projectId,entity_id:id,entity_type:'note' as const,operation:'upsert' as const,revision:1,updated_at:at,deleted_at:null}
  const {revision:_r,...n}=note(id);n.project_id=projectId;n.metadata={}
  const plain=createNoteSyncPlaintext(h,null,n).plaintext,binding=f.f.db.projectBindings.find((r:any)=>r.project_id===projectId) as any,mh=f.f.db.ownerHeads!.find((r:any)=>r.owner_kind==='project_metadata'&&r.owner_id===projectId) as any
  const raw=protocol===2?encodeNoteSyncPlaintext(plain):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:p.event.device_id,dependencies:{bootstrap_id:binding.bootstrap_id,metadata_event_id:mh.tip_event_ids[0],stage_event_ids:[]},event:plain}),frame=protocol===3&&compressed?compressCanonicalFrame(raw):raw
  try{return await retain(p.event,frame,protocol)}finally{raw.fill(0)}
 }
 const incomingMetadata=async(projectId='p',compressed=false)=>{
  const old=f.f.db.ownerHeads!.find((r:any)=>r.owner_kind==='project_metadata'&&r.owner_id===projectId) as any,binding=f.f.db.projectBindings.find((r:any)=>r.project_id===projectId) as any,p=receive('project_metadata',projectId,projectId),revision=old?old.history.length+1:1
  const event:ProjectMetadataEvent=structuredClone(f.m.event);Object.assign(event.header,{bootstrap_id:binding.bootstrap_id,project_id:projectId,entity_id:projectId,event_id:p.event.event_id,operation:old?'update':'create',revision,generation:revision,parent_event_ids:old?old.tip_event_ids:[]});event.metadata!.name='AUTHENTIC_METADATA_AFTER_RESOLUTION'
  const raw=frameProjectMetadata(event),frame=compressed?compressCanonicalFrame(raw):raw;p.event.revision=revision
  try{return await retain(p.event,frame,3)}finally{raw.fill(0)}
 }
 const incomingStage=async(orderEvent=false,compressed=false)=>{
  const p=receive(orderEvent?'stage_order':'stage',orderEvent?'stage_order':'audit-stage'),event=structuredClone(golden.event) as StructuralEvent
  Object.assign(event.header,{account_id:scope.canonicalUserId,bootstrap_id:f.f.b.bootstrap_id,project_id:'p',entity_id:p.event.entity_id,entity_type:p.event.entity_type,event_id:p.event.event_id,device_id:p.event.device_id,operation:'create',revision:1,generation:1,parent_event_ids:[],metadata_event_id:(f.f.db.ownerHeads!.find((r:any)=>r.owner_kind==='project_metadata'&&r.owner_id==='p') as any).tip_event_ids[0],updated_at:at})
  if(orderEvent){event.stage=null;event.stage_ids=[];event.stage_heads={}}
  const raw=frameStructuralEvent(event),frame=compressed?compressCanonicalFrame(raw):raw
  try{return await retain(p.event,frame,3)}finally{raw.fill(0)}
 }
 const otherProject=async()=>{
  const m=await incomingMetadata('q');await metadata.apply(scope,m.event as never,f.f.auth,f.f.bindings as never,f.f.keys as never)
 }
 const sourceProbe=async(member:boolean)=>{
  // NEGATIVE FIXTURE ONLY. Valid AEAD is deliberately NOT an apply authority.
  // No inbox/history/proof is synthesized, and no runtime consumes a fake grant.
  const row=f.f.db.localProjects!.find((r:any)=>r.project_id==='p') as any,bytes=await openHistoricalJson(scope,'p','p','project_metadata',row.envelope,amk,()=>true)
  let payload:any;try{payload=JSON.parse(new TextDecoder().decode(bytes))}finally{bytes.fill(0)}
  payload.source_revision++
  const seal=async(value:unknown,id:string,type='note')=>{const raw=new TextEncoder().encode(canonical(value));const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:type},raw);try{return{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}}
  if(member){
   const n=note('unqualified-local-probe');n.revision=0
   const source={local_format:1,kind:'note',account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:n.id,source_revision:payload.source_revision,source:{state:'live',note:n}}
   f.f.db.localNotes!.push({record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:'p',note_id:n.id,source_revision:payload.source_revision,note_revision:0,deleted:false,envelope:await seal(source,n.id)})
   payload.member_ids.push(n.id);payload.member_ids.sort()
  }
  row.source_revision=payload.source_revision;row.envelope=await seal(payload,'p','project_metadata')
 }
 return{...f,legacy,content,metadata,stage,order,h,g,j,load,history,incomingNote,incomingMetadata,incomingStage,otherProject,sourceProbe}
}
