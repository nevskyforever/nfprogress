import type {MetadataHandoffInspection} from './historicalMetadataDependency'
import type {AccountMasterKey} from '@/crypto'
import {canonical} from '@/cloud/projectMetadataCodec'
import {canonicalizeSyncTimestamp} from '@/cloud/syncTimestamp'
import {decodeBase64Url} from '@/api/base64url'
import {BrowserPersistenceError} from './persistence'
import {authenticateContinuationHistory,authenticateTerminalMetadataContinuations,authenticateMetadataHandoffContinuations,verifyContinuationSources,openHistoricalJson,sameResolutionValue as same} from './resolutionHistorical'
import {validateLocalProjectRecord,validateLocalNoteRecord,validateLocalProject,validatePersistedLocalNote,assertContentNoteRoute,localExact,MAX_LOCAL_NOTES,type LocalProjectPayload,type LocalNoteRecord} from './localAuthorityRecords'
import {openBrowserCanonicalObject} from './canonicalReaders'
import {openNoteTransport} from './noteTransport'
import type {ContentNoteEvent} from '@/cloud/contentNoteCodec'
import type {BrowserNoteCandidate} from './noteHistoryRecords'
import {validateBrowserOwnerHead} from './stageRecords'
import {validateBrowserMetadataHead} from './metadataApplyRecords'
import {validateBrowserSyncCursor} from './syncDurability'
import {readFutureInboxRecord} from './resolutionRecords'
import {prepareMetadataPrefix} from './metadataPrefixProof'
import {prepareStagePrefix} from './stageApply'
import {prepareStageOrderPrefix} from './stageOrderApply'

import type {BrowserSyncScope} from './syncDurability'
import type {ResolutionInventorySnapshot} from './resolutionPlanner'

type WitnessBlocker='no_resolution'|'unsupported_generation'|'unsupported_pending_family'|'missing_baseline'|'unsupported_local_source'|'missing_sequence'|'revision_order'|'causal_order'|'source_mismatch'|'unresolved_fork'|'resource_limit'
export class MixedSourceWitnessError extends Error {
 readonly name='MixedSourceWitnessError'
 constructor(readonly code:WitnessBlocker){super(`mixed_source_${code}`)}
}
function stop(code:WitnessBlocker):never{throw new MixedSourceWitnessError(code)}
const route=(n:Record<string,unknown>)=>[n.id,n.project_id,n.stage_id,n.source_type,n.source_map_id,n.source_node_id,n.content_format]

/** Internal pure validation over original complete inventory. Counts are NEVER
 * source authority; each owner must authenticate its own pre/post state and CAS. */
export function validateMixedSourceInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 return validateInventory(s,v,amk,current,false)
}
/** H-only source verification for historical reads/preservation. An authenticated
 * H fork may be retained with NO projection/revision. Never used by N/O/G/K;
 * H must still block source-changing apply while an unresolved group exists. */
export function validateMixedContinuationInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 return validateInventory(s,v,amk,current,true)
}
/** G-only source admission, not a family/prefix/ACK grant. Authenticated H forks
 * retain null projections; G must leave their incoming sequences unqualified. */
export function validateMixedPrefixInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 return validateInventory(s,v,amk,current,true)
}
async function validateInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean,preserveHConflicts:boolean){
 const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
 const h=await authenticateContinuationHistory(s,v,amk,current);check()
 return validateAuthenticatedInventory(s,v,amk,current,preserveHConflicts,h)
}
async function validateAuthenticatedInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean,preserveHConflicts:boolean,h:Awaited<ReturnType<typeof authenticateContinuationHistory>>){
 const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
 check()
 if(!h.resolutions.size)stop('no_resolution')
 if(h.resolutions.size!==1)stop('unsupported_generation') // Frozen K/F account boundary.
 const identities=new Map<string,string>()
 for(const a of h.dag.history){
  for(const id of [a.note_id,...(a.record_kind==='resolution'&&a.retained_note_id?[a.retained_note_id]:[])]){
   if(identities.has(id)&&identities.get(id)!==a.project_id)stop('causal_order')
   identities.set(id,a.project_id)
  }
 }
 const ordered=[...h.rows].sort((a,b)=>a.server_sequence-b.server_sequence)
 if(ordered.some((r,i)=>r.server_sequence!==i+1)||ordered.length!==v.cursor.pull_cursor)stop('missing_sequence')
 // Pending wire is authenticated too, but never promoted to an apply outcome.
 for(const row of h.rows)if(row.state==='received'){
  const wire=JSON.parse(row.wire_item),e=wire.event
  if(e.device_id===s.deviceId)stop('unsupported_local_source')
  if(e.entity_type==='note'&&['upsert','delete'].includes(e.operation))await openNoteTransport(s,amk,row.protocol_version,row.wire_item,'legacy')
  else{
   if(e.entity_type==='note'&&e.operation==='resolution')stop('unsupported_generation')
   if(!['note','project_metadata','stage','stage_order'].includes(e.entity_type))stop('unsupported_pending_family')
   const nonce=decodeBase64Url(wire.object.nonce),ciphertext=decodeBase64Url(wire.object.ciphertext)
   try{
    const decoded=await openBrowserCanonicalObject(amk,{accountId:s.canonicalUserId,projectId:e.project_id,entityId:e.entity_id,entityType:e.entity_type,eventId:e.event_id},{...wire.object,nonce,ciphertext})
    const content=e.entity_type==='note'?decoded as ContentNoteEvent:null
    if(content&&content.event.version!==1)stop('unsupported_generation')
    const header=content?content.event.header:(decoded as {header:{device_id:string;revision:number;updated_at:string}}).header
    if((content?content.device_id:(header as {device_id:string}).device_id)!==e.device_id||header.revision!==e.revision||canonicalizeSyncTimestamp(header.updated_at)!==canonicalizeSyncTimestamp(e.updated_at))throw new BrowserPersistenceError('corrupt_record')
    if(content&&content.event.version===1)assertContentNoteRoute(content.event.note)
   }finally{nonce.fill(0);ciphertext.fill(0)}
  }
  check()
 }
 // Force the actual family owners' historical crypto after FULL Note validation.
 // This is a dependency-only view, never an old-format Note/account authority.
 v.owners.forEach(o=>validateBrowserOwnerHead(o,s))
 const dependencies={...v,rows:h.rows.filter(r=>['project_metadata','stage','stage_order'].includes(JSON.parse(r.wire_item).event.entity_type))}
 const metadata=await prepareMetadataPrefix(s,dependencies,amk,current,true)
 await prepareStagePrefix(s,dependencies,amk,current,metadata,true)
 await prepareStageOrderPrefix(s,dependencies,amk,current,metadata,true);check()
 // Authenticate the complete encrypted source, including unrelated projects.
 const projects=new Map<string,LocalProjectPayload>(),notes=new Map<string,LocalNoteRecord[]>()
 for(const raw of v.projects){
  const row=validateLocalProjectRecord(raw,s),bytes=await openHistoricalJson(s,row.project_id,row.project_id,'project_metadata',row.envelope,amk,current)
  try{
   const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes),p:LocalProjectPayload=JSON.parse(text)
   if(canonical(p)!==text||!localExact(p,['local_format','kind','account_id','device_id','project_id','source_revision','deleted_at','project','member_ids'])||p.local_format!==1||p.kind!=='project'||p.account_id!==s.accountId||p.device_id!==s.deviceId||p.project_id!==row.project_id||p.source_revision!==row.source_revision||row.deleted||p.deleted_at!==null||!same(validateLocalProject(p.project),p.project)||p.project.id!==row.project_id||!Array.isArray(p.member_ids)||p.member_ids.length>MAX_LOCAL_NOTES||p.member_ids.some((id,i)=>typeof id!=='string'||i>0&&p.member_ids[i-1]!>=id))stop('source_mismatch')
   projects.set(row.project_id,p)
  }finally{bytes.fill(0)}
 }
 for(const raw of v.localNotes){
  const n=validateLocalNoteRecord(raw,s,(raw as LocalNoteRecord).project_id),p=projects.get(n.project_id)
  if(!p||n.source_revision>p.source_revision||identities.has(n.note_id)&&identities.get(n.note_id)!==n.project_id)stop('source_mismatch')
  const bytes=await openHistoricalJson(s,n.project_id,n.note_id,'note',n.envelope,amk,current)
  try{
   const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes),a=JSON.parse(text)
   if(canonical(a)!==text||!localExact(a,['local_format','kind','account_id','device_id','project_id','note_id','source_revision','source'])||a.local_format!==1||a.kind!=='note'||a.account_id!==s.accountId||a.device_id!==s.deviceId||a.project_id!==n.project_id||a.note_id!==n.note_id||a.source_revision!==n.source_revision)stop('source_mismatch')
   const source=validatePersistedLocalNote(a.source,n.project_id)
   if(source.note.id!==n.note_id||(source.state==='tombstone')!==n.deleted||(source.state==='live'?source.note.revision:source.revision)!==n.note_revision)stop('source_mismatch')
  }finally{bytes.fill(0)}
  notes.set(n.project_id,[...(notes.get(n.project_id)??[]),n]);check()
 }
 for(const [id,p] of projects)if(!same((notes.get(id)??[]).map(n=>n.note_id).sort(),p.member_ids))stop('source_mismatch')

 let baselineNotes=0,hTransitions=0,ordinaryTransitions=0
 for(const root of h.resolutions.values()){
  const r=root.record,R0=root.project.source_revision,S0=r.server_sequence,p=projects.get(r.project_id)
  if(!p||!same(p.project,root.project.project))stop('source_mismatch')
  if(v.intents.some(i=>(i as {project_id:string}).project_id===r.project_id))stop('unsupported_local_source')
  const candidates=[...h.dag.events.values()].filter((c):c is BrowserNoteCandidate=>c.record_kind==='candidate'&&c.project_id===r.project_id)
  if(candidates.some(c=>c.record_version===3))stop('unsupported_local_source')
  const rowFor=(c:BrowserNoteCandidate)=>h.rows.find(row=>row.event_id===c.event_id)
  const applied=(c:BrowserNoteCandidate)=>{
   const row=rowFor(c)
   return row?.state==='note_proven'&&row.note_proof.outcome==='applied'||row?.state==='content_note_proven'
  }
  const outputs=[r.note_id,...(r.retained_note_id?[r.retained_note_id]:[])]
  const expected=new Map<string,LocalNoteRecord>(),last=new Map<string,string>()
  const revisions=new Set<number>()
  for(const c of candidates){
   if(c.bootstrap_id!==r.bootstrap_id)stop('causal_order')
   if(c.origin==='peer'&&c.projection){
    if(!applied(c)||revisions.has(c.projection.source_revision))stop('revision_order')
    revisions.add(c.projection.source_revision)
    const row=rowFor(c)!
    if(row.server_sequence<S0?c.projection.source_revision>=R0:c.projection.source_revision<=R0)stop('revision_order')
   }
  }
  for(const id of root.project.member_ids){
   if(outputs.includes(id)){
    const n=root.notes.find(n=>n.note_id===id);if(!n)stop('missing_baseline')
    expected.set(id,n);last.set(id,r.event_id);continue
   }
   // Reconstruct the historical applied path, not today's mutable head/source.
   const prior=candidates.filter(c=>c.note_id===id&&(rowFor(c)?.server_sequence??Number.POSITIVE_INFINITY)<S0).sort((a,b)=>rowFor(a)!.server_sequence-rowFor(b)!.server_sequence)
   let previous:BrowserNoteCandidate|undefined
   for(const c of prior){
    if(c.origin!=='peer'||!applied(c)||!c.projection||c.projection.source_revision>=R0||c.projection.note_revision!==0)stop('missing_baseline')
    const value=h.opened.get(c.event_id)!
    if(previous?c.header.parent_event_id!==previous.event_id||c.header.revision!==previous.header.revision+1||c.projection.source_revision<=previous.projection!.source_revision:! (c.header.parent_event_id===null&&c.header.revision===1&&value.mutation==='create'))stop('causal_order')
    if(previous){const before=h.opened.get(previous.event_id)!;if(!same(route(before.note as unknown as Record<string,unknown>),route(value.note as unknown as Record<string,unknown>))||before.mutation==='delete'&&value.mutation!=='delete')stop('causal_order')}
    previous=c
   }
   if(!previous?.projection)stop('missing_baseline')
   expected.set(id,previous.projection);last.set(id,previous.event_id)
  }
  baselineNotes+=expected.size
  const reaches=(id:string,note:string)=>{
   const seen=new Set<string>()
   while(!seen.has(id)){
    seen.add(id);const node=h.dag.events.get(id)
    if(node?.record_kind==='resolution')return node.event_id===r.event_id&&outputs.includes(note)
    if(!node||node.project_id!==r.project_id||node.bootstrap_id!==r.bootstrap_id||node.note_id!==note||!node.header.parent_event_id)return false
    id=node.header.parent_event_id
   }
   return false
  }
  // Preserve H's per-role DAG/head/causal/no-resurrection checks independently
  // of the generalized project membership/revision fold. No Head1 substitution.
  for(const id of outputs){
   const head=h.dag.history.find(a=>a.record_kind==='head'&&a.project_id===r.project_id&&a.note_id===id)
   const following=candidates.filter(c=>c.note_id===id&&reaches(c.event_id,id))
   if(!head||head.record_kind!=='head'||head.record_version!==2||!reaches(head.linear_head_event_id,id)||head.head_revision!==(id===r.note_id?root.headBefore.head_revision+1:1)+following.length)stop('causal_order')
   for(const c of following){
    const parent=h.dag.events.get(c.header.parent_event_id!),row=rowFor(c),parentRow=h.rows.find(a=>a.event_id===c.header.parent_event_id)
    if(c.origin!=='peer'||!parent||!row||!parentRow||row.server_sequence<=parentRow.server_sequence||c.header.revision!==parent.header.revision+1)stop('causal_order')
    const before=parent.record_kind==='candidate'?h.opened.get(parent.event_id)!.note:id===r.note_id?root.payload.result.note:root.payload.resolution.strategy==='keep_both'?root.payload.resolution.retained_note:undefined
    const value=h.opened.get(c.event_id)!
    if(!before||!same(route(before as unknown as Record<string,unknown>),route(value.note as unknown as Record<string,unknown>))||'deleted_at'in before&&value.mutation!=='delete')stop('causal_order')
   }
  }
  const suffix=candidates.filter(c=>(rowFor(c)?.server_sequence??0)>S0&&applied(c))
  if(suffix.some(c=>c.origin!=='peer'||!c.projection))stop('unsupported_local_source')
  suffix.sort((a,b)=>a.projection!.source_revision-b.projection!.source_revision)
  let previousSequence=S0
  for(let i=0;i<suffix.length;i++){
   const c=suffix[i]!,row=rowFor(c)!,projection=c.projection!,value=h.opened.get(c.event_id)!,id=c.note_id,isH=outputs.includes(id),old=expected.get(id)
   if(projection.source_revision!==R0+i+1||projection.note_revision!==0||row.server_sequence<=previousSequence)stop('revision_order')
   previousSequence=row.server_sequence
   if(isH&&!reaches(c.event_id,id))stop('causal_order')
   if(!old){
    if(isH||value.mutation!=='create'||c.header.revision!==1||c.header.parent_event_id!==null||candidates.some(a=>a.note_id===id&&a.event_id!==c.event_id&&(rowFor(a)?.server_sequence??0)<row.server_sequence))stop('causal_order')
   }else{
    const parent=last.get(id)!,node=h.dag.events.get(parent)
    if(value.mutation==='create'||c.header.parent_event_id!==parent||!node||c.header.revision!==node.header.revision+1||old.deleted&&value.mutation!=='delete')stop('causal_order')
    const before=node.record_kind==='candidate'?h.opened.get(parent)!.note:id===r.note_id?root.payload.result.note:root.payload.resolution.strategy==='keep_both'?root.payload.resolution.retained_note:undefined
    if(!before||!same(route(before as unknown as Record<string,unknown>),route(value.note as unknown as Record<string,unknown>)))stop('causal_order')
   }
   expected.set(id,projection);last.set(id,c.event_id)
   if(isH)hTransitions++;else ordinaryTransitions++
  }
  const actual=notes.get(r.project_id)??[]
  if(p.source_revision!==R0+suffix.length||!same(p.member_ids,[...expected.keys()].sort())||actual.length!==expected.size||actual.some(n=>!same(n,expected.get(n.note_id))))stop('source_mismatch')
  for(const [id,event] of last){
   const head=h.dag.history.find(a=>a.record_kind==='head'&&a.project_id===r.project_id&&a.note_id===id)
   if(!head||head.record_kind!=='head'||head.linear_head_event_id!==event)stop('causal_order')
   if(!outputs.includes(id)){
    const own=candidates.filter(c=>c.note_id===id)
    if(head.record_version!==1||head.tip_event_ids.length!==1||head.tip_event_ids[0]!==event||head.head_revision!==own.length||own.some(c=>c.origin!=='peer'))stop('unsupported_local_source')
   }
  }
 }
 for(const {group,effective} of h.groups)if(effective==='open'){
  if(!preserveHConflicts)stop('unresolved_fork')
  const root=[...h.resolutions.values()].find(r=>r.record.project_id===group.project_id&&r.record.bootstrap_id===group.bootstrap_id)
  if(!root||![root.record.note_id,root.record.retained_note_id].includes(group.note_id)||group.members.some(m=>m.source==='local_unsealed'))stop('unresolved_fork')
  // Only H's role-bound post-Resolution fork is eligible for preservation.
  // Full historical authentication already joins every member/outcome/tip; the
  // exact applied-source fold above excludes every conflict-only projection.
  let id:string|null=group.common_parent_event_id
  const seen=new Set<string>()
  while(id&&!seen.has(id)){
   seen.add(id);const node=h.dag.events.get(id)
   if(node?.record_kind==='resolution'){if(node.event_id!==root.record.event_id)stop('unresolved_fork');break}
   if(!node||node.project_id!==group.project_id||node.note_id!==group.note_id||node.bootstrap_id!==group.bootstrap_id)stop('unresolved_fork')
   id=node.header.parent_event_id
  }
  if(!id||h.dag.events.get(id)?.record_kind!=='resolution')stop('unresolved_fork')
 }
 check();return{projects:h.resolutions.size,baselineNotes,hTransitions,ordinaryTransitions,pendingEvents:h.rows.filter(r=>r.state==='received').length}
}

/** Internal .14 read-only composition. No owner calls this and no source grant is
 * returned. Historical versus mixed source ordering is selected from evidence,
 * never by catching an authentication failure. */
async function authenticateTerminalMetadataSourceState(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 const h=await authenticateTerminalMetadataContinuations(s,v,amk,current)
 return authenticateMetadataSourceState(s,v,amk,current,h)
}
async function authenticateMetadataSourceState(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean,h:Awaited<ReturnType<typeof authenticateContinuationHistory>>){
 const mixed=[...h.resolutions.values()].some(root=>[...h.dag.events.values()].some(c=>
  c.record_kind==='candidate'&&c.project_id===root.record.project_id&&![root.record.note_id,root.record.retained_note_id].includes(c.note_id)&&
  ((h.rows.find(r=>r.event_id===c.event_id)?.server_sequence??0)>root.record.server_sequence||(c.projection?.source_revision??0)>root.project.source_revision)))
 if(mixed)await validateAuthenticatedInventory(s,v,amk,current,false,h)
 else{
  await verifyContinuationSources(s,v,h,amk,current)
  for(const raw of v.localNotes){
   const n=raw as LocalNoteRecord
   if([...h.resolutions.values()].some(r=>r.record.project_id===n.project_id&&[r.record.note_id,r.record.retained_note_id].includes(n.note_id)))continue
   const head=h.dag.history.find(a=>a.record_kind==='head'&&a.project_id===n.project_id&&a.note_id===n.note_id)
   const c=head?.record_kind==='head'?h.dag.events.get(head.linear_head_event_id):undefined
   if(!c||c.record_kind!=='candidate'||!same(c.projection,raw))stop('source_mismatch')
  }
 }
 if(!current())throw new BrowserPersistenceError('closed')
 return{h,mixed}
}

/** Isolated .17 verifier, no write grant or public reader mode. */
export async function authenticatePrivateMetadataSource(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean,mode:MetadataHandoffInspection):Promise<void>{
 const cursor=validateBrowserSyncCursor(v.checkpoints[0],s)
 if(v.checkpoints.length!==1||!same(cursor,v.cursor))stop('source_mismatch')
 const h=await authenticateMetadataHandoffContinuations(s,v,amk,current,mode)
 if(h.resolutions.size!==1)stop('unsupported_generation')
 await authenticateMetadataSourceState(s,v,amk,current,h)
}

/** Internal .18 authentication, never a .15 diagnostic or a caller-supplied
 * certificate. The cursor owner keeps these freshly joined maps lexically private. */
export async function authenticatePrivateMetadataPrefixInventory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 const cursor=validateBrowserSyncCursor(v.checkpoints[0],s)
 if(v.checkpoints.length!==1||!same(cursor,v.cursor))stop('source_mismatch')
 const rows=v.rows.map(r=>readFutureInboxRecord(r,s)).sort((a,b)=>a.server_sequence-b.server_sequence)
 const pending=rows.filter(r=>r.state==='received'&&JSON.parse(r.wire_item).event.entity_type==='project_metadata')
 if(pending.length>1)stop('unsupported_pending_family')
 const mode:MetadataHandoffInspection=pending.length?{kind:'pending',sequence:pending[0]!.server_sequence}:{kind:'durable'}
 const h=await authenticateMetadataHandoffContinuations(s,v,amk,current,mode)
 if(h.resolutions.size!==1)stop('unsupported_generation')
 await authenticateMetadataSourceState(s,v,amk,current,h)
 const root=[...h.resolutions.values()][0]!.record,qualified=new Map<number,'legacy'|'content'|'resolution'|'metadata'>()
 const metadata=validateBrowserMetadataHead(v.owners.find(o=>(o as {owner_kind:string;owner_id:string}).owner_kind==='project_metadata'&&(o as {owner_id:string}).owner_id===root.project_id),s)
 for(const row of rows){
  const e=JSON.parse(row.wire_item).event
  if(e.entity_type==='project_metadata'){
   if(row.state==='received')continue // Pending Metadata is authenticated, never qualified.
   const owner=validateBrowserMetadataHead(v.owners.find(o=>(o as {owner_kind:string;owner_id:string}).owner_kind==='project_metadata'&&(o as {owner_id:string}).owner_id===e.project_id),s)
   const proof=owner.history.find(p=>p.event_id===row.event_id)
   if(row.state!=='applied'||!proof||proof.server_sequence!==row.server_sequence||!same(proof,row.applied_proof))stop('source_mismatch')
   qualified.set(row.server_sequence,'metadata');continue
  }
  if(e.entity_type!=='note'||e.project_id!==root.project_id)stop('unsupported_pending_family')
  if(row.state==='note_resolution_proven'){
   if(row.event_id!==root.event_id||root.server_sequence!==row.server_sequence||root.wire_item!==row.wire_item||root.record_digest!==row.resolution_proof.resolution_digest)stop('source_mismatch')
   qualified.set(row.server_sequence,'resolution');continue
  }
  if(row.state==='received')continue
  if(!['note_proven','content_note_proven','note_conflict_preserved','content_note_conflict_preserved'].includes(row.state))stop('unsupported_pending_family')
  const candidate=h.dag.events.get(row.event_id)
  if(!candidate||candidate.record_kind!=='candidate'||!h.opened.has(row.event_id)||candidate.record_version===3||candidate.record_version===2&&candidate.server_sequence!==row.server_sequence)stop('source_mismatch')
  if(row.state==='note_conflict_preserved'||row.state==='content_note_conflict_preserved'){
   const proof=row.state==='note_conflict_preserved'?row.note_conflict_proof:row.content_note_conflict_proof
   const group=h.groups.find(g=>g.group.project_id===candidate.project_id&&g.group.note_id===candidate.note_id&&g.group.group_id===proof.group_id)
   if(!group||group.effective!=='resolved')stop('unresolved_fork')
  }
  qualified.set(row.server_sequence,candidate.record_version===2?'content':'legacy')
 }
 if(!current())throw new BrowserPersistenceError('closed')
 return{qualified,root:{project_id:root.project_id,note_id:root.note_id,retained_note_id:root.retained_note_id},metadataDeleted:metadata.history.find(p=>p.event_id===metadata.tip_event_ids[0])!.operation==='delete'}
}

/** Existing .14 diagnostic only; authenticated maps stay module-private. */
export async function inspectTerminalMetadataSourceHistory(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 const {h,mixed}=await authenticateTerminalMetadataSourceState(s,v,amk,current)
 return{resolutions:h.resolutions.size,candidates:h.opened.size,pendingEvents:h.rows.filter(r=>r.state==='received').length,firstPendingSequence:h.rows.filter(r=>r.state==='received').map(r=>r.server_sequence).sort((a,b)=>a-b)[0]??null,sourceCohort:mixed?'mixed' as const:'historical' as const}
}


type HistoricalPrefixFamily='legacy'|'content'|'resolution'|'metadata'
type HistoricalPrefixBlocker='missing_sequence'|'duplicate_sequence'|'unsupported_family'|'unqualified_proven_sequence'|'invalid_history'
export class HistoricalPrefixQualificationError extends Error {
 readonly name='HistoricalPrefixQualificationError'
 constructor(readonly code:HistoricalPrefixBlocker,readonly sequence:number|null=null){super(`historical_prefix_${code}`)}
}
function prefixReject(code:HistoricalPrefixBlocker,sequence:number|null=null):never{throw new HistoricalPrefixQualificationError(code,sequence)}

/** Isolated .15 read-only calculation. Does NOT call Q, obtain a family grant or
 * expose the authenticated F/H maps. Every family is joined to its own outcome. */
export async function inspectTerminalMetadataHistoricalPrefix(s:BrowserSyncScope,v:ResolutionInventorySnapshot,amk:AccountMasterKey,current:()=>boolean){
 const cursor=validateBrowserSyncCursor(v.checkpoints[0],s)
 if(!same(cursor,v.cursor))prefixReject('invalid_history')
 const rows=v.rows.map(r=>readFutureInboxRecord(r,s)).sort((a,b)=>a.server_sequence-b.server_sequence)
 const seen=new Set<number>()
 for(const row of rows){if(seen.has(row.server_sequence))prefixReject('duplicate_sequence',row.server_sequence);seen.add(row.server_sequence)}
 const gap=rows.findIndex((row,i)=>row.server_sequence!==i+1)
 if(gap>=0||rows.length!==cursor.pull_cursor)prefixReject('missing_sequence',gap>=0?gap+1:rows.length+1)
 // Unsupported material is never hidden to manufacture a partial account view.
 // Errors identify the rejected material, not an authenticated partial prefix.
 for(const row of rows)if(!['note','project_metadata'].includes(JSON.parse(row.wire_item).event.entity_type))prefixReject('unsupported_family',row.server_sequence)
 const {h,mixed}=await authenticateTerminalMetadataSourceState(s,v,amk,current)
 if(h.resolutions.size!==1)prefixReject('invalid_history') // This path is ONLY the accepted one-F cohort.
 const qualified=new Map<number,HistoricalPrefixFamily>(),projects=new Set([...h.resolutions.values()].map(root=>root.record.project_id))
 for(const row of h.rows){
  const e=JSON.parse(row.wire_item).event
  if(e.entity_type==='project_metadata'){
   const owner=v.owners.find(o=>(o as {owner_kind:string;owner_id:string}).owner_kind==='project_metadata'&&(o as {owner_id:string}).owner_id===e.project_id)
   const head=validateBrowserMetadataHead(owner,s),proof=head.history.find(p=>p.event_id===row.event_id)
   // Full .13 crypto already reproduced this exact owner proof from original AEAD.
   // Neither a delete nor its sequence grants any Note/source qualification.
   if(row.state!=='applied'||!proof||proof.server_sequence!==row.server_sequence||!same(proof,row.applied_proof))prefixReject('invalid_history',row.server_sequence)
   qualified.set(row.server_sequence,'metadata');continue
  }
  if(!projects.has(e.project_id))prefixReject('unsupported_family',row.server_sequence)
  if(row.state==='note_resolution_proven'){
   const root=h.resolutions.get(row.event_id)
   if(!root||root.record.server_sequence!==row.server_sequence||root.record.wire_item!==row.wire_item||root.record.record_digest!==row.resolution_proof.resolution_digest)prefixReject('invalid_history',row.server_sequence)
   qualified.set(row.server_sequence,'resolution');continue
  }
  if(!['note_proven','content_note_proven','note_conflict_preserved','content_note_conflict_preserved'].includes(row.state))continue
  const candidate=h.dag.events.get(row.event_id)
  if(!candidate||candidate.record_kind!=='candidate'||!h.opened.has(row.event_id)||candidate.record_version===2&&candidate.server_sequence!==row.server_sequence)prefixReject('invalid_history',row.server_sequence)
  if(row.state==='note_conflict_preserved'||row.state==='content_note_conflict_preserved'){
   const proof=row.state==='note_conflict_preserved'?row.note_conflict_proof:row.content_note_conflict_proof
   const group=h.groups.find(g=>g.group.project_id===candidate.project_id&&g.group.note_id===candidate.note_id&&g.group.group_id===proof.group_id)
   if(!group||group.effective!=='resolved')prefixReject('invalid_history',row.server_sequence)
  }
  if(candidate.record_version===3)prefixReject('invalid_history',row.server_sequence)
  qualified.set(row.server_sequence,candidate.record_version===2?'content':'legacy')
 }
 const counts:Record<HistoricalPrefixFamily,number>={legacy:0,content:0,resolution:0,metadata:0}
 let candidate=cursor.proven_prefix,first:number|null=null,blocker:'received'|'unproven_family'|null=null
 // Independently verify the complete already-proven interval as well as the new
 // candidate. The durable cursor is never accepted as evidence for a sequence.
 for(const row of rows){
  const family=qualified.get(row.server_sequence)
  if(!family){
   if(row.server_sequence<=cursor.proven_prefix)prefixReject('unqualified_proven_sequence',row.server_sequence)
   first=row.server_sequence;blocker=row.state==='received'?'received':'unproven_family';break
  }
  counts[family]++;candidate=row.server_sequence
 }
 if(!current())throw new BrowserPersistenceError('closed')
 return Object.freeze({readOnly:true as const,current_proven_prefix:cursor.proven_prefix,candidate_historical_prefix:candidate,pull_cursor:cursor.pull_cursor,first_blocking_sequence:first,blocker,counts:Object.freeze(counts),sourceCohort:mixed?'mixed' as const:'historical' as const,cursorCommitAuthorized:false as const,sourceAuthorized:false as const,firstApplyAllowed:false as const,commitAuthorized:false as const,ackAuthorized:false as const,declarationAllowed:false as const,ready:false as const})
}
