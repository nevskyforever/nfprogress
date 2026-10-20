import {vi} from 'vitest'
import {plannerFixture} from './resolutionPlanner.testFixture'
import {scope,amk,at} from './bootstrap.testFixture'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {encodeNoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {openHistoryCandidate} from './noteHistory'
import type {BrowserSyncTransaction} from './syncDurability'

// Give the scheduling driver native range/key semantics. The historical
// fixtures and their deliberately small request scheduler remain unchanged.
export function keyedTransaction(base:BrowserSyncTransaction):BrowserSyncTransaction {
 vi.stubGlobal('IDBKeyRange',{bound:(lower:unknown[],upper:unknown[],lowerOpen=false,upperOpen=false)=>({lower,upper,lowerOpen,upperOpen})})
 return (s,stores,mode,schedule)=>base(s,stores,mode,(tx,result,abort)=>{
  const proxy=new Proxy(tx,{get:(target,key)=>key==='objectStore'?(name:string)=>{
   const store=target.objectStore(name)
   // IndexedDB compound keys use code-unit order, not locale/insertion order.
   if(name==='localNotes')return new Proxy(store,{get:(target,key)=>{
    if(key==='openCursor')return(range:any)=>{
     const request=target.getAll(range);let handler:((this:IDBRequest,event:Event)=>unknown)|null=null
     const emit=()=>{
      const rows=[...request.result as any[]].sort((a,b)=>a.project_id<b.project_id?-1:a.project_id>b.project_id?1:a.note_id<b.note_id?-1:a.note_id>b.note_id?1:0);let position=0
      const next=()=>{const value=rows[position];Object.defineProperty(request,'result',{configurable:true,value:value?{value,continue:()=>{position++;const tick=target.get([s.accountId,rows[0].project_id,rows[0].note_id]);tick.onsuccess=next}}:null});handler?.call(request,{} as Event)}
      next()
     }
     Object.defineProperty(request,'onsuccess',{get:()=>emit,set:value=>{handler=value}});return request
    }
    const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
   }})
   if(name!=='inbox')return store
   return new Proxy(store,{get:(target,key)=>{
    if(key==='openCursor'||key==='count')return(range:any)=>{
     const request=target.getAll({lower:[s.accountId]} as never),nativeSuccess=()=>{
      const rows=(request.result as any[]).filter(r=>range.lower.length===1||r.server_sequence>range.lower[1]||!range.lowerOpen&&r.server_sequence===range.lower[1]).filter(r=>range.upper.length===1||Array.isArray(range.upper[1])||r.server_sequence<range.upper[1]||!range.upperOpen&&r.server_sequence===range.upper[1]).sort((a,b)=>a.server_sequence-b.server_sequence)
      if(key==='count'){Object.defineProperty(request,'result',{configurable:true,value:rows.length});handler?.call(request,{} as Event);return}
      let position=0
      const emit=()=>{const value=rows[position];Object.defineProperty(request,'result',{configurable:true,value:value?{value,key:[value.account_id,value.server_sequence],primaryKey:[value.account_id,value.server_sequence],continue:()=>{position++;const tick=target.get([s.accountId,rows[0].server_sequence]);tick.onsuccess=()=>emit()}}:null});handler?.call(request,{} as Event)}
      emit()
     }
     let handler:((this:IDBRequest,event:Event)=>unknown)|null=null
     Object.defineProperty(request,'onsuccess',{get:()=>nativeSuccess,set:value=>{handler=value}})
     return request
    }
    const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value
   }})
  }:Reflect.get(target,key)})
  schedule(proxy,result,abort)
 })
}

export async function transportFixture(strategy:Parameters<typeof plannerFixture>[0]='keep_both',protocol:2|3=3,compressed=false,mixed=false,conflict=false){
 const f=await plannerFixture(strategy,2,false,protocol===2,mixed?{stage:true,order:true,mixedInventory:true,compressed}:undefined)
 const since=f.sequence-1,items=[JSON.parse(f.received.wire_item)]
 // This fixture's pending R has never been applied. Retain it together with
 // genuine encrypted descendants through the real transport, then use F/H/G.
 f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.event_id!==f.received.event_id)
 ;(f.f.db.cursors[0] as any).pull_cursor=since
 const child=async(id='content-note',parent=f.resolution.header.event_id,revision=4)=>{
  const output=f.resolution.result.note,retained=f.resolution.resolution.strategy==='keep_both'?f.resolution.resolution.retained_note:undefined
  const live=retained?.id===id?retained:'content'in output?output:(await openHistoryCandidate(scope,f.parents[0]!,amk)).note
  const deleted=strategy==='delete',note=deleted?{id,project_id:'p',stage_id:output.stage_id,source_type:'project' as const,source_map_id:null,source_node_id:null,content_format:output.content_format,deleted_at:at}:{...live,id,content:'AUTHENTIC_TRANSPORT_CHILD',updated_at:at}
  const h={event_id:crypto.randomUUID(),project_id:'p',entity_id:id,entity_type:'note' as const,operation:deleted?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:deleted?at:null}
  const plain=createNoteSyncPlaintext(h,parent,note).plaintext,raw=protocol===2?encodeNoteSyncPlaintext(plain):frameContentNote({...f.content,event:plain}),frame=protocol===3&&compressed?compressCanonicalFrame(raw):raw
  const object=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:'note'},frame)
  try{items.push({event:{...h,operation:protocol===2?h.operation:'event',deleted_at:protocol===2?h.deleted_at:null,device_id:f.content.device_id,server_sequence:since+items.length+1},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(object.nonce),ciphertext:encodeBase64Url(object.ciphertext)}})}finally{frame.fill(0);raw.fill(0);object.nonce.fill(0);object.ciphertext.fill(0)}
  return since+items.length
 }
 const children=[await child()]
 if(strategy==='keep_both')children.push(await child('retained-note'))
 if(conflict)children.push(await child())
 const orphan=await child('content-note',crypto.randomUUID(),5)
 const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items,next_cursor:orphan,has_more:true})
 await f.f.sync.commitInboundPage(scope,since,rawPage)
 const applier=f.runtime.atomicApply(),plan=await f.runtime.prepare(scope,f.sequence);await applier.commit(await applier.prepare(plan.token))
 let active=true
 const h=new BrowserResolutionContinuation(f.f.transaction,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 for(const sequence of children)await h.apply(scope,sequence)
 const g=new BrowserResolutionPrefix(f.f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await g.commit(await g.prepareCommit(await g.prepare(scope)))
 return{...f,h,g,since,rawPage,items,children,orphan,transaction:keyedTransaction(f.f.transaction),current:()=>active,close:()=>{active=false;f.close()}}
}
