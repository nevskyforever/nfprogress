import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {resolutionSame as same} from './resolutionRecords'
import {HistoricalPrefixQualificationError,inspectTerminalMetadataHistoricalPrefix} from './mixedSourceValidation'

/** Dormant .15 reader only. No prepare/calculate/commit/capability surface. */
export class BrowserHistoricalPrefixQualification {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
  const transaction=this.transaction,profileCurrent=this.profileCurrent
  return Object.freeze({inspect:async(input:BrowserSyncScope)=>{
   const s=snapshotBrowserSyncScope(input),initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(s.accountId),lease=keys.leaseForAccount(s.accountId)
   const current=()=>profileCurrent()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,s,auth)
   const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
   if(!lease||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||lease.authEpoch!==context.authEpoch||context.userId!==s.canonicalUserId)throw new BrowserPersistenceError('account_mismatch')
   check()
   const load=()=>transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort)),v=await load()
   let result:Awaited<ReturnType<typeof inspectTerminalMetadataHistoricalPrefix>>|undefined,error:HistoricalPrefixQualificationError|undefined
   try{result=await lease.use(amk=>inspectTerminalMetadataHistoricalPrefix(s,v,amk,current))}
   catch(e){check();error=e instanceof HistoricalPrefixQualificationError?e:new HistoricalPrefixQualificationError('invalid_history')}
   check();if(!same(await load(),v))throw new BrowserPersistenceError('stale_source');check()
   if(error)throw error
   if(!result)throw new HistoricalPrefixQualificationError('invalid_history')
   return result
  }})
 }
}
