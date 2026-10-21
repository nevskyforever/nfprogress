import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {snapshotBrowserSyncScope,validateBrowserSyncCursor,type BrowserSyncScope,type BrowserSyncTransaction} from './syncDurability'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {readFutureInboxRecord} from './resolutionRecords'
import {authenticateContinuationHistory,verifyContinuationSources,sameResolutionValue as same} from './resolutionHistorical'
import {validateMixedPrefixInventory,MixedSourceWitnessError} from './mixedSourceValidation'
import {prepareMetadataPrefix,verifiedMetadataSequences,type VerifiedMetadataPrefix} from './metadataPrefixProof'
import {prepareStagePrefix,stageSequences,type VerifiedStagePrefix} from './stageApply'
import {prepareStageOrderPrefix,stageOrderSequences,type VerifiedStageOrderPrefix} from './stageOrderApply'
import {validateBrowserOwnerHead} from './stageRecords'
import type {BrowserPrefixInventory} from './provenPrefixRecords'

export interface VerifiedResolutionPrefix {readonly verifiedResolutionPrefix:unique symbol}
export interface ResolutionPrefixCommit {readonly resolutionPrefixCommit:unique symbol}
type Family='legacy'|'content'|'resolution'|'metadata'|'stage'|'stage_order'
export interface ResolutionPrefixResult {
 readonly readOnly:true;readonly ackAuthorized:false
 current_proven_prefix:number;candidate_proven_prefix:number;pull_cursor:number
 first_blocking_sequence:number|null;blocker:'missing_sequence'|'unproven_family'|null
 counts:Record<Family,number>
}
interface Certificate {
 owner:BrowserResolutionPrefixRuntime;scope:BrowserSyncScope;inventory:ResolutionInventorySnapshot;current:()=>boolean
 // Only the authenticated H pass below can mint these family grants. No plaintext
 // or public diagnostic object crosses this boundary.
 notes:Map<number,'legacy'|'content'>;resolutions:Set<number>
 dependencies:BrowserPrefixInventory;metadata:VerifiedMetadataPrefix;stage:VerifiedStagePrefix;order:VerifiedStageOrderPrefix
}
interface CommitPlan {owner:BrowserResolutionPrefixRuntime;certificate:Certificate;result:ResolutionPrefixResult}
const certificates=new WeakMap<object,Certificate>(),commits=new WeakMap<object,CommitPlan>()
function fail(code:'closed'|'corrupt_record'|'stale_source'|'unsupported_local_source'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
// Module-private, rather than a TypeScript-private instance method which would
// still expose the mutable capability state to JavaScript callers.
function certificateFor(owner:BrowserResolutionPrefixRuntime,token:VerifiedResolutionPrefix):Certificate {
 const p=certificates.get(token);if(!p||p.owner!==owner)fail();if(!p.current())fail('closed');return p
}

/** Full v10 dispatch, never the old v9 calculator. All stored sequences, including
 * the already-proven interval, must qualify under their own authenticated family. */
function calculate(p:Certificate):ResolutionPrefixResult {
 if(!p.current())fail('closed')
 const v=p.inventory,cursor=validateBrowserSyncCursor(v.checkpoints[0],p.scope)
 if(!same(cursor,v.cursor))fail()
 const qualified=new Map<number,Family>()
 for(const n of verifiedMetadataSequences(p.metadata,p.scope,p.dependencies))qualified.set(n,'metadata')
 for(const n of stageSequences(p.stage,p.scope,p.dependencies))qualified.set(n,'stage')
 for(const n of stageOrderSequences(p.order,p.scope,p.dependencies))qualified.set(n,'stage_order')
 for(const [n,family] of p.notes)qualified.set(n,family)
 for(const n of p.resolutions)qualified.set(n,'resolution')
 const rows=new Map<number,ReturnType<typeof readFutureInboxRecord>>()
 for(const raw of v.rows){const row=readFutureInboxRecord(raw,p.scope);if(rows.has(row.server_sequence)||row.server_sequence>cursor.pull_cursor)fail();rows.set(row.server_sequence,row)}
 const result:ResolutionPrefixResult={readOnly:true,ackAuthorized:false,current_proven_prefix:cursor.proven_prefix,candidate_proven_prefix:cursor.proven_prefix,pull_cursor:cursor.pull_cursor,first_blocking_sequence:null,blocker:null,counts:{legacy:0,content:0,resolution:0,metadata:0,stage:0,stage_order:0}}
 // A gap terminates immediately, so even a maliciously large pull cursor cannot
 // cause a scan longer than the bounded inventory plus one.
 for(let sequence=1;sequence<=cursor.pull_cursor;sequence++){
  const row=rows.get(sequence),family=qualified.get(sequence)
  if(!row||!family){
   if(sequence<=cursor.proven_prefix)fail()
   result.first_blocking_sequence=sequence;result.blocker=row?'unproven_family':'missing_sequence';break
  }
  result.counts[family]++;result.candidate_proven_prefix=sequence
 }
 return result
}

/** Explicit dormant G surface. No production composition, ACK or HTTP methods. */
export class BrowserResolutionPrefix {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){return new BrowserResolutionPrefixRuntime(this.transaction,this.profileCurrent,auth,bindings,keys,device)}
 /** Explicit isolated Q entry. K keeps bind() and cannot inherit this admission. */
 bindMixedSources(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){return new BrowserResolutionPrefixRuntime(this.transaction,this.profileCurrent,auth,bindings,keys,device,true)}
}
export class BrowserResolutionPrefixRuntime {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext,private readonly device:VerifiedBrowserDevice,private readonly mixedSources=false){}
 private async guard(s:BrowserSyncScope){
  const initial=this.auth.requireContext(),{context}=await this.bindings.ensureForCurrentUser(s.accountId),lease=this.keys.leaseForAccount(s.accountId)
  const current=()=>this.profileCurrent()&&this.auth.isCurrent(initial)&&this.auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(this.device,s,this.auth)
  if(!lease||lease.authEpoch!==context.authEpoch||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||context.userId!==s.canonicalUserId||!current())fail('closed')
  return{lease,current}
 }
 private load(s:BrowserSyncScope,current:()=>boolean){return this.transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort))}

 async prepare(input:BrowserSyncScope):Promise<VerifiedResolutionPrefix>{
  const s=snapshotBrowserSyncScope(input),{lease,current}=await this.guard(s),v=await this.load(s,current)
  const p=await lease.use(async amk=>{
   // Reuse accepted H crypto/closure/DAG authentication. Its
   // public readOnly diagnostics are deliberately NOT accepted as a capability.
   const h=await authenticateContinuationHistory(s,v,amk,current)
   // Select from authenticated evidence, never by catching a verification error.
   // F/H-only histories keep their accepted ordering and missing-sequence rules.
   const mixed=this.mixedSources&&[...h.resolutions.values()].some(root=>[...h.dag.events.values()].some(c=>
    c.record_kind==='candidate'&&c.project_id===root.record.project_id&&![root.record.note_id,root.record.retained_note_id].includes(c.note_id)&&
    ((h.rows.find(r=>r.event_id===c.event_id)?.server_sequence??0)>root.record.server_sequence||(c.projection?.source_revision??0)>root.project.source_revision)))
   if(mixed){
    try{await validateMixedPrefixInventory(s,v,amk,current)}catch(e){
     if(e instanceof BrowserPersistenceError||e instanceof MixedSourceWitnessError)throw e
     fail() // No plaintext decoder errors and no historical fallback.
    }
   }else await verifyContinuationSources(s,v,h,amk,current)
   if(!h.resolutions.size)fail('unsupported_local_source')
   if(v.intents.some(i=>(i as {record_version:number}).record_version===2))fail('unsupported_local_source')
   // H proves the current original/retained chains. G also pins other members
   // of those projects to an already authenticated ordinary projection or
   // pending Legacy snapshot; a valid AEAD envelope alone cannot explain drift.
   const projects=new Set([...h.resolutions.values()].map(r=>r.record.project_id))
   for(const raw of v.localNotes){
    const note=raw as {project_id:string;note_id:string}
    if(!projects.has(note.project_id))continue
    const output=[...h.resolutions.values()].some(r=>r.record.project_id===note.project_id&&(r.record.note_id===note.note_id||r.record.retained_note_id===note.note_id))
    if(output)continue // Authenticated through H's complete current-source chain.
    const head=h.dag.history.find(r=>r.record_kind==='head'&&r.project_id===note.project_id&&r.note_id===note.note_id)
    const candidate=head?.record_kind==='head'?h.dag.events.get(head.linear_head_event_id):undefined
    const pending=v.intents.some(i=>{const intent=i as {record_version:number;project_id:string;note_id:string;snapshot:unknown};return intent.record_version===1&&intent.project_id===note.project_id&&intent.note_id===note.note_id&&same(intent.snapshot,raw)})
    if(!pending&&!(candidate?.record_kind==='candidate'&&same(candidate.projection,raw)))fail('unsupported_local_source')
   }
   v.owners.forEach(owner=>validateBrowserOwnerHead(owner,s))
   // Family-only crypto adapters, as in H. The COMPLETE future inventory was
   // authenticated above and stays pinned below. No old Note/prefix calculator
   // receives a filtered Resolution history, fabricated Head1 or v9 cast.
   const dependencies:BrowserPrefixInventory={...v,rows:h.rows.filter(row=>['project_metadata','stage','stage_order'].includes(JSON.parse(row.wire_item).event.entity_type))}
   const metadata=await prepareMetadataPrefix(s,dependencies,amk,current,true)
   const stage=await prepareStagePrefix(s,dependencies,amk,current,metadata,true)
   const order=await prepareStageOrderPrefix(s,dependencies,amk,current,metadata,true)
   const notes=new Map<number,'legacy'|'content'>(),resolutions=new Set<number>()
   for(const row of h.rows){
    if(row.state==='note_resolution_proven'){
     const root=h.resolutions.get(row.event_id);if(!root||root.record.server_sequence!==row.server_sequence)fail()
     resolutions.add(row.server_sequence);continue // keep_both is ONE sequence.
    }
    if(!['note_proven','note_conflict_preserved','content_note_proven','content_note_conflict_preserved'].includes(row.state))continue
    const candidate=h.dag.events.get(row.event_id)
    if(!candidate||candidate.record_kind!=='candidate'||!h.opened.has(row.event_id))fail()
    if(row.state==='note_conflict_preserved'||row.state==='content_note_conflict_preserved'){
     const proof=row.state==='note_conflict_preserved'?row.note_conflict_proof:row.content_note_conflict_proof
     const group=h.groups.find(g=>g.group.project_id===candidate.project_id&&g.group.note_id===candidate.note_id&&g.group.group_id===proof.group_id)
     if(!group)fail()
     // A new independent unresolved fork is authentic retained history, but
     // does not authorize advancement through its incoming branch.
     if(group.effective!=='resolved')continue
    }
    if(candidate.record_version===3)continue // P2/inbox9 never gains qualification.
    notes.set(row.server_sequence,candidate.record_version===2?'content':'legacy')
   }
   if(!current())fail('closed')
   return{owner:this,scope:s,inventory:v,current,notes,resolutions,dependencies,metadata,stage,order}
  })
  calculate(p) // Corruption inside the existing prefix fails closed at minting.
  if(!current()||!same(await this.load(s,current),v))fail('stale_source')
  const token=Object.freeze({}) as VerifiedResolutionPrefix;certificates.set(token,p);return token
 }
 async calculate(token:VerifiedResolutionPrefix):Promise<ResolutionPrefixResult>{
  const p=certificateFor(this,token)
  if(!same(await this.load(p.scope,p.current),p.inventory))fail('stale_source')
  return calculate(p)
 }
 /** Distinct private commit authorization, prepared only from a fresh genuine
  * certificate/calculation. A caller-supplied result can never authorize writing. */
 async prepareCommit(token:VerifiedResolutionPrefix):Promise<ResolutionPrefixCommit>{
  const result=await this.calculate(token),certificate=certificateFor(this,token)
  const commit=Object.freeze({}) as ResolutionPrefixCommit
  commits.set(commit,{owner:this,certificate,result});return commit
 }
 async commit(token:ResolutionPrefixCommit):Promise<'advanced'|'already_proven'|'no_progress'>{
  const plan=commits.get(token);if(!plan||plan.owner!==this)fail()
  const p=plan.certificate;if(!p.current())fail('closed')
  let activeAbort:((e:unknown)=>void)|undefined
  const stop=()=>activeAbort?.(new BrowserPersistenceError('closed')),unAuth=this.auth.onInvalidated(stop),unKey=this.keys.onInvalidated(stop)
  try{return await this.transaction(p.scope,resolutionInventoryStores,'readwrite',(tx,result,abort)=>{
   activeAbort=abort
   scheduleResolutionInventory(tx,p.scope,p.current,v=>{try{
    if(!p.current())fail('closed')
    const target=plan.result.candidate_proven_prefix
    const expected={...p.inventory,cursor:{...p.inventory.cursor,proven_prefix:target},checkpoints:p.inventory.checkpoints.map(raw=>({...raw as object,proven_prefix:target}))}
    const already=target>p.inventory.cursor.proven_prefix&&same(v,expected)
    if(!already&&!same(v,p.inventory))fail('stale_source')
    // Exact full inventory CAS makes the original outside-transaction AEAD and
    // family certificates current. No crypto/HTTP/async callback inside IDB.
    if(!same(calculate(p),plan.result))fail('stale_source')
    if(already){result('already_proven');return}
    if(target===v.cursor.proven_prefix){result('no_progress');return}
    if(target<v.cursor.proven_prefix||target>v.cursor.pull_cursor||v.cursor.ack_cursor>target)fail()
    const request=tx.objectStore('cursors').put({...v.checkpoints[0] as object,proven_prefix:target})
    request.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))}
    result('advanced') // Session resolves ONLY after native transaction completion.
   }catch(e){abort(e)}},abort)
  })}finally{activeAbort=undefined;unAuth();unKey()}
 }
}
