import {vi} from 'vitest'
import {canonical} from '@/cloud/projectMetadataCodec'
import {syncApi} from '@/api/sync'
import {resolutionFixture} from './resolution.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {BrowserResolutionPlanner} from './resolutionPlanner'
import type {NoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {encryptObjectBytes} from '@/crypto'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {encodeNoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {received as receiveLegacy} from './legacyNoteApply.testFixture'
import {contentConflictSetup,conflictGroup} from './contentConflict.testFixture'
import {openHistoryCandidate} from './noteHistory'
import {encodeBase64Url} from '@/api/base64url'
import {orderRow} from './stageOrder.testFixture'
import {BrowserStageOrderApply} from './stageOrderApply'
/** Actual receive owner, preserving original raw ciphertext and descriptor. */
export async function receiveLegacyResolutionOn3(f:Awaited<ReturnType<typeof plannerFixture>>){
 const original=f.received
 if(original.protocol_version!==2||JSON.parse(original.wire_item).event.operation!=='resolution')throw Error('genuine raw Legacy fixture required')
 f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.event_id!==original.event_id)
 ;(f.f.db.cursors[0] as any).pull_cursor=f.sequence-1
 const rawPage=JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[JSON.parse(original.wire_item)],next_cursor:f.sequence,has_more:false})
 await f.f.sync.commitInboundPage(scope,f.sequence-1,rawPage)
 return rawPage
}
export async function plannerFixture(strategy:NoteSyncResolutionV2['resolution']['strategy']='choose_version',count=2,local=false,legacy=false,route?:{stage?:boolean;format?:'html'|'plain';compressed?:boolean;order?:boolean;mixed?:boolean;mixedInventory?:boolean}){
 if(count===64)legacy=true
 const history=await resolutionFixture(strategy,count===64?2:count,local,legacy)
 if(route){
  const real=await contentConflictSetup(route.stage??false,route.format??'html',route.compressed??false,'update',route.mixed??false);await real.content.apply(scope,real.start+2);history.f=real
  const group=conflictGroup(real),parents=real.db.legacyNoteHistory!.filter((r:any)=>r.record_kind==='candidate'&&group.tip_event_ids.includes(r.event_id)) as typeof history.parents;parents.sort((a,b)=>a.event_id.localeCompare(b.event_id));history.parents=parents
  const opened=await Promise.all(parents.map(c=>openHistoryCandidate(scope,c,amk))),n=opened[0]!.note,other=opened[1]!.note,ids=group.tip_event_ids
  Object.assign(history.resolution.header,{parent_event_id:ids[0],additional_parent_event_ids:ids.slice(1)})
  const decision=history.resolution.resolution;decision.resolved_event_ids=ids
  if('selected_event_id'in decision)decision.selected_event_id=parents[0]!.event_id
  if(decision.strategy==='keep_both'){decision.retained_event_id=parents[1]!.event_id;decision.retained_note={...other,id:'retained-note',created_at:history.resolution.header.updated_at,updated_at:history.resolution.header.updated_at} as never}
  history.resolution.result=decision.strategy==='delete'?{operation:'delete',note:{id:n.id,project_id:n.project_id,stage_id:n.stage_id,source_type:n.source_type,source_map_id:n.source_map_id,source_node_id:n.source_node_id,content_format:n.content_format,deleted_at:history.resolution.header.updated_at}}:{operation:'upsert',note:{...n,...(decision.strategy==='manual_merge'?{content:'PRIVATE_ROUTE_MERGE'}:{})} as never}
  history.content.dependencies={bootstrap_id:real.b.bootstrap_id,metadata_event_id:real.m.event.header.event_id,stage_event_ids:route.stage?[(real as any).a.event.header.event_id]:[]};history.content.event=history.resolution
  if(route.mixedInventory){
   await receiveLegacy(real,real.start+3);await real.notes.apply(scope,real.start+3)
  }
  if(route.order){
   if(!route.stage)throw Error('order fixture requires Stage')
   const a=(real as any).a.event
   await orderRow({...real,stageEvents:[a]} as never,real.start+3+(route.mixedInventory?1:0))
   await new BrowserStageOrderApply(real.transaction,()=>true).bind(real.auth,real.bindings as never,real.keys as never).apply(scope,real.start+3+(route.mixedInventory?1:0))
  }
  history.row.server_sequence=real.start+3+(route.order?1:0)+(route.mixedInventory?1:0);const wire=JSON.parse(history.row.wire_item);wire.event.server_sequence=history.row.server_sequence
  const plain=frameContentNote(history.content),bytes=route.compressed?compressCanonicalFrame(plain):plain,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes)
  try{wire.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)};history.row.wire_item=JSON.stringify(wire)}finally{plain.fill(0);bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 }
 const f=history.f
 if(count===64){
  const root=history.parents[0]!.header.parent_event_id!
  for(let i=2;i<count;i++){await receiveLegacy(f,i+3,2,root,'upsert',undefined,'content-note');await f.notes.apply(scope,i+3)}
  const group=conflictGroup(f),parents=f.db.legacyNoteHistory.filter((r:any)=>r.record_kind==='candidate'&&group.tip_event_ids.includes(r.event_id)) as typeof history.parents
  parents.sort((a,b)=>a.event_id.localeCompare(b.event_id));history.parents=parents
  const h=history.resolution.header;h.parent_event_id=group.tip_event_ids[0]!;h.additional_parent_event_ids=group.tip_event_ids.slice(1);history.resolution.resolution.resolved_event_ids=group.tip_event_ids
  if(history.resolution.resolution.strategy!=='choose_version')throw Error('64-parent choose fixture only')
  history.resolution.resolution.selected_event_id=parents[0]!.event_id;history.resolution.result={operation:'upsert',note:(await openHistoryCandidate(scope,parents[0]!,amk)).note as never}
  history.row.server_sequence=count+3;const wire=JSON.parse(history.row.wire_item);wire.event.server_sequence=count+3
  const bytes=encodeNoteSyncResolutionV2(history.resolution),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes)
  try{wire.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)};history.row.wire_item=JSON.stringify(wire)}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 }
 // Only accepted ordinary producers persisted history. No future apply rows are
 // inserted into the scheduling fixture; the original received wire is separate.
 f.db.inbox.push({...history.row,record_version:1,state:'received',resolution_proof:undefined})
 const received=f.db.inbox.at(-1) as any;delete received.resolution_proof
 const currentRow=()=>f.db.inbox.find((r:any)=>r.event_id===history.row.event_id) as any
 ;(f.db.cursors[0] as any).pull_cursor=history.row.server_sequence
 let active=true
 const http=vi.spyOn(syncApi,'registerDevice').mockImplementation(async(_token,id)=>({protocol_version:1,device_id:id,last_ack_cursor:0}))
 const device=await new BrowserDeviceRegistration(f.transaction,()=>active).bind(f.auth,f.bindings as never).registerVerified(scope)
 const factory=new BrowserResolutionPlanner(f.transaction,f.localOwner,()=>active),runtime=factory.bind(f.auth,f.bindings as never,f.keys as never,device)
 const sequence=received.server_sequence
 const before=()=>structuredClone(f.db)
 const reseal=async(unchecked=false)=>{
  let bytes:Uint8Array
  if(unchecked){
   const raw=new TextEncoder().encode(canonical(legacy?history.resolution:history.content))
   if(legacy)bytes=raw
   else{bytes=new Uint8Array(20+raw.length);bytes.set([87,79,82,84,65,45,67,49,1,8,1,0]);new DataView(bytes.buffer).setUint32(12,raw.length);new DataView(bytes.buffer).setUint32(16,raw.length);bytes.set(raw,20);raw.fill(0)}
  }else bytes=legacy?encodeNoteSyncResolutionV2(history.resolution):frameContentNote(history.content)
  const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes)
  try{const wire=JSON.parse(currentRow().wire_item);wire.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)};currentRow().wire_item=JSON.stringify(wire)}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 }
 return{...history,f,runtime,factory,device,get received(){return currentRow()},sequence,before,reseal,http,close:()=>{active=false;f.close()}}
}
