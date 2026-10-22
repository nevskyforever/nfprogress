import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {readFutureInboxRecord,resolutionSame as same} from './resolutionRecords'
import {inspectTerminalMetadataSourceHistory} from './mixedSourceValidation'

/** Dormant .14 read-only reader. Actual durable state is always reloaded. Only
 * diagnostics escape; no plaintext, source/prefix grant or live certificate. */
export class BrowserHistoricalContentAuthentication {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
  const transaction=this.transaction,profileCurrent=this.profileCurrent
  return Object.freeze({inspect:async(input:BrowserSyncScope,eventId:string)=>{
   const s=snapshotBrowserSyncScope(input),initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(s.accountId),lease=keys.leaseForAccount(s.accountId)
   const current=()=>profileCurrent()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,s,auth)
   const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
   if(!lease||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||lease.authEpoch!==context.authEpoch||context.userId!==s.canonicalUserId)throw new BrowserPersistenceError('account_mismatch')
   check()
   const load=()=>transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort)),v=await load()
   let reason:'invalid_evidence'|'not_applied'|'unsupported_target'|null=null,counts:Awaited<ReturnType<typeof inspectTerminalMetadataSourceHistory>>|undefined
   try{
    counts=await lease.use(amk=>inspectTerminalMetadataSourceHistory(s,v,amk,current))
    const target=v.rows.map(r=>readFutureInboxRecord(r,s)).find(r=>r.event_id===eventId)
    if(!target||target.state==='received')reason='not_applied'
    else if(!['content_note_proven','note_resolution_proven'].includes(target.state))reason='unsupported_target'
   }catch{check();reason='invalid_evidence';counts=undefined}
   check();if(!same(await load(),v))throw new BrowserPersistenceError('stale_source');check()
   return Object.freeze({readOnly:true as const,historicalAuthenticated:reason===null,fullHistoryAuthenticated:reason===null,currentSourceVerified:reason===null,reason,sourceAuthorized:false as const,firstApplyAllowed:false as const,commitAuthorized:false as const,ackAuthorized:false as const,ready:false as const,...counts})
  }})
 }
}
