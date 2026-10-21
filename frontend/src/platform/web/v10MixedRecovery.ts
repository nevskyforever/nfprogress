import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {canonicalizeSyncTimestamp} from '@/cloud/syncTimestamp'
import type {ContentNoteEvent} from '@/cloud/contentNoteCodec'
import {decodeBase64Url} from '@/api/base64url'
import {BrowserPersistenceError} from './persistence'
import {BrowserLocalAuthority} from './localAuthority'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {readFutureInboxRecord,resolutionSame as same} from './resolutionRecords'
import {authenticateContinuationHistory} from './resolutionHistorical'
import {MixedSourceWitnessError} from './mixedSourceValidation'
import {BrowserV10Transport} from './v10Transport'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {BrowserV10OrdinaryApply} from './v10OrdinaryApply'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {openNoteTransport} from './noteTransport'
import {openBrowserCanonicalObject} from './canonicalReaders'
import type {RecoveryBlocker,V10RecoveryOptions,V10RecoveryResult} from './v10Recovery'

export interface MixedV10RecoveryResult extends Omit<V10RecoveryResult,'blocker'> {
 blocker:(RecoveryBlocker&{reason:string})|null
}
function fail(code:'closed'|'corrupt_record'|'stale_source'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
/** Internal factory for K's explicit dormant binding. All component handles,
 * pass ownership, certificates and source plans remain in this lexical closure. */
export function bindMixedV10Recovery(tx:BrowserSyncTransaction,local:BrowserLocalAuthority,current:()=>boolean,auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
 const transport=new BrowserV10Transport(tx,current).bind(auth,bindings,keys,device)
 const h=new BrowserResolutionContinuation(tx,local,current).bind(auth,bindings,keys,device)
 const o=new BrowserV10OrdinaryApply(tx,local,current).bind(auth,bindings,keys,device)
 const g=new BrowserResolutionPrefix(tx,current).bindMixedSources(auth,bindings,keys,device)
 let busy=false
 return Object.freeze({run:async(input:BrowserSyncScope,options:V10RecoveryOptions={}):Promise<MixedV10RecoveryResult>=>{
  if(busy)fail('closed')
  const s=snapshotBrowserSyncScope(input),max=options.maxEvents??8,replay=options.replay?{...options.replay}:undefined
  if(!Number.isSafeInteger(max)||max<1||max>32)fail()
  busy=true
  try{
   const initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(s.accountId),lease=keys.leaseForAccount(s.accountId)
   const live=()=>current()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,s,auth)
   const check=()=>{if(!live())fail('closed')}
   if(!lease||lease.authEpoch!==context.authEpoch||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||context.userId!==s.canonicalUserId)fail('closed')
   check()
   const step=async<T>(promise:Promise<T>)=>{const value=await promise;check();return value}
   const load=()=>step(tx<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,live,result,abort)))
   const result:MixedV10RecoveryResult={ready:false,declarationAllowed:false,ackAuthorized:false,applied:[],blocker:null,more:false,replayed_events:0,prefix:null,readiness:null}
   const block=(sequence:number,kind:RecoveryBlocker['kind'],reason:string,retryable=false)=>{result.blocker={sequence,kind,reason,retryable}}
   // These are explicit unsupported source cohorts, never crypto/CAS/lifecycle
   // errors disguised as a retry or a historical fallback.
   const witnessBarrier=(error:unknown,sequence:number)=>{
    if(!(error instanceof MixedSourceWitnessError))return false
    if(error.code==='missing_sequence')block(sequence,'missing_sequence','incomplete_mixed_inventory')
    else if(error.code==='unsupported_generation')block(sequence,'unsupported_generation','additional_resolution')
    else if(error.code==='unsupported_pending_family')block(sequence,'unsupported_route','unsupported_pending_family')
    else if(error.code==='unresolved_fork')block(sequence,'unresolved_fork','unsupported_open_group')
    else if(['missing_baseline','unsupported_local_source','no_resolution'].includes(error.code))block(sequence,'unsupported_route',`mixed_source_${error.code}`)
    else return false // revision/source/causal corruption must reject the pass.
    return true
   }
   if(replay)result.replayed_events=(await step(transport.replayInboundPage(s,replay.since,replay.rawPage))).replayed_events
   let noCertificate=false
   for(;;){
    // J uses real IDB keys/index ownership and authenticates retained evidence.
    // Always begin at zero, never accept an alternative offset or skip a gap.
    const pending=await step(transport.listReceived(s,200)),v=await load(),rows=v.rows.map(r=>readFutureInboxRecord(r,s)).sort((a,b)=>a.server_sequence-b.server_sequence),row=pending[0]
    if(row&&!same(rows.find(r=>r.server_sequence===row.server_sequence),row))fail('stale_source')
    const missing=rows.findIndex((r,i)=>r.server_sequence!==i+1),gap=missing>=0?missing+1:rows.length<v.cursor.pull_cursor?rows.length+1:null
    if(gap!==null&&gap<=v.cursor.proven_prefix)fail()
    if(gap!==null){block(gap,'missing_sequence','incomplete_account_inventory');noCertificate=true;break}
    const history=await step(lease.use(amk=>authenticateContinuationHistory(s,v,amk,live)))
    if(history.resolutions.size!==1){
     block(row?.server_sequence??1,'unsupported_generation',history.resolutions.size?'additional_resolution':'accepted_F_required');noCertificate=true;break
    }
    const root=[...history.resolutions.values()][0]!
    // Q authenticates the full current source. Its calculation is not permission
    // to apply, acknowledge or declare readiness; each actual owner prepares anew.
    let certificate
    try{certificate=await step(g.prepare(s))}catch(error){
     check();if(!witnessBarrier(error,row?.server_sequence??v.cursor.proven_prefix+1))throw error
     if(row&&JSON.parse(row.wire_item).event.device_id===s.deviceId)block(row.server_sequence,'unsupported_route','own_authorship_or_self_echo')
     noCertificate=true;break
    }
    const prefix=await step(g.calculate(certificate)),barrier=prefix.first_blocking_sequence===null?undefined:rows.find(r=>r.server_sequence===prefix.first_blocking_sequence)
    if(barrier&&barrier.state!=='received'){
     block(barrier.server_sequence,['note_conflict_preserved','content_note_conflict_preserved'].includes(barrier.state)?'unresolved_fork':'unqualified_family','persisted_unqualified_evidence');break
    }
    if(!row)break
    if(result.applied.length===max){block(row.server_sequence,'budget_exhausted','manual_pass_limit',true);break}
    const e=JSON.parse(row.wire_item).event
    if(e.device_id===s.deviceId){block(row.server_sequence,'unsupported_route','own_authorship_or_self_echo');break}
    if(e.entity_type!=='note'){
     block(row.server_sequence,'unsupported_route',['project_metadata','stage','stage_order'].includes(e.entity_type)?'post_F_structural_route':'unsupported_family');break
    }
    const value=await step(lease.use(async amk=>{
     if(e.operation!=='event'){
      if(e.operation==='resolution')return null
      return(await openNoteTransport(s,amk,row.protocol_version,row.wire_item,'legacy')).plaintext
     }
     if(row.protocol_version!==3)fail()
     const wire=JSON.parse(row.wire_item),nonce=decodeBase64Url(wire.object.nonce),ciphertext=decodeBase64Url(wire.object.ciphertext)
     try{
      const c=await openBrowserCanonicalObject(amk,{accountId:s.canonicalUserId,projectId:e.project_id,entityId:e.entity_id,entityType:'note',eventId:e.event_id},{...wire.object,nonce,ciphertext}) as ContentNoteEvent
      if(c.device_id!==e.device_id||c.event.header.revision!==e.revision||canonicalizeSyncTimestamp(c.event.header.updated_at)!==canonicalizeSyncTimestamp(e.updated_at))fail()
      return c.event.version===2?null:c.event
     }finally{nonce.fill(0);ciphertext.fill(0)}
    }))
    if(!value){block(row.server_sequence,'unsupported_generation','additional_resolution');break}
    if(e.project_id!==root.record.project_id){block(row.server_sequence,'unsupported_route','unrelated_project_writer');break}
    const role=[root.record.note_id,root.record.retained_note_id].includes(value.header.entity_id)
    // Project/root identity determines the owner, never a guessed Head1/Head2 or
    // an unsuccessful H attempt followed by O. Owners enforce their own ancestry.
    const route=role?'continuation':row.protocol_version===2?'legacy':'content'
    try{
     const commit=async<T,R>(prepare:Promise<T>,apply:(token:T)=>Promise<R>)=>{
      const plan=await step(prepare);if(!same(await load(),v))fail('stale_source');return step(apply(plan))
     }
     const outcome=role?await commit(h.prepare(s,row.server_sequence),t=>h.commit(t)):await commit(o.prepare(s,row.server_sequence),t=>o.commit(t)),status=outcome==='conflict_preserved'?'conflict_preserved':'applied'
     result.applied.push({sequence:row.server_sequence,route,status})
     if(status==='conflict_preserved'){block(row.server_sequence,'unresolved_fork','H_preserved_without_projection');break}
    }catch(error){
     check()
     if(witnessBarrier(error,row.server_sequence))break
     if(error instanceof BrowserPersistenceError&&['note_orphan','missing_history','ineligible_lineage','stale_authority'].includes(error.code)){block(row.server_sequence,'dependency_unavailable',error.code,true);break}
     if(error instanceof BrowserPersistenceError&&['unsupported_local_source','note_conflict_unproven','local_incompatible'].includes(error.code)){block(row.server_sequence,'unsupported_route',error.code);break}
     throw error
    }
    // No cached source/history/role survives an event commit. Reload on every
    // iteration, including after budget exhaustion, before any further decision.
   }
   if(!noCertificate){
    const token=await step(g.prepare(s));result.prefix=await step(g.calculate(token))
    if(result.prefix.candidate_proven_prefix>result.prefix.current_proven_prefix)await step(g.commit(await step(g.prepareCommit(token))))
    if(!result.blocker&&result.prefix.first_blocking_sequence!==null)block(result.prefix.first_blocking_sequence,'unqualified_family','missing_applied_family_evidence')
   }
   // I remains an unchanged negative-only default-G preflight. Do not synthesize
   // its diagnostic or borrow its failed historical admission for mixed history.
   result.more=(await step(transport.listReceived(s,1))).length>0
   if(replay)await step(transport.replayInboundPage(s,replay.since,replay.rawPage))
   return result
  }finally{busy=false}
 }})
}
