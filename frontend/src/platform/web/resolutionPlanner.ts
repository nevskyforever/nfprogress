import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import {decryptObjectBytes,type AccountMasterKey} from '@/crypto'
import {decodeBase64Url} from '@/api/base64url'
import {unframeContentNote,type ContentNoteEvent} from '@/cloud/contentNoteCodec'
import {decodeNoteSyncResolutionV2,type NoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {canonicalizeSyncTimestamp} from '@/cloud/syncTimestamp'
import type {NoteSyncPlaintext,NoteSyncRecord,NoteSyncTombstone} from '@/cloud/noteSyncCodec'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {BrowserLocalAuthority,type BrowserLocalAuthorityRuntime,type LocalSourceToken} from './localAuthority'
import {assertContentNoteRoute,validateContentLocalNote,validateLocalNote,MAX_LOCAL_SOURCE_BYTES,MAX_LOCAL_NOTES,localCanonicalBytes} from './localAuthorityRecords'
import {snapshotBrowserSyncScope,validateBrowserInboxRecord,validateBrowserStoredUploadPair,validateBrowserSyncCursor,immutableWireIdentity,type BrowserSyncScope,type BrowserSyncTransaction,type BrowserInboxRecord} from './syncDurability'
import {validateBrowserProjectBinding} from './projectBindings'
import {validateNoteHistorySet,type BrowserNoteCandidate,type BrowserNoteConflictGroup,type BrowserNoteHead} from './noteHistoryRecords'
import {validateNoteIntentRecord} from './noteIntentRecords'
import {validateBrowserV9State} from './indexedDbV9Migration'
import {inspectResolutionDag} from './resolutionDag'
import {boundResolutionJson} from './resolutionRecords'
import {openHistoryCandidate} from './noteHistory'
import {openNoteTransport} from './noteTransport'
import {verifyContentGroup} from './contentNoteConflictProof'
import {verifyStoredContentNoteProof} from './contentNoteProof'
import {openFrozenLocalVersion} from './noteUnsealedVersion'
import {verifyStoredNoteProof} from './legacyNoteApply'
import {authenticateContentAuthorityInventory} from './contentAuthorityInventory'
import {prepareMetadataPrefix,verifiedMetadataSequences} from './metadataPrefixProof'
import {validateBrowserMetadataHead} from './metadataApplyRecords'
import {prepareStagePrefix,stageSequences} from './stageApply'
import {validateStageHead} from './stageRecords'
import {proveStageReferenceCoverage} from './stageOrderRecords'
import type {BrowserPrefixInventory} from './provenPrefixRecords'

export const MAX_PLANNER_ROWS=16384
export const MAX_PLANNER_INVENTORY_BYTES=32*1024*1024
export type ResolutionPlannerCode='missing_parent'|'missing_publication'|'missing_bootstrap'|'dependency_unavailable'|'missing_conflict'|'stale_inventory'|'invalid_resolution'|'source_incompatible'|'resource_limit'|'lifecycle_invalid'|'clone_collision'
export class ResolutionPlannerError extends Error {
 readonly name='ResolutionPlannerError'
 constructor(readonly code:ResolutionPlannerCode){super(`resolution_planner_${code}`)}
}
function fail(code:ResolutionPlannerCode):never{throw new ResolutionPlannerError(code)}
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const stores=['inbox','outbox','receipts','projectBindings','ownerHeads','legacyNoteHistory','legacyNoteIntents','localProjects','localNotes','cursors']
interface Inventory extends BrowserPrefixInventory {projects:unknown[];localNotes:unknown[];intents:unknown[];checkpoints:unknown[]}
export interface ResolutionPlannerToken {readonly resolutionPlannerToken:unique symbol}
export interface ResolutionPlanStatus {readonly readOnly:true;readonly commitAuthorized:false;readonly ackAuthorized:false;readonly parentCount:number;readonly strategy:NoteSyncResolutionV2['resolution']['strategy']}
interface Plan {owner:BrowserResolutionPlannerRuntime;scope:BrowserSyncScope;sequence:number;inventory:Inventory;source:LocalSourceToken;current:()=>boolean;resolution:NoteSyncResolutionV2;group:BrowserNoteConflictGroup;parents:Map<string,NoteSyncPlaintext>;status:ResolutionPlanStatus}
const plans=new WeakMap<object,Plan>()
const wireNote=(n:NoteSyncRecord|NoteSyncTombstone|Record<string,unknown>)=>{const v={...n};delete(v as Record<string,unknown>).revision;return v}
const route=(n:NoteSyncRecord|NoteSyncTombstone)=>[n.project_id,n.stage_id,n.source_type,n.source_map_id,n.source_node_id,n.content_format]

/** Dormant internal entry point. Never composed into BrowserPersistence/editor/scheduler. */
export class BrowserResolutionPlanner {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthority,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){return new BrowserResolutionPlannerRuntime(this.transaction,this.local.bind(auth,bindings,keys),this.profileCurrent,auth,bindings,keys,device)}
}
export class BrowserResolutionPlannerRuntime {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthorityRuntime,private readonly profileCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext,private readonly device:VerifiedBrowserDevice){}
 private async guard(s:BrowserSyncScope){
  const initial=this.auth.requireContext()
  if(!this.profileCurrent()||!currentBrowserDevice(this.device,s,this.auth))fail('lifecycle_invalid')
  const {context}=await this.bindings.ensureForCurrentUser(s.accountId),lease=this.keys.leaseForAccount(s.accountId)
  const current=()=>this.profileCurrent()&&this.auth.isCurrent(initial)&&this.auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(this.device,s,this.auth)
  if(!lease||context.userId!==s.canonicalUserId||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||lease.authEpoch!==context.authEpoch||!current())fail('lifecycle_invalid')
  return{lease,current}
 }
 private load(s:BrowserSyncScope,current:()=>boolean):Promise<Inventory>{
  return this.transaction(s,stores,'readonly',(tx,result,abort)=>{
   const range=IDBKeyRange.bound([s.accountId],[s.accountId,[]]),arrays:unknown[][]=stores.map(()=>[])
   let completed=0,left=MAX_PLANNER_INVENTORY_BYTES-2*stores.length
   stores.forEach((name,index)=>{
    const request=tx.objectStore(name).openCursor(range)
    request.onsuccess=()=>{try{
     if(!current())fail('lifecycle_invalid')
     const cursor=request.result
     if(cursor){
      if(arrays[index]!.length>=MAX_PLANNER_ROWS)fail('resource_limit')
      const value:unknown=cursor.value
      // Admit one record before retaining it; do not materialize every account
      // store with getAll and discover the aggregate limit only afterwards.
      try{boundResolutionJson(value,left)}catch{fail('resource_limit')}
      const bytes=new TextEncoder().encode(JSON.stringify(value))
      try{left-=bytes.length+1;if(left<0)fail('resource_limit')}finally{bytes.fill(0)}
      arrays[index]!.push(value);cursor.continue();return
     }
     if(++completed!==stores.length)return
     const [rows,out,receipts,bindings,owners,history,intents,projects,localNotes,checkpoints]=arrays as [unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[],unknown[]]
     if(checkpoints.length!==1)fail('invalid_resolution')
     result({rows,out,receipts,bindings,owners,history,intents,projects,localNotes,checkpoints,cursor:validateBrowserSyncCursor(checkpoints[0],s)})
    }catch(e){abort(e)}}
   })
  })
 }
 private async original(s:BrowserSyncScope,row:BrowserInboxRecord,amk:AccountMasterKey,check:()=>void){
  if(row.state!=='received')fail('invalid_resolution')
  const wire=JSON.parse(row.wire_item),e=wire.event
  if(e.entity_type!=='note'||e.deleted_at!==null||e.device_id===s.deviceId||!(row.protocol_version===2&&e.operation==='resolution'||row.protocol_version===3&&e.operation==='event')||wire.object.crypto_version!==1||wire.object.aad_version!==1)fail('invalid_resolution')
  const nonce=decodeBase64Url(wire.object.nonce),ciphertext=decodeBase64Url(wire.object.ciphertext);let bytes:Uint8Array|undefined
  try{
   bytes=await decryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:e.project_id,entityId:e.entity_id,entityType:'note'},{...wire.object,nonce,ciphertext});check()
   let resolution:NoteSyncResolutionV2,content:ContentNoteEvent|undefined
   if(row.protocol_version===3){content=unframeContentNote(bytes);if(content.event.version!==2||content.account_id!==s.canonicalUserId||content.device_id!==e.device_id)fail('invalid_resolution');resolution=content.event}
   else resolution=decodeNoteSyncResolutionV2(bytes)
   const h=resolution.header
   if(h.event_id!==row.event_id||h.event_id!==e.event_id||h.project_id!==e.project_id||h.entity_id!==e.entity_id||h.revision!==e.revision||h.updated_at!==canonicalizeSyncTimestamp(e.updated_at))fail('invalid_resolution')
   const outputs=[resolution.result.note,...(resolution.resolution.strategy==='keep_both'?[resolution.resolution.retained_note]:[])]
   for(const n of outputs){
    assertContentNoteRoute(n)
    if('content'in n){let title=0,body=0;for(const _ of n.title)if(++title>500)fail('resource_limit');for(const _ of n.content)if(++body>300000)fail('resource_limit')}
    if(row.protocol_version===2&&(n.stage_id!==null||n.content_format!=='html'))fail('source_incompatible')
    const source='deleted_at'in n?{state:'tombstone' as const,note:n,revision:0}:{state:'live' as const,note:{...n,revision:0}}
    try{(row.protocol_version===3?validateContentLocalNote:validateLocalNote)(source,h.project_id);const b=localCanonicalBytes({local_format:1,kind:'note',account_id:s.accountId,device_id:s.deviceId,project_id:h.project_id,note_id:n.id,source_revision:1,source});try{if(b.length>MAX_LOCAL_SOURCE_BYTES)fail('resource_limit')}finally{b.fill(0)}}catch(e){if(e instanceof ResolutionPlannerError)throw e;fail('source_incompatible')}
   }
   return{resolution,content}
  }finally{nonce.fill(0);ciphertext.fill(0);bytes?.fill(0)}
 }
 private async dependencies(s:BrowserSyncScope,row:BrowserInboxRecord,content:ContentNoteEvent|undefined,v:Inventory,amk:AccountMasterKey,step:<T>(p:Promise<T>)=>Promise<T>,current:()=>boolean){
  if(!content)return // Protocol2 does not acquire invented Content dependencies.
  const d=content.dependencies,h=content.event.header,b=v.bindings.map(b=>validateBrowserProjectBinding(b,s)).find(b=>b.project_id===h.project_id)
  if(!b||b.mode!=='import_remote'||b.phase!=='captured'||b.remote_state!=='active'||d.bootstrap_id!==b.bootstrap_id)fail('dependency_unavailable')
  const rawHead=v.owners.find((x:any)=>x.owner_kind==='project_metadata'&&x.owner_id===h.project_id)
  if(!rawHead)fail('dependency_unavailable')
  const cert=await step(prepareMetadataPrefix(s,v,amk,current,true)),safe=verifiedMetadataSequences(cert,s,v)
  const head=validateBrowserMetadataHead(rawHead,s)
  const dependency=head.history.find(p=>p.event_id===d.metadata_event_id),tip=head.history.find(p=>p.event_id===head.tip_event_ids[0])
  if(head.bootstrap_id!==b.bootstrap_id||head.tip_event_ids.length!==1||!dependency||dependency.operation==='delete'||!safe.has(dependency.server_sequence)||!tip||tip.operation==='delete'||!safe.has(tip.server_sequence))fail('dependency_unavailable')
  if(content.event.version!==2)fail('invalid_resolution')
  const outputs=[content.event.result.note,...(content.event.resolution.strategy==='keep_both'?[content.event.resolution.retained_note]:[])]
  for(const n of outputs){
   if(n.stage_id===null){if(d.stage_event_ids.length)fail('dependency_unavailable');continue}
   const raw=v.owners.find((x:any)=>x.owner_kind==='stage'&&x.project_id===h.project_id&&x.stage_id===n.stage_id)
   if(!raw)fail('dependency_unavailable')
   const stage=validateStageHead(raw,s),st=await step(prepareStagePrefix(s,v,amk,current,cert,true)),covered=stageSequences(st,s,v)
   if(stage.bootstrap_id!==b.bootstrap_id||stage.history.some(p=>!covered.has(p.server_sequence))||!proveStageReferenceCoverage(stage.tip_event_ids,d.stage_event_ids,stage.history))fail('dependency_unavailable')
   for(const raw of v.rows){const r=validateBrowserInboxRecord(raw,s),e=JSON.parse(r.wire_item).event;if(r.server_sequence<row.server_sequence&&e.entity_type==='stage'&&e.project_id===h.project_id&&e.entity_id===n.stage_id&&(r.state!=='stage_proven'||!covered.has(r.server_sequence)))fail('dependency_unavailable')}
  }
 }
 private collision(s:BrowserSyncScope,resolution:NoteSyncResolutionV2,v:Inventory,futureChildren:WeakSet<object>,reservedClones:Map<string,string>){
  const decision=resolution.resolution;if(decision.strategy!=='keep_both')return
  const id=decision.retained_note.id
  // A retained *reference* from a future child is not an allocation. Received
  // unknown payloads cannot prove safe child identity and remain explicit blockers.
  if(v.localNotes.some((r:any)=>r.note_id===id)||v.intents.some((r:any)=>r.note_id===id)||v.history.some((r:any)=>r.note_id===id||r.retained_note_id===id))fail('clone_collision')
  for(const raw of v.out){const r=validateBrowserStoredUploadPair(raw,v.receipts.find((p:any)=>p.event_id===(raw as any).event_id),s),e=JSON.parse(r.raw_body).items[0].event;if(e.entity_type==='note'&&e.entity_id===id)fail('clone_collision')}
  for(const raw of v.rows){const r=validateBrowserInboxRecord(raw,s),w=JSON.parse(r.wire_item),e=w.event;if(e.event_id===resolution.header.event_id)continue
   if(e.entity_type==='note'&&e.entity_id===id){
    // Existing proven or genesis identities reserve the name. A future child is
    // checked cryptographically in prepare before this structural reservation pass.
    if(r.state!=='received'||!futureChildren.has(raw as object))fail('clone_collision')
   }
   if(e.entity_type==='note'&&reservedClones.get(e.event_id)===id)fail('clone_collision')
  }
 }
 async prepare(input:BrowserSyncScope,sequence:number):Promise<{token:ResolutionPlannerToken;status:ResolutionPlanStatus}>{
  try{
   const s=snapshotBrowserSyncScope(input),{lease,current}=await this.guard(s)
   const check=()=>{if(!current())fail('lifecycle_invalid')},step=async<T>(p:Promise<T>)=>{const value=await p;check();return value}
   if(!Number.isSafeInteger(sequence)||sequence<1)fail('invalid_resolution')
   const v=await step(this.load(s,current)),rows=v.rows.map(r=>validateBrowserInboxRecord(r,s)),row=rows.find(r=>r.server_sequence===sequence)
   if(!row||row.server_sequence>v.cursor.pull_cursor)fail('invalid_resolution')
   if(new Set(rows.map(r=>r.event_id)).size!==rows.length||new Set(rows.map(r=>r.server_sequence)).size!==rows.length)fail('invalid_resolution')
   return await step(lease.use(async amk=>{
    const {resolution,content}=await step(this.original(s,row,amk,check)),h=resolution.header,ids=resolution.resolution.resolved_event_ids
    const binding=v.bindings.map(b=>validateBrowserProjectBinding(b,s)).find(b=>b.project_id===h.project_id)
    if(!binding)fail('missing_bootstrap')
    if(binding.remote_state!=='active'||!(binding.mode==='import_remote'&&binding.phase==='captured'||binding.mode==='upload_existing'&&binding.phase==='completing'))fail('missing_bootstrap')
    const relevant=v.history.filter((r:any)=>r.project_id===h.project_id&&r.note_id===h.entity_id)
    for(const id of ids)if(!relevant.some((r:any)=>r.record_kind==='candidate'&&r.event_id===id)){
     if(v.intents.some((r:any)=>r.event_id===id)||relevant.some((r:any)=>r.record_kind==='local_version'&&r.header.event_id===id))fail('missing_publication')
     fail('missing_parent')
    }
    const history=validateNoteHistorySet(s,relevant),dag=inspectResolutionDag(s,history),group=history.find((r):r is BrowserNoteConflictGroup=>r.record_kind==='group'),head=history.find((r):r is BrowserNoteHead=>r.record_kind==='head')
    if(!group||!head)fail('missing_conflict')
    if(group.bootstrap_id!==binding.bootstrap_id||!same(group.tip_event_ids,ids)||!same(head.tip_event_ids,ids)||!same(dag.frontier(h.project_id,h.entity_id,binding.bootstrap_id),ids))fail('stale_inventory')
    const candidates=history.filter((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'),parents=candidates.filter(c=>ids.includes(c.event_id))
    if(parents.length!==ids.length||h.revision!==Math.max(...parents.map(c=>c.header.revision))+1||parents.some(c=>c.bootstrap_id!==binding.bootstrap_id||c.header.parent_event_id!==group.common_parent_event_id))fail('invalid_resolution')
    if(v.intents.map(i=>validateNoteIntentRecord(i,s)).some(i=>i.project_id===h.project_id&&i.note_id===h.entity_id))fail('missing_publication')
    await step(authenticateContentAuthorityInventory(s,{...v,history:v.history},amk,current))
    for(const c of candidates){
     const inbound=rows.find(r=>r.event_id===c.event_id)
     if(c.source_device_id===s.deviceId){
      const o=v.out.find((r:any)=>r.event_id===c.event_id),receipt=v.receipts.find((r:any)=>r.event_id===c.event_id)
      if(!o||!receipt)fail('missing_publication')
      const out=validateBrowserStoredUploadPair(o,receipt,s),w=JSON.parse(out.raw_body).items[0]
      if(out.state!=='accepted'||out.protocol_version!==c.protocol_version||!same(w,JSON.parse(c.wire_item)))fail('invalid_resolution')
      if(inbound&&(inbound.server_sequence!==(receipt as any).server_sequence||!same(JSON.parse(inbound.wire_item).object,w.object)))fail('invalid_resolution')
     }else{
      if(!inbound||!['note_proven','note_conflict_preserved','content_note_proven','content_note_conflict_preserved'].includes(inbound.state))fail('missing_publication')
      const w=JSON.parse(inbound.wire_item),{device_id,server_sequence:_seq,...event}=w.event
      if(device_id!==c.source_device_id||c.protocol_version!==inbound.protocol_version||!same(c.record_version===2?w:{event,object:w.object},JSON.parse(c.wire_item)))fail('invalid_resolution')
      if(inbound.state==='note_proven')await step(verifyStoredNoteProof(s,amk,inbound))
      if(inbound.state==='content_note_proven')await step(verifyStoredContentNoteProof(s,amk,inbound,history))
     }
    }
    await step(verifyContentGroup(s,group,history,rows,amk,{out:v.out,receipts:v.receipts}))
    const opened=new Map<string,NoteSyncPlaintext>();let materialBytes=0
    for(const c of candidates){const p=await step(openHistoryCandidate(s,c,amk));const bytes=new TextEncoder().encode(immutableWireIdentity(p));try{materialBytes+=bytes.length;if(materialBytes>16*1024*1024)fail('resource_limit')}finally{bytes.fill(0)}opened.set(c.event_id,p)}
    for(const m of group.members)if(m.source==='local_unsealed'){
     const frozen=history.find(r=>r.record_kind==='local_version'&&r.version_id===m.version_id),sealed=parents.find(c=>c.event_id===m.event_id)
     if(!frozen||frozen.record_kind!=='local_version'||!sealed||sealed.record_version!==1||sealed.origin!=='local_sealed'||(sealed.mutation_generation??0)<frozen.intent.mutation_generation)fail('missing_publication')
     await step(openFrozenLocalVersion(s,frozen,amk))
    }
    const result=resolution.result,decision=resolution.resolution,selected='selected_event_id'in decision?opened.get(decision.selected_event_id):undefined
    if(parents.some(c=>!same(route(opened.get(c.event_id)!.note),route(result.note))))fail('source_incompatible')
    if(decision.strategy==='choose_version'||decision.strategy==='keep_both')if(!selected||selected.header.operation!==result.operation||!same(selected.note,result.note))fail('invalid_resolution')
    if(decision.strategy==='keep_both'){
     const other=opened.get(decision.retained_event_id)
     if(parents.length!==2||parents.some(c=>c.header.operation!=='upsert')||!other||!same({...other.note,id:decision.retained_note.id,created_at:decision.retained_note.created_at,updated_at:decision.retained_note.updated_at},decision.retained_note)||!same(route(result.note),route(decision.retained_note)))fail('invalid_resolution')
    }
    try{await step(this.dependencies(s,row,content,v,amk,step,current))}catch(e){check();if(e instanceof ResolutionPlannerError)throw e;fail('dependency_unavailable')}
    // Current-format inventory also retains the accepted shared ordinal/pull/ACK
    // invariants. Structural validation never grants AEAD or prefix authority.
    validateBrowserV9State([s],[v.out,v.rows,v.checkpoints,v.receipts,v.bindings,v.owners,v.projects,v.localNotes,v.history,v.intents])
    // Authenticate account-wide incoming Resolution reservations and distinguish a
    // valid future child reference from an already allocated proposed clone.
    const futureChildren=new WeakSet<object>(),reservedClones=new Map<string,string>()
    if(decision.strategy==='keep_both')for(const raw of v.rows){const r=validateBrowserInboxRecord(raw,s),w=JSON.parse(r.wire_item),e=w.event
     if(r.event_id===row.event_id||e.entity_type!=='note'||r.state!=='received')continue
     if(e.entity_id===decision.retained_note.id){
      const p=await step(openNoteTransport(s,amk,r.protocol_version,r.wire_item,['upsert','delete'].includes(e.operation)?'legacy':'content_note_v1'))
      if(p.plaintext.header.parent_event_id===h.event_id&&p.plaintext.header.revision===h.revision+1&&same(route(p.plaintext.note),route(decision.retained_note))&&e.project_id===h.project_id)futureChildren.add(raw as object)
     }else if((r.protocol_version===2&&e.operation==='resolution')||(r.protocol_version===3&&e.operation==='event')){
      // Only Resolution wrappers reserve a proposed second output. Ordinary rows
      // cannot be treated as failed Resolution decryption/fallback.
      if(r.protocol_version===3){const nonce=decodeBase64Url(w.object.nonce),ciphertext=decodeBase64Url(w.object.ciphertext);let bytes:Uint8Array|undefined
       try{bytes=await step(decryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:e.project_id,entityId:e.entity_id,entityType:'note'},{...w.object,nonce,ciphertext}));const c=unframeContentNote(bytes);if(c.account_id!==s.canonicalUserId||c.device_id!==e.device_id||c.event.header.event_id!==e.event_id)fail('invalid_resolution');if(c.event.version===2&&c.event.resolution.strategy==='keep_both')reservedClones.set(e.event_id,c.event.resolution.retained_note.id)}finally{nonce.fill(0);ciphertext.fill(0);bytes?.fill(0)}
      }else{const r2=await step(this.original(s,r,amk,check));if(r2.resolution.resolution.strategy==='keep_both')reservedClones.set(e.event_id,r2.resolution.resolution.retained_note.id)}
     }
    }
    this.collision(s,resolution,v,futureChildren,reservedClones)
    const snapshot=await step(this.local.readSnapshot(s,h.project_id))
    if(!same(snapshot.project,v.projects.find((p:any)=>p.project_id===h.project_id))||!same(snapshot.notes,v.localNotes.filter((n:any)=>n.project_id===h.project_id)))fail('stale_inventory')
    if(!Number.isSafeInteger(snapshot.source_revision+1)||decision.strategy==='keep_both'&&snapshot.notes.length>=MAX_LOCAL_NOTES)fail('resource_limit')
    const working=parents.find(c=>c.event_id===head.linear_head_event_id)
    if(!working||!working.projection)fail('source_incompatible')
    const actual=snapshot.notes.find(n=>n.note_id===h.entity_id)
    if(!actual||!same(actual,working.projection))fail('source_incompatible')
    await step(this.local.withDecryptedSnapshot(s,snapshot.token,async source=>{
     const note=source.notes.find(n=>n.note.id===h.entity_id)
     if(!note||!same(wireNote(note.note),opened.get(working.event_id)!.note))fail('source_incompatible')
     const projectPayload={local_format:1,kind:'project',account_id:s.accountId,device_id:s.deviceId,project_id:h.project_id,source_revision:snapshot.source_revision+1,deleted_at:null,project:source.project,member_ids:[...snapshot.notes.map(n=>n.note_id),...(decision.strategy==='keep_both'?[decision.retained_note.id]:[])].sort()}
     try{const bytes=localCanonicalBytes(projectPayload);bytes.fill(0)}catch{fail('resource_limit')}
    }))
    await step(this.local.assertSnapshot(s,snapshot.token))
    if(!same(await step(this.load(s,current)),v))fail('stale_inventory')
    const status=Object.freeze({readOnly:true as const,commitAuthorized:false as const,ackAuthorized:false as const,parentCount:parents.length,strategy:decision.strategy}),token=Object.freeze({}) as ResolutionPlannerToken
    plans.set(token,{owner:this,scope:s,sequence,inventory:v,source:snapshot.token,current,resolution,group,parents:opened,status})
    return{token,status}
   }))
  }catch(e){if(e instanceof ResolutionPlannerError)throw e;if(e instanceof BrowserPersistenceError&&['closed','account_mismatch'].includes(e.code))fail('lifecycle_invalid');fail('invalid_resolution')}
 }
 /** Bounded diagnostics only. A future apply transaction must independently CAS all witnesses. */
 async inspect(token:ResolutionPlannerToken):Promise<ResolutionPlanStatus>{
  const p=plans.get(token);if(!p||p.owner!==this||!p.current())fail('lifecycle_invalid')
  try{await this.local.assertSnapshot(p.scope,p.source);if(!p.current())fail('lifecycle_invalid');const v=await this.load(p.scope,p.current);if(!p.current())fail('lifecycle_invalid');if(!same(v,p.inventory)){plans.delete(token);fail('stale_inventory')}return p.status}catch(e){plans.delete(token);if(e instanceof ResolutionPlannerError)throw e;fail('stale_inventory')}
 }
}
