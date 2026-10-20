import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import type {VerifiedBrowserDevice} from './deviceRegistration'
import type {BrowserSyncScope,BrowserSyncTransaction} from './syncDurability'
import {BrowserResolutionPrefix} from './resolutionPrefix'

// Audited gaps under the frozen ordinary1/Resolution2 claim, NOT runtime grants.
// Removing a blocker requires its own genuine producer/consumer acceptance.
const blockers=Object.freeze([
 'production_v10_reader_dispatch_incomplete',
 'transport_v10_page_replay_incomplete',
 'orphan_dependency_recovery_not_accepted',
 'tombstone_resurrection_not_accepted',
 'further_resolution_chains_not_accepted',
 'local_author_after_resolution_not_accepted',
 'own_content_self_echo_not_qualified',
 'own_resolution_author_chain_not_accepted',
 'multi_device_reader_orchestration_not_proven',
 'server_note_gate_not_checked',
] as const)
export interface BrowserNoteReadinessDiagnostic {
 readonly readOnly:true;readonly ready:false;readonly declarationAllowed:false;readonly writerAuthorized:false
 readonly localEvidence:'authenticated_bounded_inventory'
 readonly serverGate:'not_checked'
 readonly blockers:readonly string[]
 readonly localPrefix:{current:number;candidate:number;firstBlockingSequence:number|null}
}
/** Dormant negative preflight only. No server declaration/gate HTTP, write method,
 * persistent flag or positive capability token. Not composed into persistence. */
export class BrowserNoteReaderReadiness {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
  // Keep the actual G runtime and its tokens in this lexical closure, never in a
  // TypeScript-private property or a diagnostic DTO available to JS callers.
  const prefix=new BrowserResolutionPrefix(this.transaction,this.profileCurrent).bind(auth,bindings,keys,device)
  return Object.freeze({inspect:async(scope:BrowserSyncScope):Promise<BrowserNoteReadinessDiagnostic>=>{
   // Accepted G owns normal auth/device/AMK/profile checks, complete bounded
   // inventory authentication/currentness and fresh native snapshot comparison.
   // Unsupported/corrupt/stale local evidence rejects, never becomes readiness.
   const certificate=await prefix.prepare(scope),result=await prefix.calculate(certificate)
   return Object.freeze({readOnly:true,ready:false,declarationAllowed:false,writerAuthorized:false,
    localEvidence:'authenticated_bounded_inventory',serverGate:'not_checked',
    blockers:Object.freeze([...blockers,...(result.first_blocking_sequence===null?[]:['local_prefix_blocked'])]),
    localPrefix:Object.freeze({current:result.current_proven_prefix,candidate:result.candidate_proven_prefix,firstBlockingSequence:result.first_blocking_sequence})})
  }})
 }
}
