import {readerFrame} from './canonicalReaders.testFixture'
import {openHistoryCandidate} from './noteHistory'
import {plannerFixture,receiveLegacyResolutionOn3} from './resolutionPlanner.testFixture'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {scope,amk,at} from './bootstrap.testFixture'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {encodeNoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import type {NoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
export async function continuationFixture(strategy:NoteSyncResolutionV2['resolution']['strategy']='keep_both',legacy=false,route?:{stage?:boolean;format?:'html'|'plain';compressed?:boolean;order?:boolean;mixed?:boolean;mixedInventory?:boolean},local=false,count=2,legacy3=false,prefixFamilies?:{compressed:boolean}){
 if(count===64)legacy=true
 const f=await plannerFixture(strategy,count,local,legacy,route)
 if(prefixFamilies){
  // Produce the family outcomes before F; no applied evidence is manufactured.
  const {stageRow}=await import('./stageApply.testFixture'),{orderRow}=await import('./stageOrder.testFixture'),{BrowserStageApply}=await import('./stageApply'),{BrowserStageOrderApply}=await import('./stageOrderApply')
  const wire=JSON.parse(f.received.wire_item),start=f.sequence,producer={...f.f,metadataEvent:{header:{event_id:f.content.dependencies.metadata_event_id}}} as any
  f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.event_id!==wire.event.event_id);(f.f.db.cursors[0] as any).pull_cursor=start-1
  const a=await stageRow(producer,start,prefixFamilies);await new BrowserStageApply(f.f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never).apply(scope,start)
  await orderRow({...producer,stageEvents:[a.event]},start+1,prefixFamilies);await new BrowserStageOrderApply(f.f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never).apply(scope,start+1)
  // An unrelated project's real Metadata owner also participates in the account prefix.
  const {frameProjectMetadata}=await import('@/cloud/projectMetadataCodec'),{BrowserImportedMetadataApply}=await import('./importedMetadataApply')
  const binding=await f.f.projects.importRemote(scope,{project_id:'other',bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0}),event=structuredClone(f.f.m.event)
  Object.assign(event.header,{project_id:'other',entity_id:'other',bootstrap_id:binding.bootstrap_id,event_id:crypto.randomUUID()})
  const bytes=frameProjectMetadata(event),encrypted=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'other',entityId:'other',entityType:'project_metadata'},bytes)
  const reference={...event.header,entity_type:'project_metadata' as const,operation:'upsert' as const,server_sequence:start+2,deleted_at:null}
  // The wire descriptor has the transport's exact field set.
  const ref={event_id:reference.event_id,device_id:reference.device_id,project_id:'other',entity_id:'other',entity_type:reference.entity_type,operation:reference.operation,server_sequence:reference.server_sequence,revision:reference.revision,updated_at:reference.updated_at,deleted_at:null}
  try{await f.f.sync.commitInboundPage(scope,start+1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:ref,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(encrypted.nonce),ciphertext:encodeBase64Url(encrypted.ciphertext)}}],next_cursor:start+2,has_more:false}))}finally{bytes.fill(0);encrypted.nonce.fill(0);encrypted.ciphertext.fill(0)}
  await new BrowserImportedMetadataApply(f.f.transaction,f.f.sync).apply(scope,ref,f.f.auth,f.f.bindings as never,f.f.keys as never)
  wire.event.server_sequence=start+3
  await f.f.sync.commitInboundPage(scope,start+2,JSON.stringify({protocol_version:2,encrypted_sync_version:2,items:[wire],next_cursor:start+3,has_more:false}))
 }
 if(legacy3)await receiveLegacyResolutionOn3(f)
 const rootSequence=f.received.server_sequence
 const applier=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,rootSequence)
 await applier.commit(await applier.prepare(p.token))
 let active=true
 const runtime=new BrowserResolutionContinuation(f.f.transaction,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 let sequence=rootSequence
 const receive=async(options:{id?:string;parent?:string|null;revision?:number;deleted?:boolean;protocol?:2|3;compressed?:boolean;content?:string;rawLegacyOn3?:boolean;unchecked?:boolean;alter?:(plaintext:any,wrapper:any,reference:any)=>void}={})=>{
  const id=options.id??'content-note',protocol=options.protocol??(legacy?2:3),parent=options.parent===undefined?f.resolution.header.event_id:options.parent,revision=options.revision??4
  const original=f.resolution.result.note as any,other=f.resolution.resolution.strategy==='keep_both'?f.resolution.resolution.retained_note:undefined
  const live=other&&other.id===id?other:'content'in original?original:(await openHistoryCandidate(scope,f.parents[0]!,amk)).note
  // A genuine Content update must explicitly publish its eligible empty metadata;
  // the Legacy root and original parent evidence are never normalized or rewritten.
  const note=options.deleted?{id,project_id:'p',stage_id:original.stage_id,source_type:'project',source_map_id:null,source_node_id:null,content_format:original.content_format,deleted_at:at}:{...live,id,content:options.content??'AUTHENTIC_SUCCESSOR',updated_at:at,...(protocol===3&&!options.rawLegacyOn3?{metadata:{}}:{})}
  const h={event_id:crypto.randomUUID(),project_id:'p',entity_id:id,entity_type:'note' as const,operation:options.deleted?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:options.deleted?at:null}
  const plaintext=createNoteSyncPlaintext(h,parent,note).plaintext
  const wrapper={version:1 as const,account_id:scope.canonicalUserId,device_id:f.content.device_id,dependencies:structuredClone(f.content.dependencies),event:plaintext}
  const reference={...h,operation:protocol===2||options.rawLegacyOn3?h.operation:'event',deleted_at:protocol===2||options.rawLegacyOn3?h.deleted_at:null,device_id:f.content.device_id,server_sequence:++sequence}
  options.alter?.(plaintext,wrapper,reference)
  const raw=protocol===2||options.rawLegacyOn3?encodeNoteSyncPlaintext(plaintext):options.unchecked?readerFrame({id:8,version:1,event:wrapper}):frameContentNote(wrapper)
  const frame=protocol===3&&options.compressed?compressCanonicalFrame(raw):raw,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:'note'},frame)
  try{await f.f.sync.commitInboundPage(scope,sequence-1,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event:reference,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0);raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  return{sequence,event_id:h.event_id,plaintext}
 }
 return{...f,sequence:rootSequence,get received(){return f.received},runtime,applier,receive,close:()=>{active=false;f.close()}}
}
