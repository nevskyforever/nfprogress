import {vi} from 'vitest'
import {metadataSetup,metadataRow} from './metadataPrefix.testFixture'
import {stageRow} from './stageApply.testFixture'
import {orderRow} from './stageOrder.testFixture'
import {scope,amk,at,note,project} from './bootstrap.testFixture'
import {keyedTransaction} from './v10Transport.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserV10Recovery} from './v10Recovery'
import {BrowserResolutionPlanner} from './resolutionPlanner'
import {syncApi} from '@/api/sync'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {encodeNoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encodeNoteSyncResolutionV2,type NoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import type {BrowserSyncTransaction} from './syncDurability'

/** All positive applied evidence is produced by K calling real accepted readers.
 * The sender prepares genuine AEAD before the receiver applies anything. */
export async function recoveryFixture(strategy:NoteSyncResolutionV2['resolution']['strategy']='keep_both',protocol:2|3=3,compressed=false,mixed=false,otherProject=false,baseline=false){
 const f=await metadataSetup(),m=await metadataRow(f,1),metadata=JSON.parse(m.row.wire_item)
 if(otherProject){
  // Pre-Resolution canonical authority, never an invented post-v10 source.
  await f.local.initializeProject(scope,{project:project('q'),notes:[]})
  await f.projects.importRemote(scope,{project_id:'q',bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
 }
 // Retain the genuine metadata through transport rather than injecting apply evidence.
 f.db.inbox=[];(f.db.cursors[0] as any).pull_cursor=0
 await f.sync.commitInboundPage(scope,0,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[metadata],next_cursor:1,has_more:true}))
 let sequence=1,stageId:string|null=null,stageRefs:string[]=[]
 if(mixed){
  const a=await stageRow({...f,metadataEvent:m.event} as never,++sequence,{compressed}),o=await orderRow({...f,metadataEvent:m.event,stageEvents:[a.event]} as never,++sequence,{compressed})
  // Test sender fixtures retain only received rows, never synthesize proof/source.
  void o;stageId='s';stageRefs=[a.event.header.event_id]
 }
 const since=sequence,items:any[]=[],peer='44444444-4444-4444-8444-444444444444'
 const dependencies={bootstrap_id:f.b.bootstrap_id,metadata_event_id:m.event.header.event_id,stage_event_ids:stageRefs}
 const fresh=(id='content-note')=>{const {revision:_rev,...n}=note(id);return{...n,stage_id:stageId,metadata:{},content:'REAL_PENDING_READER_SOURCE'.repeat(30)}}
 const append=async(payload:any,id='content-note',version:2|3=protocol)=>{
  const h=payload.header,raw=payload.version===2?(version===2?encodeNoteSyncResolutionV2(payload):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:peer,dependencies,event:payload})):(version===2?encodeNoteSyncPlaintext(payload):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:peer,dependencies,event:payload}))
  const frame=version===3&&compressed?compressCanonicalFrame(raw):raw,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:'note'},frame)
  try{items.push({event:{event_id:h.event_id,device_id:peer,server_sequence:++sequence,project_id:'p',entity_id:id,entity_type:'note',operation:version===2?h.operation:'event',revision:h.revision,updated_at:at,deleted_at:version===2?h.deleted_at??null:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}})}finally{frame.fill(0);raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  return{sequence,event_id:h.event_id,payload}
 }
 const ordinary=async(id='content-note',parent:string|null=null,revision=1,deleted=false,version:2|3=protocol)=>{
  const h={event_id:crypto.randomUUID(),project_id:'p',entity_id:id,entity_type:'note' as const,operation:deleted?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:deleted?at:null},n=fresh(id)
  return append(createNoteSyncPlaintext(h,parent,deleted?{id,project_id:'p',stage_id:stageId,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:at}:n).plaintext,id,version)
 }
 // N baselines are genuine received applies BEFORE F, produced by K's real
 // ordinary owners. No applied row/proof/source is inserted by this fixture.
 if(baseline){
  const live=await ordinary('baseline-live');await ordinary('baseline-live',live.event_id,2)
  const tombstone=await ordinary('baseline-deleted');await ordinary('baseline-deleted',tombstone.event_id,2,true)
 }
 const root=await ordinary(),a=await ordinary('content-note',root.event_id,2),b=await ordinary('content-note',root.event_id,2)
 const parents=[a,b].sort((a,b)=>a.event_id.localeCompare(b.event_id)),ids=parents.map(p=>p.event_id),chosen=parents[0]!,other=parents[1]!
 const decision:NoteSyncResolutionV2['resolution']={conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:ids,strategy,...(['choose_version','keep_both'].includes(strategy)?{selected_event_id:chosen.event_id}:{}),...(strategy==='keep_both'?{retained_event_id:other.event_id,retained_note:{...other.payload.note,id:'retained-note',created_at:at,updated_at:at}}:{})} as NoteSyncResolutionV2['resolution']
 const resolution:NoteSyncResolutionV2={version:2,header:{event_id:crypto.randomUUID(),parent_event_id:ids[0]!,additional_parent_event_ids:ids.slice(1),project_id:'p',entity_id:'content-note',entity_type:'note',operation:'resolution',revision:3,updated_at:at},mutation:'resolution',resolution:decision,result:strategy==='delete'?{operation:'delete',note:{id:'content-note',project_id:'p',stage_id:stageId,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:at}}:{operation:'upsert',note:{...chosen.payload.note,...(strategy==='manual_merge'?{content:'REAL_MERGED_READER_OUTPUT'}:{})}}}
 const r=await append(resolution),children=[await ordinary('content-note',r.event_id,4,strategy==='delete')]
 if(strategy==='keep_both')children.push(await ordinary('retained-note',r.event_id,4))
 const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items,next_cursor:sequence,has_more:false})
 await f.sync.commitInboundPage(scope,since,rawPage)
 let active=true
 vi.spyOn(syncApi,'registerDevice').mockImplementation(async(_token,id)=>({protocol_version:1,device_id:id,last_ack_cursor:0}))
 const device=await new BrowserDeviceRegistration(f.transaction,()=>active).bind(f.auth,f.bindings as never).registerVerified(scope),transaction=keyedTransaction(f.transaction)
 const create=(tx:BrowserSyncTransaction=transaction)=>new BrowserV10Recovery(tx,f.localOwner,()=>active).bind(f.auth,f.bindings as never,f.keys as never,device)
 const planner=new BrowserResolutionPlanner(transaction,f.localOwner,()=>active).bind(f.auth,f.bindings as never,f.keys as never,device)
 return{f,transaction,create,runtime:create(),planner,device,root,parents,r,children,resolution,sequence,since,rawPage,items,m,before:()=>structuredClone(f.db),close:()=>{active=false;f.close()}}
}
