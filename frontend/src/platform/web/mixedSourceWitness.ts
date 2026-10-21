import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,ResolutionPlannerError,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {sameResolutionValue as same} from './resolutionHistorical'
import {validateMixedSourceInventory as verify,MixedSourceWitnessError} from './mixedSourceValidation'
export {MixedSourceWitnessError} from './mixedSourceValidation'

/** N's isolated read-only diagnostic. Imported only by tests/acceptance harness;
 * not composed into persistence, H/G/K, source writers or production startup. */
export class BrowserMixedSourceWitness {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
  const transaction=this.transaction,profileCurrent=this.profileCurrent
  return Object.freeze({inspect:async(input:BrowserSyncScope)=>{
   const s=snapshotBrowserSyncScope(input),initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(s.accountId),lease=keys.leaseForAccount(s.accountId)
   const current=()=>profileCurrent()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,s,auth)
   const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
   if(!lease||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||lease.authEpoch!==context.authEpoch||context.userId!==s.canonicalUserId)throw new BrowserPersistenceError('account_mismatch')
   check()
   const load=()=>transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort))
   const v=await load();check()
   let counts:Awaited<ReturnType<typeof verify>>
   try{counts=await lease.use(amk=>verify(s,v,amk,current))}
   catch(e){
    if(e instanceof BrowserPersistenceError||e instanceof MixedSourceWitnessError)throw e
    if(e instanceof ResolutionPlannerError&&e.code==='resource_limit'){throw new MixedSourceWitnessError('resource_limit')}
    // Invalid authenticated JSON/decoder errors must not echo source plaintext.
    throw new BrowserPersistenceError('corrupt_record')
   }
   check()
   if(!same(await load(),v))throw new BrowserPersistenceError('stale_source')
   check();return Object.freeze({readOnly:true as const,commitAuthorized:false as const,ackAuthorized:false as const,ready:false as const,...counts})
  }})
 }
}
