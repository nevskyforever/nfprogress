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
export async function continuationFixture(strategy:NoteSyncResolutionV2['resolution']['strategy']='keep_both',legacy=false,route?:{stage?:boolean;format?:'html'|'plain';compressed?:boolean;order?:boolean;mixed?:boolean;mixedInventory?:boolean},local=false,count=2,legacy3=false){
 if(count===64)legacy=true
 const f=await plannerFixture(strategy,count,local,legacy,route)
 if(legacy3)await receiveLegacyResolutionOn3(f)
 const applier=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,f.sequence)
 await applier.commit(await applier.prepare(p.token))
 let active=true
 const runtime=new BrowserResolutionContinuation(f.f.transaction,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 let sequence=f.sequence
 const receive=async(options:{id?:string;parent?:string;revision?:number;deleted?:boolean;protocol?:2|3;compressed?:boolean;content?:string;rawLegacyOn3?:boolean;unchecked?:boolean;alter?:(plaintext:any,wrapper:any,reference:any)=>void}={})=>{
  const id=options.id??'content-note',protocol=options.protocol??(legacy?2:3),parent=options.parent??f.resolution.header.event_id,revision=options.revision??4
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
 return{...f,get received(){return f.received},runtime,applier,receive,close:()=>{active=false;f.close()}}
}
