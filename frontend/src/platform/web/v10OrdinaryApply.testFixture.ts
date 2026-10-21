import {recoveryFixture} from './v10Recovery.testFixture'
import {scope,amk,at,note} from './bootstrap.testFixture'
import {BrowserV10OrdinaryApply} from './v10OrdinaryApply'
import {BrowserMixedSourceWitness} from './mixedSourceWitness'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Transport} from './v10Transport'
import {createNoteSyncPlaintext} from '@/cloud/encryptedSyncProtocol'
import {encodeNoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import type {BrowserSyncTransaction} from './syncDurability'
/** Sender-only encryption. Every positive applied result uses actual O commits. */
export async function ordinaryV10Fixture(strategy:Parameters<typeof recoveryFixture>[0]='keep_both',protocol:2|3=3,compressed=false,stage=false){
 const f=await recoveryFixture(strategy,protocol,compressed,stage,true,true);await f.runtime.run(scope,{maxEvents:32})
 let active=true
 const create=(tx:BrowserSyncTransaction=f.transaction)=>new BrowserV10OrdinaryApply(tx,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const witness=new BrowserMixedSourceWitness(f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const h=new BrowserResolutionContinuation(f.transaction,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),g=new BrowserResolutionPrefix(f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),j=new BrowserV10Transport(f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const receive=async(id='independent',parent:string|null=null,revision=1,deleted=false,options:{protocol?:2|3;compressed?:boolean;project?:string;device?:string;stage?:string|null;format?:'html'|'plain';dependencies?:string[]}={})=>{
  const version=options.protocol??protocol,project=options.project??'p',device=options.device??'44444444-4444-4444-8444-444444444444',sequence=(f.f.db.cursors[0] as any).pull_cursor+1
  const stageId=options.stage===undefined?stage?'s':null:options.stage,format=options.format??'html'
  const header={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note' as const,operation:deleted?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:deleted?at:null}
  const {revision:_local,...n}=note(id)
  const plaintext=createNoteSyncPlaintext(header,parent,deleted?{id,project_id:project,stage_id:stageId,source_type:'project',source_map_id:null,source_node_id:null,content_format:format,deleted_at:at}:{...n,project_id:project,stage_id:stageId,content_format:format,metadata:{},content:'AUTHENTIC_ORDINARY_V10'.repeat(40)}).plaintext
  const b=f.f.db.projectBindings.find((r:any)=>r.project_id===project) as any,raw=version===2?encodeNoteSyncPlaintext(plaintext):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:device,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:options.dependencies??(stage?[...new Set(f.f.db.ownerHeads!.filter((r:any)=>r.owner_kind==='stage').map((r:any)=>r.tip_event_ids[0]))] as string[]:[])},event:plaintext})
  const frame=version===3&&(options.compressed??compressed)?compressCanonicalFrame(raw):raw,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame)
  const event={...header,device_id:device,server_sequence:sequence,operation:version===2?header.operation:'event',deleted_at:version===2?header.deleted_at:null},rawPage=JSON.stringify({protocol_version:version,encrypted_sync_version:version,items:[{event,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false})
  try{await f.f.sync.commitInboundPage(scope,sequence-1,rawPage)}finally{frame.fill(0);raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  return{sequence,event_id:header.event_id,plaintext,rawPage,since:sequence-1}
 }
 return{...f,create,owner:create(),witness,h,g,j,receive,revoke:()=>{active=false}}
}
