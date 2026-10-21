import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import type {NoteSyncPlaintext} from '@/cloud/noteSyncCodec'
import {BrowserPersistenceError} from './persistence'
import {BrowserLocalAuthority,type BrowserLocalAuthorityRuntime,type ProtectedNoteSourcePlan,scheduleProtectedNoteApply} from './localAuthority'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {resolutionInventoryStores,scheduleResolutionInventory,ResolutionPlannerError,type ResolutionInventorySnapshot,MAX_PLANNER_INVENTORY_BYTES,MAX_PLANNER_ROWS} from './resolutionPlanner'
import {boundResolutionJson,readFutureInboxRecord} from './resolutionRecords'
import {authenticateContinuationHistory,continuationDependencyView,sameResolutionValue as same} from './resolutionHistorical'
import {validateMixedSourceInventory,MixedSourceWitnessError} from './mixedSourceValidation'
import {snapshotBrowserSyncScope,validateBrowserInboxRecord,type BrowserSyncScope,type BrowserSyncTransaction,type BrowserInboxRecord} from './syncDurability'
import {validateBrowserProjectBinding} from './projectBindings'
import {openNoteTransport} from './noteTransport'
import {makeHistoryCandidate,nextNoteHead} from './noteHistory'
import {prepareNotePrerequisite,prepareNoteTransportCommit,scheduleNoteTransportCommit,type VerifiedNoteTransportCommit} from './noteTransportPrerequisite'
import {noteProofDigest,noteOutcomeDigest} from './legacyNoteApply'
import {contentProofFor} from './contentNoteProof'
import {validateBrowserNoteProof,type BrowserNoteProof} from './noteApplyRecords'
import {assertContentNoteRoute} from './localAuthorityRecords'
import type {BrowserNoteCandidate,BrowserNoteHead} from './noteHistoryRecords'

export interface V10OrdinaryToken {readonly v10Ordinary:unique symbol}
interface Plan {
 owner:BrowserV10OrdinaryApplyRuntime;local:BrowserLocalAuthorityRuntime;scope:BrowserSyncScope;inventory:ResolutionInventorySnapshot;
 row:BrowserInboxRecord;plaintext:NoteSyncPlaintext;content:boolean;current:()=>boolean;handoff:boolean;
 source?:ProtectedNoteSourcePlan;candidate?:BrowserNoteCandidate;head?:BrowserNoteHead;nextRow?:BrowserInboxRecord;transport?:VerifiedNoteTransportCommit
}
const plans=new WeakMap<object,Plan>()
function fail(code:'closed'|'corrupt_record'|'stale_source'|'unsupported_local_source'|'note_orphan'|'note_conflict_unproven'|'conflicting_record'|'source_limit'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
/** Internal opaque handoff, never a read-only diagnostic/counts or plaintext DTO. */
export function verifiedV10OrdinaryForLocal(token:V10OrdinaryToken,local:BrowserLocalAuthorityRuntime,scope:BrowserSyncScope){
 const p=plans.get(token)
 if(!p||p.local!==local||!same(p.scope,scope)||!p.current()||p.handoff)fail('closed')
 p.handoff=true
 return{plaintext:structuredClone(p.plaintext),content:p.content,current:p.current}
}
const route=(n:NoteSyncPlaintext['note'])=>[n.id,n.project_id,n.stage_id,n.source_type,n.source_map_id,n.source_node_id,n.content_format]
function bounded(v:ResolutionInventorySnapshot){
 let remaining=MAX_PLANNER_INVENTORY_BYTES
 for(const values of [v.rows,v.out,v.receipts,v.bindings,v.owners,v.history,v.intents,v.projects,v.localNotes,v.checkpoints]){
  if(values.length>MAX_PLANNER_ROWS)fail('source_limit')
  for(const value of values){
   try{boundResolutionJson(value,remaining)}catch{fail('source_limit')}
   const bytes=new TextEncoder().encode(JSON.stringify(value))
   try{remaining-=bytes.length+2;if(remaining<0)fail('source_limit')}finally{bytes.fill(0)}
  }
 }
}
/** O's explicit dormant owner; absent from persistence composition and H/G/K.
 * Received-only independent Notes in the one F project, import_remote/captured.
 * Original/retained roles, unrelated projects and forks require another owner. */
export class BrowserV10OrdinaryApply {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthority,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){return new BrowserV10OrdinaryApplyRuntime(this.transaction,this.local.bind(auth,bindings,keys),this.profileCurrent,auth,bindings,keys,device)}
}
export class BrowserV10OrdinaryApplyRuntime {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthorityRuntime,private readonly profileCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext,private readonly device:VerifiedBrowserDevice){}
 private async guard(s:BrowserSyncScope){
  const initial=this.auth.requireContext(),{context}=await this.bindings.ensureForCurrentUser(s.accountId),lease=this.keys.leaseForAccount(s.accountId)
  const current=()=>this.profileCurrent()&&this.auth.isCurrent(initial)&&this.auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(this.device,s,this.auth)
  if(!lease||lease.authEpoch!==context.authEpoch||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||context.userId!==s.canonicalUserId||!current())fail('closed')
  return{lease,current}
 }
 private load(s:BrowserSyncScope,current:()=>boolean){return this.transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort))}
 private async sanitized<T>(run:()=>Promise<T>):Promise<T>{
  try{return await run()}catch(e){
   if(e instanceof BrowserPersistenceError||e instanceof MixedSourceWitnessError)throw e
   if(e instanceof ResolutionPlannerError&&e.code==='resource_limit')fail('source_limit')
   // AEAD/decoder/parser errors must not include source plaintext in diagnostics.
   fail()
  }
 }
 async prepare(input:BrowserSyncScope,sequence:number):Promise<V10OrdinaryToken>{return this.sanitized(async()=>{
  const s=snapshotBrowserSyncScope(input),{lease,current}=await this.guard(s),v=await this.load(s,current)
  const step=async<T>(promise:Promise<T>)=>{const value=await promise;if(!current())fail('closed');return value}
  return lease.use(async amk=>{
   // A fresh owner-owned complete pre-state check; N.inspect is never consumed.
   await step(validateMixedSourceInventory(s,v,amk,current))
   const h=await step(authenticateContinuationHistory(s,v,amk,current)),root=[...h.resolutions.values()][0]!
   const future=readFutureInboxRecord(v.rows.find((r:any)=>r.server_sequence===sequence),s)
   if(future.state!=='received'||sequence<=root.record.server_sequence||sequence>v.cursor.pull_cursor)fail('conflicting_record')
   // Manual retry must start with the earliest received event of ANY family.
   if(h.rows.some(r=>r.state==='received'&&r.server_sequence<sequence))fail('note_orphan')
   const row=validateBrowserInboxRecord(future,s),wire=JSON.parse(row.wire_item),e=wire.event,content=row.protocol_version===3
   if(e.device_id===s.deviceId||e.entity_type!=='note'||content&&e.operation!=='event'||!content&&!['upsert','delete'].includes(e.operation))fail('unsupported_local_source')
   if(e.project_id!==root.record.project_id||[root.record.note_id,root.record.retained_note_id].includes(e.entity_id))fail('unsupported_local_source')
   const binding=v.bindings.map(b=>validateBrowserProjectBinding(b,s)).find(b=>b.project_id===e.project_id)
   if(!binding||binding.bootstrap_id!==root.record.bootstrap_id||binding.remote_state!=='active'||binding.mode!=='import_remote'||binding.phase!=='captured')fail('unsupported_local_source')
   const prerequisite=content?await step(prepareNotePrerequisite(s,row,binding,amk,current,undefined,continuationDependencyView(v,row))):undefined
   const plaintext=prerequisite?.plaintext??(await step(openNoteTransport(s,amk,2,row.wire_item,'legacy'))).plaintext,header=plaintext.header
   assertContentNoteRoute(plaintext.note)
   if(!content&&(plaintext.note.stage_id!==null||plaintext.note.content_format!=='html'))fail('unsupported_local_source')
   const own=[...h.dag.events.values()].filter((c):c is BrowserNoteCandidate=>c.record_kind==='candidate'&&c.project_id===e.project_id&&c.note_id===e.entity_id)
   const head=h.dag.history.find(r=>r.record_kind==='head'&&r.project_id===e.project_id&&r.note_id===e.entity_id)
   if(head&&(head.record_kind!=='head'||head.record_version!==1||head.tip_event_ids.length!==1))fail('note_conflict_unproven')
   const source=await step(this.local.readSnapshot(s,e.project_id))
   if(!same(source.project,v.projects.find((p:any)=>p.project_id===e.project_id))||!same(source.notes,v.localNotes.filter((n:any)=>n.project_id===e.project_id)))fail('stale_source')
   const old=source.notes.find(n=>n.note_id===e.entity_id)
   if(plaintext.mutation==='create'){
    if(header.parent_event_id!==null||header.revision!==1||head||own.length||old||v.localNotes.some((n:any)=>n.note_id===e.entity_id)||h.dag.history.some(r=>r.note_id===e.entity_id||r.record_kind==='resolution'&&r.retained_note_id===e.entity_id))fail('conflicting_record')
   }else{
    if(!head||head.record_kind!=='head'||head.record_version!==1||head.linear_head_event_id!==header.parent_event_id||head.tip_event_ids[0]!==header.parent_event_id||!old)fail('note_orphan')
    const parent=own.find(c=>c.event_id===header.parent_event_id),prior=parent&&h.opened.get(parent.event_id),parentRow=parent&&h.rows.find(r=>r.event_id===parent.event_id)
    if(!parent||!prior||!parentRow||parent.origin!=='peer'||!parent.projection||!same(parent.projection,old)||header.revision!==parent.header.revision+1||parentRow.server_sequence>=sequence||!same(route(prior.note),route(plaintext.note)))fail('note_orphan')
    if(old.deleted&&plaintext.mutation!=='delete')fail('unsupported_local_source')
   }
   const token=Object.freeze({}) as V10OrdinaryToken,p:Plan={owner:this,local:this.local,scope:s,inventory:v,row,plaintext,content,current,handoff:false}
   plans.set(token,p)
   try{
    const prepared=await step(this.local.prepareProtectedV10OrdinaryApply(s,source.token,token))
    if(prepared.source_revision!==source.project.source_revision+1||prepared.project.source_revision!==prepared.source_revision||prepared.note.source_revision!==prepared.source_revision||prepared.project.project_id!==e.project_id||prepared.note.project_id!==e.project_id||prepared.note.note_id!==e.entity_id)fail()
    p.source=prepared.token
    let candidate:BrowserNoteCandidate
    if(content){const result=await step(prepareNoteTransportCommit(prerequisite!.certificate,plaintext,prepared.note));candidate=result.candidate;p.transport=result.hook}
    else{const {device_id:_device,server_sequence:_sequence,...event}=wire.event;candidate=await step(makeHistoryCandidate(s,binding,2,e.device_id,{event,object:wire.object},plaintext,'peer',prepared.note))}
    let nextRow:BrowserInboxRecord
    if(content)nextRow=validateBrowserInboxRecord({...row,record_version:7,state:'content_note_proven',content_note_proof:await step(contentProofFor(s,row,candidate,plaintext.mutation))},s)
    else{
     const proof:BrowserNoteProof={record_version:1,owner_kind:'legacy_note',account_id:s.accountId,bootstrap_id:binding.bootstrap_id,protocol_version:2,reference:e,header,mutation:plaintext.mutation,wire_digest:await step(noteProofDigest({protocol_version:2,event:e,object:wire.object})),outcome_digest:'',outcome:'applied',source_revision:prepared.source_revision,local_note_digest:await step(noteProofDigest(prepared.note))}
     proof.outcome_digest=await step(noteOutcomeDigest(proof));validateBrowserNoteProof(proof,s)
     nextRow=validateBrowserInboxRecord({...row,record_version:3,state:'note_proven',note_proof:proof},s)
    }
    const nextHead=nextNoteHead(s,binding,[...own,candidate],header.event_id,head as BrowserNoteHead|undefined)
    const predicted:ResolutionInventorySnapshot={...v,history:[...v.history.filter((r:any)=>!(r.record_kind==='head'&&r.project_id===e.project_id&&r.note_id===e.entity_id)),candidate,nextHead],rows:v.rows.map(r=>same(r,row)?nextRow:r),projects:v.projects.map((r:any)=>r.project_id===e.project_id?prepared.project:r),localNotes:[...v.localNotes.filter((n:any)=>!(n.project_id===e.project_id&&n.note_id===e.entity_id)),prepared.note]}
    bounded(predicted)
    await step(validateMixedSourceInventory(s,predicted,amk,current))
    p.candidate=candidate;p.head=nextHead;p.nextRow=nextRow
    if(!same(await step(this.load(s,current)),v))fail('stale_source')
    return token
   }catch(e){plans.delete(token);throw e}
  })
 })}
 async commit(token:V10OrdinaryToken):Promise<'applied'>{
  const p=plans.get(token)
  if(!p||p.owner!==this||!p.current()||!p.source||!p.candidate||!p.head||!p.nextRow)fail('closed')
  plans.delete(token)
  let activeAbort:((e:unknown)=>void)|undefined
  const stop=()=>activeAbort?.(new BrowserPersistenceError('closed')),unAuth=this.auth.onInvalidated(stop),unKey=this.keys.onInvalidated(stop)
  try{return await this.transaction(p.scope,resolutionInventoryStores,'readwrite',(tx,result,abort)=>{
   activeAbort=abort
   scheduleResolutionInventory(tx,p.scope,p.current,v=>{try{
    if(!p.current())fail('closed');if(!same(v,p.inventory))fail('stale_source')
    scheduleProtectedNoteApply(tx,p.scope,p.source!,()=>{
     const finish=()=>{
      try{
       if(!p.current())fail('closed')
       const requests=[tx.objectStore('legacyNoteHistory').put(p.head),tx.objectStore('inbox').put(p.nextRow)]
       if(!p.transport)requests.push(tx.objectStore('legacyNoteHistory').add(p.candidate))
       requests.forEach(r=>r.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))})
       result('applied')
      }catch(e){abort(e)}
     }
     if(p.transport)scheduleNoteTransportCommit(tx,p.transport,finish,abort);else finish()
    },abort)
   }catch(e){abort(e)}},abort)
  })}finally{activeAbort=undefined;unAuth();unKey()}
 }
 async reconcile(input:BrowserSyncScope,sequence:number):Promise<'already_applied'>{return this.sanitized(async()=>{
  const s=snapshotBrowserSyncScope(input),{lease,current}=await this.guard(s),v=await this.load(s,current)
  await lease.use(async amk=>{
   await validateMixedSourceInventory(s,v,amk,current)
   const h=await authenticateContinuationHistory(s,v,amk,current),root=[...h.resolutions.values()][0]!,row=h.rows.find(r=>r.server_sequence===sequence),c=row&&h.dag.events.get(row.event_id)
   if(!row||!['note_proven','content_note_proven'].includes(row.state)||!c||c.record_kind!=='candidate'||c.origin!=='peer'||!c.projection||c.project_id!==root.record.project_id||[root.record.note_id,root.record.retained_note_id].includes(c.note_id)||sequence<=root.record.server_sequence)fail('unsupported_local_source')
  })
  if(!current()||!same(await this.load(s,current),v))fail('stale_source')
  return'already_applied' as const
 })}
 async apply(input:BrowserSyncScope,sequence:number){
  const s=snapshotBrowserSyncScope(input),{current}=await this.guard(s),v=await this.load(s,current),row=readFutureInboxRecord(v.rows.find((r:any)=>r.server_sequence===sequence),s)
  return row.state==='received'?this.commit(await this.prepare(s,sequence)):this.reconcile(s,sequence)
 }
}
