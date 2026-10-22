import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,validateBrowserInboundPage,validateBrowserSyncCursor,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {readFutureInboxRecord,resolutionSame as same} from './resolutionRecords'
import {authenticatePrivateMetadataPrefixInventory} from './mixedSourceValidation'
import type {ResolutionPrefixResult} from './resolutionPrefix'

export interface PrivateMetadataPrefixCertificate {readonly privateMetadataPrefix:unique symbol}
export interface PrivateMetadataPrefixCommit {readonly privateMetadataPrefixCommit:unique symbol}
export class PrivateMetadataPrefixError extends Error {
 readonly name='PrivateMetadataPrefixError'
 constructor(readonly code:'invalid_history'|'invalid_token'|'post_commit_verification_failed',readonly commitMayHaveOccurred=false){super(`private_metadata_prefix_${code}`)}
}
type Evidence=Awaited<ReturnType<typeof authenticatePrivateMetadataPrefixInventory>>
interface Certificate {scope:BrowserSyncScope;inventory:ResolutionInventorySnapshot;evidence:Evidence;current:()=>boolean}
function fail(code:'closed'|'stale_source'|'corrupt_record'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
function calculate(p:Certificate):ResolutionPrefixResult {
 if(!p.current())fail('closed')
 const v=p.inventory,cursor=validateBrowserSyncCursor(v.checkpoints[0],p.scope)
 if(v.checkpoints.length!==1||!same(cursor,v.cursor))fail()
 const rows=v.rows.map(r=>readFutureInboxRecord(r,p.scope)).sort((a,b)=>a.server_sequence-b.server_sequence)
 const result:ResolutionPrefixResult={readOnly:true,ackAuthorized:false,current_proven_prefix:cursor.proven_prefix,candidate_proven_prefix:cursor.proven_prefix,pull_cursor:cursor.pull_cursor,first_blocking_sequence:null,blocker:null,counts:{legacy:0,content:0,resolution:0,metadata:0,stage:0,stage_order:0}}
 for(let sequence=1;sequence<=cursor.pull_cursor;sequence++){
  const row=rows[sequence-1],family=p.evidence.qualified.get(sequence)
  if(!row||row.server_sequence!==sequence||!family){
   if(sequence<=cursor.proven_prefix)fail()
   result.first_blocking_sequence=sequence;result.blocker=row?.server_sequence===sequence?'unproven_family':'missing_sequence';break
  }
  if(row.state==='received')fail()
  result.counts[family]++;result.candidate_proven_prefix=sequence
 }
 return result
}

/** Internal .18 owner only. Fresh original-wire/source authentication mints every
 * certificate here; .15 diagnostics and existing G/Q tokens are never inputs. */
export function bindPrivateMetadataPrefix(transaction:BrowserSyncTransaction,profileCurrent:()=>boolean,auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
 const certificates=new WeakMap<object,Certificate>(),commits=new WeakMap<object,{certificate:Certificate;result:ResolutionPrefixResult}>()
 const guard=async(input:BrowserSyncScope)=>{
  const scope=snapshotBrowserSyncScope(input),initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(scope.accountId),lease=keys.leaseForAccount(scope.accountId)
  const current=()=>profileCurrent()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,scope,auth)
  if(!lease||lease.localAccountId!==scope.accountId||lease.canonicalUserId!==scope.canonicalUserId||lease.authEpoch!==context.authEpoch||context.userId!==scope.canonicalUserId||!current())fail('closed')
  return{scope,lease,current}
 }
 const load=(s:BrowserSyncScope,current:()=>boolean)=>transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort))
 const certificateFor=(token:PrivateMetadataPrefixCertificate)=>{const p=token&&certificates.get(token);if(!p)throw new PrivateMetadataPrefixError('invalid_token');if(!p.current())fail('closed');return p}
 const authenticate=async(s:BrowserSyncScope,v:ResolutionInventorySnapshot,lease:NonNullable<ReturnType<RuntimeKeyContext['leaseForAccount']>>,current:()=>boolean)=>{
  try{return await lease.use(amk=>authenticatePrivateMetadataPrefixInventory(s,v,amk,current))}
  catch(error){if(!current())fail('closed');if(error instanceof BrowserPersistenceError)throw error;throw new PrivateMetadataPrefixError('invalid_history')}
 }
 const prepare=async(input:BrowserSyncScope):Promise<PrivateMetadataPrefixCertificate>=>{
  const {scope,lease,current}=await guard(input),inventory=await load(scope,current),evidence=await authenticate(scope,inventory,lease,current)
  const p={scope,inventory,evidence,current};calculate(p)
  if(!current()||!same(await load(scope,current),inventory))fail('stale_source')
  const token=Object.freeze({}) as PrivateMetadataPrefixCertificate;certificates.set(token,p);return token
 }
 const fresh=async(token:PrivateMetadataPrefixCertificate)=>{const p=certificateFor(token);if(!same(await load(p.scope,p.current),p.inventory))fail('stale_source');if(!p.current())fail('closed');return p}
 return Object.freeze({
  prepare,
  calculate:async(token:PrivateMetadataPrefixCertificate)=>calculate(await fresh(token)),
  route:async(token:PrivateMetadataPrefixCertificate)=>{
   const p=await fresh(token),first=p.inventory.rows.map(r=>readFutureInboxRecord(r,p.scope)).filter(r=>r.state==='received').sort((a,b)=>a.server_sequence-b.server_sequence)[0]
   return Object.freeze({root:Object.freeze({...p.evidence.root}),metadataDeleted:p.evidence.metadataDeleted,firstPending:first?Object.freeze({sequence:first.server_sequence,event_id:first.event_id,protocol_version:first.protocol_version,event:Object.freeze({...JSON.parse(first.wire_item).event})}):null})
  },
  prepareCommit:async(token:PrivateMetadataPrefixCertificate):Promise<PrivateMetadataPrefixCommit>=>{
   const certificate=certificateFor(token)
   certificates.delete(token)
   if(!same(await load(certificate.scope,certificate.current),certificate.inventory))fail('stale_source')
   const result=calculate(certificate)
   const commit=Object.freeze({}) as PrivateMetadataPrefixCommit;commits.set(commit,{certificate,result});return commit
  },
  commit:async(token:PrivateMetadataPrefixCommit)=>{
   const plan=token&&commits.get(token);if(!plan)throw new PrivateMetadataPrefixError('invalid_token')
   commits.delete(token)
   const p=plan.certificate;if(!p.current())fail('closed')
   let activeAbort:((e:unknown)=>void)|undefined,committed=false
   const stop=()=>activeAbort?.(new BrowserPersistenceError('closed')),unAuth=auth.onInvalidated(stop),unKey=keys.onInvalidated(stop)
   const target=plan.result.candidate_proven_prefix,expected={...p.inventory,cursor:{...p.inventory.cursor,proven_prefix:target},checkpoints:p.inventory.checkpoints.map(raw=>({...raw as object,proven_prefix:target}))}
   try{
    const status=await transaction<'advanced'|'no_progress'>(p.scope,resolutionInventoryStores,'readwrite',(tx,result,abort)=>{
     activeAbort=abort;tx.addEventListener?.('complete',()=>{committed=true},{once:true})
     scheduleResolutionInventory(tx,p.scope,p.current,v=>{try{
      if(!p.current())fail('closed')
      if(!same(v,p.inventory)||!same(calculate(p),plan.result))fail('stale_source')
      if(target===v.cursor.proven_prefix){result('no_progress');return}
      if(target<v.cursor.proven_prefix||target>v.cursor.pull_cursor||v.cursor.ack_cursor>target)fail()
      const request=tx.objectStore('cursors').put({...v.checkpoints[0] as object,proven_prefix:target})
      request.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))}
      result('advanced')
     }catch(error){abort(error)}},abort)
    })
    committed=true;activeAbort=undefined
    const {scope,lease,current}=await guard(p.scope),durable=await load(scope,current)
    if(!p.current()||!same(durable,expected))fail('stale_source')
    const evidence=await authenticate(scope,durable,lease,current)
    if(calculate({scope,inventory:durable,evidence,current}).candidate_proven_prefix!==target||!p.current()||!same(await load(scope,current),durable))fail('stale_source')
    return status
   }catch(error){if(committed)throw new PrivateMetadataPrefixError('post_commit_verification_failed',true);throw error}
   finally{activeAbort=undefined;unAuth();unKey()}
  },
  replay:async(input:BrowserSyncScope,since:number,rawPage:string)=>{
   if(!Number.isSafeInteger(since)||since<0)fail()
   const token=await prepare(input),p=certificateFor(token),page=validateBrowserInboundPage(rawPage,since,p.scope)
   try{
    if(p.inventory.cursor.pull_cursor!==page.next_cursor||page.next_cursor<=since||!page.items.length)fail('stale_source')
    const output=await transaction<{committed_cursor:number;new_events:0;replayed_events:number;has_more:boolean}>(p.scope,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,p.scope,p.current,v=>{try{
     if(!same(v,p.inventory))fail('stale_source')
     const store=tx.objectStore('inbox'),count=store.count(IDBKeyRange.bound([p.scope.accountId,since],[p.scope.accountId,page.next_cursor],true,false))
     count.onsuccess=()=>{try{
      if(!p.current())fail('closed');if(count.result!==page.items.length)fail()
      const next=(index:number)=>{
       if(index===page.items.length){result({committed_cursor:page.next_cursor,new_events:0,replayed_events:page.items.length,has_more:page.has_more});return}
       const item=page.items[index]!,bySequence=store.get([p.scope.accountId,item.event.server_sequence!]),byEvent=store.index('event').get([p.scope.accountId,item.event.event_id]);let done=0
       const finish=()=>{if(++done!==2)return;try{
        if(!p.current())fail('closed')
        const row=readFutureInboxRecord(bySequence.result,p.scope)
        if(row.server_sequence!==item.event.server_sequence||row.event_id!==item.event.event_id||row.protocol_version!==page.protocol_version||!same(row,readFutureInboxRecord(byEvent.result,p.scope))||!same(JSON.parse(row.wire_item),item))fail()
        next(index+1)
       }catch(error){abort(error)}}
       bySequence.onsuccess=finish;byEvent.onsuccess=finish
      };next(0)
     }catch(error){abort(error)}}
    }catch(error){abort(error)}},abort))
    if(!p.current())fail('closed');return output
   }finally{certificates.delete(token)}
  },
 })
}
