import type { AccountMasterKey } from '@/crypto'
import { BrowserPersistenceError } from './persistence'
import { immutableWireIdentity,validateBrowserInboxRecord,type BrowserSyncScope } from './syncDurability'
import { validateBrowserProjectBinding } from './projectBindings'
import { validateNoteHistorySet } from './noteHistoryRecords'
import { verifyStoredContentNoteProof } from './contentNoteProof'
import { prepareNotePrerequisite } from './noteTransportPrerequisite'
import type { BrowserPrefixInventory } from './provenPrefixRecords'
export interface VerifiedContentNotePrefix {readonly verifiedContentNotePrefix:unique symbol}
const anchors=(v:BrowserPrefixInventory)=>immutableWireIdentity({rows:v.rows,owners:v.owners,bindings:v.bindings,history:v.history,out:v.out,receipts:v.receipts})
const certificates=new WeakMap<object,{scope:string;anchors:string;current:()=>boolean;sequences:Set<number>}>()
export function contentNoteSequences(token:VerifiedContentNotePrefix|undefined,scope:BrowserSyncScope,v:BrowserPrefixInventory):ReadonlySet<number>{
 if(!token)return new Set();const p=certificates.get(token)
 if(!p||!p.current()||p.scope!==immutableWireIdentity(scope)||p.anchors!==anchors(v))throw new BrowserPersistenceError('stale_authority')
 return new Set(p.sequences)
}
/** Final inbox proof AND authenticated candidate/history AND current Metadata coverage. No HTTP. */
export async function prepareContentNotePrefix(scope:BrowserSyncScope,v:BrowserPrefixInventory,amk:AccountMasterKey,current:()=>boolean):Promise<VerifiedContentNotePrefix>{
 const history=validateNoteHistorySet(scope,v.history),bindings=v.bindings.map(b=>validateBrowserProjectBinding(b,scope)),sequences=new Set<number>()
 for(const raw of v.rows){const row=validateBrowserInboxRecord(raw,scope);if(row.state!=='content_note_proven')continue
  const binding=bindings.find(b=>b.project_id===row.content_note_proof.header.project_id);if(!binding||binding.mode!=='import_remote'||binding.phase!=='captured'||binding.remote_state!=='active'||binding.bootstrap_id!==row.content_note_proof.bootstrap_id)throw new BrowserPersistenceError('corrupt_record')
  await verifyStoredContentNoteProof(scope,amk,row,history)
  await prepareNotePrerequisite(scope,row,binding,amk,current,undefined,v)
  sequences.add(row.server_sequence)
 }
 if(!current())throw new BrowserPersistenceError('closed');const token=Object.freeze({}) as VerifiedContentNotePrefix
 certificates.set(token,{scope:immutableWireIdentity(scope),anchors:anchors(v),current,sequences});return token
}
