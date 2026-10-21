import type {NormalUserAuthRuntime} from '@/auth/userAuth'
import type {AuthoritativeAccountBinding} from '@/auth/accountBinding'
import type {RuntimeKeyContext} from '@/auth/keyContext'
import type {AccountMasterKey} from '@/crypto'
import {canonical,type ProjectMetadataEvent} from '@/cloud/projectMetadataCodec'
import {unframeContentNote,type ContentNoteEvent} from '@/cloud/contentNoteCodec'
import {decodeNoteSyncResolutionV2,type NoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {decodeBase64Url} from '@/api/base64url'
import {BrowserPersistenceError} from './persistence'
import {currentBrowserDevice,type VerifiedBrowserDevice} from './deviceRegistration'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {snapshotBrowserSyncScope,validateBrowserStoredUploadPair,type BrowserSyncScope} from './syncDurability'
import type {BrowserSyncTransaction} from './syncDurability'
import {inspectResolutionDag} from './resolutionDag'
import {resolutionIdentity,readFutureInboxRecord,readFutureHistoryRecord,resolutionSame as same,MAX_RESOLUTION_EVIDENCE_BYTES,boundResolutionJson,type BrowserResolution4} from './resolutionRecords'
import {openHistoricalJson,MAX_CONTINUATION_MATERIAL_BYTES} from './resolutionHistorical'
import {resolutionBytesDigest} from './resolutionAuthentication'
import {openHistoryCandidate} from './noteHistory'
import {openNoteTransport} from './noteTransport'
import {noteProofDigest,noteOutcomeDigest,verifyStoredNoteProof} from './legacyNoteApply'
import {contentProofFor} from './contentNoteProof'
import {contentConflictProofFor} from './contentNoteConflictProof'
import {metadataProofFor} from './importedMetadataApply'
import {validateBrowserMetadataHead} from './metadataApplyRecords'
import {validateBrowserProjectBinding} from './projectBindings'
import {validateBrowserOwnerHead} from './stageRecords'
import {openBrowserCanonicalObject} from './canonicalReaders'
import {validateLocalProjectRecord,validateLocalNoteRecord,validatePersistedLocalNote,validateLocalProject,localExact,MAX_LOCAL_NOTES,type LocalProjectRecord,type LocalNoteRecord,type LocalProjectPayload,type LocalNotePayload} from './localAuthorityRecords'
import type {BrowserNoteConflictGroup,BrowserNoteHead} from './noteHistoryRecords'

type Reason='invalid_evidence'|'missing_sequence'|'unsupported_generation'|'unsupported_local'|'unsupported_stage'|'unsupported_family'|'unresolved_fork'|'not_applied'|'not_content'|'missing_metadata'|'unproven_interval'|'not_terminal_delete'|'outside_interval'|'resource_limit'
class Rejected extends Error {constructor(readonly reason:Reason){super(reason)}}
function reject(reason:Reason='invalid_evidence'):never{throw new Rejected(reason)}
const digest=async(value:object,field:string)=>{const body={...value} as Record<string,unknown>;delete body[field];return noteProofDigest(body)}
type Row=ReturnType<typeof readFutureInboxRecord>
type Dag=ReturnType<typeof inspectResolutionDag>
interface FEnvelope {
 resolution_format:1;kind:'resolution_apply';identity:ReturnType<typeof resolutionIdentity>
 authenticated_payload:{wire_frame_digest:string;wrapper_payload_digest:string|null;resolution_payload_digest:string}
 parents:{event_id:string;revision:number;operation:string;history_digest:string;inbox_digest:string;publication_source:string;server_sequence:number;local_mutation_generation:null;frozen_version_digest:null;snapshot_digest:string}[]
 group_snapshot:BrowserNoteConflictGroup;head_before:BrowserNoteHead
 source_before:{project:LocalProjectRecord;notes:LocalNoteRecord[]};source_after:{project:LocalProjectRecord;notes:LocalNoteRecord[]}
}
async function json(s:BrowserSyncScope,project:string,id:string,type:'note'|'project_metadata',envelope:LocalNoteRecord['envelope'],amk:AccountMasterKey,current:()=>boolean){
 const bytes=await openHistoricalJson(s,project,id,type,envelope,amk,current)
 try{if(bytes.length>MAX_CONTINUATION_MATERIAL_BYTES)reject('resource_limit');const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes),value=JSON.parse(text);boundResolutionJson(value,MAX_RESOLUTION_EVIDENCE_BYTES);if(canonical(value)!==text)reject();return value as unknown}finally{bytes.fill(0)}
}
async function project(s:BrowserSyncScope,raw:unknown,amk:AccountMasterKey,current:()=>boolean){
 const r=validateLocalProjectRecord(raw,s),p=await json(s,r.project_id,r.project_id,'project_metadata',r.envelope,amk,current) as LocalProjectPayload
 if(!localExact(p,['local_format','kind','account_id','device_id','project_id','source_revision','deleted_at','project','member_ids'])||p.local_format!==1||p.kind!=='project'||p.account_id!==s.accountId||p.device_id!==s.deviceId||p.project_id!==r.project_id||p.source_revision!==r.source_revision||r.deleted||p.deleted_at!==null||!same(validateLocalProject(p.project),p.project)||p.project.id!==r.project_id||!Array.isArray(p.member_ids)||p.member_ids.length>MAX_LOCAL_NOTES||p.member_ids.some((id,i)=>typeof id!=='string'||!id||i>0&&p.member_ids[i-1]!>=id))reject()
 return p
}
async function note(s:BrowserSyncScope,raw:LocalNoteRecord,amk:AccountMasterKey,current:()=>boolean){
 const r=validateLocalNoteRecord(raw,s,raw.project_id),p=await json(s,r.project_id,r.note_id,'note',r.envelope,amk,current) as LocalNotePayload
 if(!localExact(p,['local_format','kind','account_id','device_id','project_id','note_id','source_revision','source'])||p.local_format!==1||p.kind!=='note'||p.account_id!==s.accountId||p.device_id!==s.deviceId||p.project_id!==r.project_id||p.note_id!==r.note_id||p.source_revision!==r.source_revision)reject()
 const source=validatePersistedLocalNote(p.source,r.project_id)
 if(source.note.id!==r.note_id||r.deleted!==(source.state==='tombstone')||r.note_revision!==(source.state==='live'?source.note.revision:source.revision))reject()
 return source
}
const wireNote=(n:object)=>{const v={...n} as Record<string,unknown>;delete v.revision;return v}
async function openCanonical(s:BrowserSyncScope,row:Row,amk:AccountMasterKey){
 const w=JSON.parse(row.wire_item),e=w.event,nonce=decodeBase64Url(w.object.nonce),ciphertext=decodeBase64Url(w.object.ciphertext)
 try{return await openBrowserCanonicalObject(amk,{accountId:s.canonicalUserId,projectId:e.project_id,entityId:e.entity_id,entityType:e.entity_type,eventId:e.event_id},{...w.object,nonce,ciphertext}) as ProjectMetadataEvent|ContentNoteEvent}finally{nonce.fill(0);ciphertext.fill(0)}
}
/** Original accepted F evidence only. No live prerequisite, source witness or
 * new Resolution qualification. The dependency component is checked separately. */
async function resolution(s:BrowserSyncScope,r:BrowserResolution4,rows:Row[],dag:Dag,opened:Map<string,Awaited<ReturnType<typeof openHistoryCandidate>>>,amk:AccountMasterKey,current:()=>boolean){
 if(r.source_device_id===s.deviceId||await digest(r,'record_digest')!==r.record_digest)reject()
 const row=rows.find(a=>a.event_id===r.event_id)
 if(!row||row.state!=='note_resolution_proven'||row.server_sequence!==r.server_sequence||row.wire_item!==r.wire_item)reject()
 const wire=JSON.parse(row.wire_item),bytes=await openHistoricalJson(s,r.project_id,r.note_id,'note',wire.object,amk,current)
 let payload:NoteSyncResolutionV2,content:ContentNoteEvent|undefined,frameDigest:string
 try{frameDigest=await resolutionBytesDigest(bytes);if(r.protocol_version===3){content=unframeContentNote(bytes);if(content.event.version!==2||content.account_id!==s.canonicalUserId||content.device_id!==r.source_device_id)reject();payload=content.event}else payload=decodeNoteSyncResolutionV2(bytes)}finally{bytes.fill(0)}
 if(await noteProofDigest({protocol_version:r.protocol_version,item:wire})!==r.wire_digest||await noteProofDigest(payload)!==r.payload_digest||!same(payload.header,r.header)||payload.resolution.conflict_group_id!==r.remote_group_id||payload.resolution.conflict_generation!==r.remote_generation||payload.resolution.strategy!==r.strategy||payload.result.operation!==r.result_operation||(payload.resolution.strategy==='keep_both'?payload.resolution.retained_note.id:null)!==r.retained_note_id)reject()
 const e=await json(s,r.project_id,r.note_id,'note',r.evidence_envelope,amk,current) as FEnvelope
 if(!localExact(e,['resolution_format','kind','identity','authenticated_payload','parents','group_snapshot','head_before','source_before','source_after'])||e.resolution_format!==1||e.kind!=='resolution_apply'||!same(e.identity,resolutionIdentity(r))||!same(e.authenticated_payload,{wire_frame_digest:frameDigest,wrapper_payload_digest:content?await noteProofDigest(content):null,resolution_payload_digest:r.payload_digest}))reject()
 const g=readFutureHistoryRecord(e.group_snapshot,s),h=readFutureHistoryRecord(e.head_before,s)
 if(g.record_kind!=='group'||h.record_kind!=='head'||g.project_id!==r.project_id||g.note_id!==r.note_id||g.bootstrap_id!==r.bootstrap_id||g.group_id!==r.local_group_id||g.conflict_generation!==r.local_generation||await noteProofDigest(g)!==r.group_digest||!dag.history.some(a=>same(a,g))||!same(g.tip_event_ids,r.parent_event_ids)||h.project_id!==r.project_id||h.note_id!==r.note_id||h.bootstrap_id!==r.bootstrap_id||!same(h.tip_event_ids,r.parent_event_ids)||!Array.isArray(e.parents)||e.parents.length!==r.parent_event_ids.length)reject()
 for(const [i,p] of e.parents.entries()){
  const c=dag.events.get(p.event_id),member=g.members.find(m=>m.event_id===p.event_id),incoming=rows.find(a=>a.event_id===p.event_id),value=opened.get(p.event_id)
  if(!localExact(p,['event_id','revision','operation','history_digest','inbox_digest','publication_source','server_sequence','local_mutation_generation','frozen_version_digest','snapshot_digest'])||p.event_id!==r.parent_event_ids[i]||!c||c.record_kind!=='candidate'||!member||!incoming||!value||c.project_id!==r.project_id||c.note_id!==r.note_id||c.bootstrap_id!==r.bootstrap_id||c.header.parent_event_id!==g.common_parent_event_id||c.header.revision!==g.tip_revision||p.revision!==c.header.revision||p.operation!==c.header.operation||p.history_digest!==c.record_digest||p.publication_source!==member.source||p.server_sequence!==incoming.server_sequence||p.server_sequence!==member.server_sequence||incoming.server_sequence>=r.server_sequence||p.local_mutation_generation!==null||p.frozen_version_digest!==null||await noteProofDigest(incoming)!==p.inbox_digest||await noteProofDigest(value.note)!==p.snapshot_digest||member.source==='remote_applied'&&!['content_note_proven','note_proven'].includes(incoming.state)||member.source==='remote'&&!['content_note_conflict_preserved','note_conflict_preserved'].includes(incoming.state))reject()
 }
 const decision=payload.resolution,selected='selected_event_id'in decision?opened.get(decision.selected_event_id):undefined
 if(['choose_version','keep_both'].includes(decision.strategy)&&(!selected||selected.header.operation!==payload.result.operation||!same(selected.note,payload.result.note)))reject()
 if(decision.strategy==='keep_both'){
  const retained=opened.get(decision.retained_event_id)
  if(!retained||r.parent_event_ids.some(id=>opened.get(id)?.mutation==='delete')||!same({...retained.note,id:decision.retained_note.id,created_at:decision.retained_note.created_at,updated_at:decision.retained_note.updated_at},decision.retained_note))reject()
 }
 for(const source of [e.source_before,e.source_after])if(!localExact(source,['project','notes'])||!Array.isArray(source.notes)||source.notes.some((n,i)=>i>0&&source.notes[i-1]!.note_id>=n.note_id))reject()
 const before=await project(s,e.source_before.project,amk,current),after=await project(s,e.source_after.project,amk,current)
 if(before.project_id!==r.project_id||after.project_id!==r.project_id||after.source_revision!==before.source_revision+1||!same(before.project,after.project)||!same(after.member_ids,[...before.member_ids,...(r.retained_note_id?[r.retained_note_id]:[])].sort())||r.retained_note_id!==null&&before.member_ids.includes(r.retained_note_id)||e.source_before.notes.length!==1||e.source_before.notes[0]?.note_id!==r.note_id||e.source_after.notes.length!==(r.retained_note_id?2:1))reject()
 const old=e.source_before.notes[0]!,working=r.parent_event_ids.map(id=>dag.events.get(id)).find(c=>c?.record_kind==='candidate'&&same(c.projection,old))
 if(!working||working.record_kind!=='candidate'||!same(wireNote((await note(s,old,amk,current)).note),opened.get(working.event_id)!.note)||!before.member_ids.includes(old.note_id)||old.source_revision>before.source_revision||h.linear_head_event_id!==g.members.find(m=>m.source!=='remote')?.event_id)reject()
 for(const n of e.source_after.notes){
  const expected=n.note_id===r.note_id?payload.result.note:decision.strategy==='keep_both'&&n.note_id===r.retained_note_id?decision.retained_note:undefined
  if(!expected||n.source_revision!==after.source_revision||n.note_revision!==0||!same(wireNote((await note(s,n,amk,current)).note),expected))reject()
 }
 const t=dag.history.find(a=>a.record_kind==='group_transition'&&a.project_id===r.project_id&&a.note_id===r.note_id&&a.group_id===r.local_group_id)
 if(!t||t.record_kind!=='group_transition'||t.bootstrap_id!==r.bootstrap_id||t.from_generation!==r.local_generation||t.from_digest!==r.group_digest||t.resolution_event_id!==r.event_id||t.resolution_digest!==r.record_digest||!same(t.resolved_parent_ids,r.parent_event_ids)||await digest(t,'record_digest')!==t.record_digest)reject()
 const p=row.resolution_proof
 if(p.bootstrap_id!==r.bootstrap_id||p.resolution_digest!==r.record_digest||p.transition_digest!==t.record_digest||p.wire_digest!==r.wire_digest||p.payload_digest!==r.payload_digest||p.dependency_digest!==r.dependency_digest||!same(p.header,r.header)||!same(p.output_digests,{original:await noteProofDigest(e.source_after.notes.find(n=>n.note_id===r.note_id)),retained:r.retained_note_id?await noteProofDigest(e.source_after.notes.find(n=>n.note_id===r.retained_note_id)):null})||await digest(p,'outcome_digest')!==p.outcome_digest)reject()
 return content
}

/** Component checker over the ORIGINAL entire snapshot. No old-format account
 * view, injected authorization callback, source handoff or certificates. */
async function verify(s:BrowserSyncScope,v:ResolutionInventorySnapshot,eventId:string,amk:AccountMasterKey,current:()=>boolean){
 const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
 let remaining=MAX_CONTINUATION_MATERIAL_BYTES
 const retain=(value:unknown)=>{try{boundResolutionJson(value,remaining)}catch{reject('resource_limit')}const bytes=new TextEncoder().encode(JSON.stringify(value));try{remaining-=bytes.length;if(remaining<0)reject('resource_limit')}finally{bytes.fill(0)}}
 const unique=(values:unknown[])=>{if(new Set(values.map(a=>JSON.stringify(a))).size!==values.length)reject()}
 const rows=v.rows.map(a=>readFutureInboxRecord(a,s)).sort((a,b)=>a.server_sequence-b.server_sequence),dag=inspectResolutionDag(s,v.history)
 unique(rows.map(r=>r.event_id));unique(rows.map(r=>r.server_sequence))
 if(rows.some((r,i)=>r.server_sequence!==i+1)||rows.length!==v.cursor.pull_cursor)reject('missing_sequence')
 const bindings=v.bindings.map(a=>validateBrowserProjectBinding(a,s));unique(bindings.map(b=>b.project_id));unique(bindings.map(b=>b.bootstrap_id))
 const owners=v.owners.map(a=>validateBrowserOwnerHead(a,s));unique(owners.map(a=>[a.owner_kind,a.owner_id]))
 // Validate every publication pair before rejecting local authorship cohorts.
 for(const a of v.out)validateBrowserStoredUploadPair(a,v.receipts.find(r=>(r as {event_id:string}).event_id===(a as {event_id:string}).event_id),s)
 if(v.intents.length||v.out.length||v.receipts.length||dag.history.some(a=>a.record_kind==='local_version'||a.record_kind==='candidate'&&(a.record_version===3||a.origin!=='peer')))reject('unsupported_local')
 const roots=[...dag.events.values()].filter((a):a is BrowserResolution4=>a.record_kind==='resolution')
 if(roots.length!==1)reject('unsupported_generation')
 const root=roots[0]!,target=rows.find(a=>a.event_id===eventId)
 if(!target)reject('not_applied')
 const targetWire=JSON.parse(target.wire_item).event
 if(targetWire.project_id!==root.project_id)reject('invalid_evidence')
 const projects=await Promise.all(v.projects.map(p=>project(s,p,amk,current)));unique(projects.map(p=>p.project_id));unique(v.localNotes.map(n=>(n as LocalNoteRecord).note_id))
 for(const raw of v.localNotes){const n=raw as LocalNoteRecord,p=projects.find(p=>p.project_id===n.project_id);if(!p||n.source_revision>p.source_revision)reject();await note(s,n,amk,current);check()}
 for(const p of projects)if(!same(p.member_ids,v.localNotes.filter(n=>(n as LocalNoteRecord).project_id===p.project_id).map(n=>(n as LocalNoteRecord).note_id).sort()))reject()
 const opened=new Map<string,Awaited<ReturnType<typeof openHistoryCandidate>>>(),contents=new Map<string,ContentNoteEvent>()
 for(const row of rows){
  const e=JSON.parse(row.wire_item).event
  if(e.device_id===s.deviceId)reject('unsupported_local')
  if(['stage','stage_order'].includes(e.entity_type))reject('unsupported_stage')
  if(!['project_metadata','note'].includes(e.entity_type))reject('unsupported_family')
  if(row.state==='note_resolution_proven'&&row.event_id!==root.event_id)reject('unsupported_generation')
  if(e.entity_type==='project_metadata')retain(await openCanonical(s,row,amk))
  else if(row.state==='received'){
   if(e.operation==='resolution')reject('unsupported_generation')
   if(e.operation==='event'){const c=await openCanonical(s,row,amk) as ContentNoteEvent;if(c.event.version!==1)reject('unsupported_generation');retain(c);contents.set(row.event_id,c)}
   else await openNoteTransport(s,amk,row.protocol_version,row.wire_item,'legacy')
  }
  check()
 }
 for(const c of dag.events.values())if(c.record_kind==='candidate'){
  const value=await openHistoryCandidate(s,c,amk),row=rows.find(a=>a.event_id===c.event_id),binding=bindings.find(b=>b.project_id===c.project_id)
  if(!row||!binding||binding.bootstrap_id!==c.bootstrap_id||binding.remote_state!=='active')reject()
  const wire=JSON.parse(row.wire_item),{device_id,server_sequence:_seq,...event}=wire.event
  if(device_id!==c.source_device_id||row.protocol_version!==c.protocol_version||!same(JSON.parse(c.wire_item),c.record_version===2?wire:{event,object:wire.object}))reject()
  retain(value);opened.set(c.event_id,value)
  if(row.state==='note_proven'){
   await verifyStoredNoteProof(s,amk,row)
   if(c.record_version!==1||row.note_proof.outcome!=='applied'||row.note_proof.bootstrap_id!==c.bootstrap_id||row.note_proof.local_note_digest!==c.projection_digest||row.note_proof.source_revision!==c.projection?.source_revision)reject()
  }else if(row.state==='content_note_proven'){
   if(c.record_version!==2||!same(await contentProofFor(s,row,c,value.mutation),row.content_note_proof)||!c.projection)reject()
  }else if(row.state==='note_conflict_preserved'||row.state==='content_note_conflict_preserved'){
   const p=row.state==='note_conflict_preserved'?row.note_conflict_proof:row.content_note_conflict_proof,g=dag.history.find((a):a is BrowserNoteConflictGroup=>a.record_kind==='group'&&a.project_id===c.project_id&&a.note_id===c.note_id&&a.group_id===p.group_id),m=g?.members.find(m=>m.event_id===c.event_id)
   if(!g||!m||m.source!=='remote'||m.server_sequence!==row.server_sequence||m.conflict_generation!==p.conflict_generation||c.projection!==null||c.projection_digest!==null||!same(p.header,value.header)||p.mutation!==value.mutation||p.bootstrap_id!==c.bootstrap_id||await noteOutcomeDigest(p)!==p.outcome_digest)reject()
   if(row.state==='content_note_conflict_preserved'&&(!same(await contentConflictProofFor(s,row,c,g,value.mutation),row.content_note_conflict_proof)))reject()
  }else reject('not_applied')
  if(c.record_version===2){const {content}=await openNoteTransport(s,amk,3,row.wire_item,'content_note_v1');if(!content)reject();retain(content);contents.set(c.event_id,content)}
  check()
 }
 for(const row of rows)if(['note_proven','content_note_proven','note_conflict_preserved','content_note_conflict_preserved'].includes(row.state)&&!dag.events.has(row.event_id))reject()
 const rootContent=await resolution(s,root,rows,dag,opened,amk,current);if(rootContent)contents.set(root.event_id,rootContent)
 if(dag.history.filter(a=>a.record_kind==='group_transition').length!==1)reject('unsupported_generation')
 for(const h of dag.history)if(h.record_kind==='group'&&!dag.history.some(t=>t.record_kind==='group_transition'&&t.project_id===h.project_id&&t.note_id===h.note_id&&t.group_id===h.group_id&&t.resolution_event_id===root.event_id&&t.resolution_digest===root.record_digest))reject('unresolved_fork')
 const head=owners.find(a=>a.owner_kind==='project_metadata'&&a.owner_id===root.project_id)
 if(!head||head.owner_kind!=='project_metadata')reject('missing_metadata')
 const metadata=validateBrowserMetadataHead(head,s),binding=bindings.find(b=>b.project_id===root.project_id)
 if(!binding||binding.mode!=='import_remote'||binding.phase!=='captured'||binding.remote_state!=='active'||binding.bootstrap_id!==metadata.bootstrap_id||metadata.bootstrap_id!==root.bootstrap_id)reject('invalid_evidence')
 // Every owner history is independently opened; no certificate is fabricated
 // from the count or digest of a successful-looking head.
 for(const owner of owners){
  if(owner.owner_kind!=='project_metadata')reject('unsupported_stage')
  const h=validateBrowserMetadataHead(owner,s),chain=[...h.history].sort((a,b)=>a.server_sequence-b.server_sequence)
  if(!bindings.some(b=>b.project_id===h.owner_id&&b.bootstrap_id===h.bootstrap_id&&b.mode==='import_remote'&&b.phase==='captured'&&b.remote_state==='active'))reject('invalid_evidence')
  for(const [i,p] of chain.entries()){
   const previous=chain[i-1],row=rows.find(a=>a.event_id===p.event_id)
   if(p.source_device_id===s.deviceId||!['create','update','delete'].includes(p.operation)||i===0&&(p.operation!=='create'||p.revision!==1||p.generation!==1||p.parent_event_ids.length)||previous&&(!same(p.parent_event_ids,[previous.event_id])||p.revision!==previous.revision+1||p.generation<=previous.generation||previous.operation==='delete'||p.server_sequence<=previous.server_sequence)||!row||row.state!=='applied'||!same(row.applied_proof,p)||row.server_sequence!==p.server_sequence)reject('unproven_interval')
   const wire=JSON.parse(row.wire_item),event=await openCanonical(s,row,amk) as ProjectMetadataEvent,proof=metadataProofFor(s,wire.event,event,await noteProofDigest({protocol_version:row.protocol_version,event:wire.event,object:wire.object}),row.protocol_version)
   if(!same(proof,p))reject();check()
  }
  if(!same(h.tip_event_ids,[chain.at(-1)!.event_id]))reject('unproven_interval')
  const retained=rows.filter(a=>{const e=JSON.parse(a.wire_item).event;return e.entity_type==='project_metadata'&&e.project_id===h.owner_id})
  if(retained.length!==chain.length||retained.some(row=>!chain.some(p=>p.event_id===row.event_id)))reject('unproven_interval')
 }
 if(rows.some(row=>{const e=JSON.parse(row.wire_item).event;return e.entity_type==='project_metadata'&&!owners.some(h=>h.owner_kind==='project_metadata'&&h.owner_id===e.project_id&&h.history.some(p=>p.event_id===row.event_id))}))reject('unproven_interval')
 const chain=[...metadata.history].sort((a,b)=>a.server_sequence-b.server_sequence),deletion=chain.at(-1)!
 if(deletion.operation!=='delete'||chain.slice(0,-1).some(p=>p.operation==='delete'))reject('not_terminal_delete')
 // Authenticate the dependency component of every retained Content outcome in
 // the root cohort. Pending Content stays pending and grants no positive result.
 for(const [id,c] of contents){
  const row=rows.find(r=>r.event_id===id)!,e=JSON.parse(row.wire_item).event,n=c.event.version===1?c.event.note:c.event.result.note
  if(c.account_id!==s.canonicalUserId||c.device_id!==e.device_id||!same(c.event.header,dag.events.get(id)?.header??c.event.header)||c.event.header.revision!==e.revision||c.event.header.updated_at!==e.updated_at||c.dependencies.bootstrap_id!==metadata.bootstrap_id||c.event.header.project_id!==root.project_id)reject()
  if(n.stage_id!==null||n.source_type!=='project'||n.source_map_id!==null||n.source_node_id!==null||c.dependencies.stage_event_ids.length||c.event.version===2&&c.event.resolution.strategy==='keep_both'&&c.event.resolution.retained_note.stage_id!==null)reject('unsupported_stage')
  if(row.state==='received')continue
  const m=chain.find(p=>p.event_id===c.dependencies.metadata_event_id),at=chain.filter(p=>p.server_sequence<row.server_sequence).at(-1)
  if(!m)reject('missing_metadata')
  if(m.operation==='delete'||!at||at.operation==='delete'||m.server_sequence>=row.server_sequence||row.server_sequence>=deletion.server_sequence)reject('outside_interval')
 }
 check()
 if(!['content_note_proven','note_resolution_proven'].includes(target.state))reject(target.state==='received'?'not_applied':'not_content')
 if(!contents.has(target.event_id))reject('not_content')
 return{metadataEvents:chain.length,pendingEvents:rows.filter(r=>r.state==='received').length}
}

/** Isolated .13 reader. No persistence composition or F/H/O/G/Q/K imports this
 * factory. Only a frozen diagnostic escapes; there is no capability state. */
export class BrowserHistoricalMetadataDependency {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly profileCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext,device:VerifiedBrowserDevice){
  const transaction=this.transaction,profileCurrent=this.profileCurrent
  return Object.freeze({inspect:async(input:BrowserSyncScope,eventId:string)=>{
   const s=snapshotBrowserSyncScope(input),initial=auth.requireContext(),{context}=await bindings.ensureForCurrentUser(s.accountId),lease=keys.leaseForAccount(s.accountId)
   const current=()=>profileCurrent()&&auth.isCurrent(initial)&&auth.isCurrent(context)&&!!lease?.isCurrent()&&currentBrowserDevice(device,s,auth)
   const check=()=>{if(!current())throw new BrowserPersistenceError('closed')}
   if(!lease||lease.localAccountId!==s.accountId||lease.canonicalUserId!==s.canonicalUserId||lease.authEpoch!==context.authEpoch||context.userId!==s.canonicalUserId)throw new BrowserPersistenceError('account_mismatch')
   check();const load=()=>transaction<ResolutionInventorySnapshot>(s,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,s,current,result,abort)),v=await load()
   let reason:Reason|null=null,counts:{metadataEvents:number;pendingEvents:number}|undefined
   try{counts=await lease.use(amk=>verify(s,v,eventId,amk,current))}catch(e){check();reason=e instanceof Rejected?e.reason:'invalid_evidence'}
   check();if(!same(await load(),v))throw new BrowserPersistenceError('stale_source');check()
   return Object.freeze({readOnly:true as const,historicalMetadataAdmissible:reason===null,reason,fullHistoryAuthenticated:false as const,sourceAuthorized:false as const,firstApplyAllowed:false as const,commitAuthorized:false as const,ackAuthorized:false as const,ready:false as const,...counts})
  }})
 }
}
