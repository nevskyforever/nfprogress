import { openNoteTransport } from './noteTransport'
import { prepareNotePrerequisite, prepareNoteTransportCommit, scheduleNoteTransportCommit, type VerifiedNoteTransportCommit } from './noteTransportPrerequisite'
import { NOTE_INTENT_STORE,validateNoteIntent,type BrowserNoteIntent } from './noteIntentRecords'
import { freezeLocalVersion,openFrozenLocalVersion,unsealedPlaintext } from './noteUnsealedVersion'
import { NOTE_HISTORY_STORE,validateNoteHistorySet,type BrowserNoteLocalVersion,type BrowserNoteHistoryRecord,type BrowserNoteCandidate,type BrowserNoteConflictGroup,type BrowserNoteHead } from './noteHistoryRecords'
import { historyRange,makeHistoryCandidate,openHistoryCandidate,nextNoteHead,commitHistoryChange } from './noteHistory'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { type AccountMasterKey } from '@/crypto'
import { type NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError, type BrowserPersistenceCode } from './persistence'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { immutableWireIdentity, readBrowserSyncCursor, snapshotBrowserSyncScope, validateBrowserInboxRecord, validateBrowserUploadPair, type BrowserSyncScope, type BrowserSyncTransaction, type BrowserInboxRecord, type BrowserSyncCheckpoint } from './syncDurability'
import { BrowserLocalAuthority, assertLocalSourceInTransaction, scheduleProtectedNoteApply, type BrowserLocalAuthorityRuntime, type ProtectedNoteSourcePlan, type LocalSourceToken } from './localAuthority'
import { validateBrowserNoteProof,validateBrowserNoteConflictProof,type BrowserNoteConflictProof, type BrowserNoteProof } from './noteApplyRecords'
import { deriveInitialLegacyCohort } from './initialNoteCapture'

export interface VerifiedNoteCausalPlan {readonly verifiedNoteCausalPlan:unique symbol}
/** Backward-compatible Legacy surface over the shared private causal plan. */
export type VerifiedLegacyNotePlan = VerifiedNoteCausalPlan
interface Inventory {intents:BrowserNoteIntent[];history:BrowserNoteHistoryRecord[];checkpoint:BrowserSyncCheckpoint;binding:BrowserProjectBinding;rows:BrowserInboxRecord[];out:unknown[];receipts:unknown[]}
type DormantNoteOutcome=Omit<BrowserNoteProof,'owner_kind'> & {owner_kind:'dormant_note_prerequisite'}
type NoteCausalOutcome=BrowserNoteProof|BrowserNoteConflictProof|DormantNoteOutcome
interface Plan {transportHook?:VerifiedNoteTransportCommit;dormant?:boolean;owner:BrowserLegacyNoteApplyRuntime;scope:BrowserSyncScope;inventory:Inventory;row:BrowserInboxRecord;proof:NoteCausalOutcome;historyNext:BrowserNoteHistoryRecord[];current:()=>boolean;local:BrowserLocalAuthorityRuntime;plaintext?:NoteSyncPlaintext;source?:ProtectedNoteSourcePlan;sourceToken?:LocalSourceToken;replay:boolean}
const plans=new WeakMap<object,Plan>()
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const range=(a:string)=>IDBKeyRange.bound([a],[a,[]])
function historySort(rows:BrowserNoteHistoryRecord[]):BrowserNoteHistoryRecord[]{return rows.sort((a,b)=>{const x=`${a.record_kind}:${a.record_id}`,y=`${b.record_kind}:${b.record_id}`;return x<y?-1:x>y?1:0})}
function proofRow(row:BrowserInboxRecord,proof:NoteCausalOutcome){if(proof.owner_kind!=='legacy_note')fail('corrupt_record');return proof.outcome==='conflict_preserved'?{...row,record_version:4,state:'note_conflict_preserved',note_conflict_proof:proof}:{...row,record_version:3,state:'note_proven',note_proof:proof}}
function fail(code:BrowserPersistenceCode):never{throw new BrowserPersistenceError(code)}
export async function noteProofDigest(value:unknown):Promise<string>{const bytes=new TextEncoder().encode(immutableWireIdentity(value));let digest:Uint8Array|undefined;try{digest=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));return Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('')}finally{bytes.fill(0);digest?.fill(0)}}
export async function noteOutcomeDigest(p:NoteCausalOutcome):Promise<string>{const {outcome_digest:_digest,...body}=p;return noteProofDigest(body)}
export async function openRetainedNote(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord):Promise<NoteSyncPlaintext>{
  return (await openNoteTransport(scope,amk,row.protocol_version,row.wire_item,'legacy')).plaintext
}
export async function verifyStoredNoteProof(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord):Promise<void>{
  if(row.state!=='note_proven')fail('corrupt_record');const raw=JSON.parse(row.wire_item),p=validateBrowserNoteProof(row.note_proof,scope)
  try{const decoded=await openRetainedNote(scope,amk,row);if(await noteOutcomeDigest(p)!==p.outcome_digest||!same(decoded.header,p.header)||decoded.mutation!==p.mutation||await noteProofDigest({protocol_version:row.protocol_version,event:raw.event,object:raw.object})!==p.wire_digest)fail('corrupt_record')}catch{fail('corrupt_record')}
}
function requireOwnReceipt(scope:BrowserSyncScope,inventory:Inventory,row:BrowserInboxRecord):void{
  const raw=JSON.parse(row.wire_item),{device_id,server_sequence,...event}=raw.event
  const outbound=inventory.out.find(r=>(r as {event_id:string}).event_id===row.event_id),receipt=inventory.receipts.find(r=>(r as {event_id:string}).event_id===row.event_id)
  if(device_id!==scope.deviceId||!outbound||!receipt)fail('self_echo_unavailable')
  const out=validateBrowserUploadPair(outbound,receipt,scope)
  if(out.state!=='accepted'||out.protocol_version!==row.protocol_version||(receipt as {server_sequence:number}).server_sequence!==server_sequence||!same(JSON.parse(out.raw_body).items[0],{event,object:raw.object}))fail('self_echo_unavailable')
}
/** Internal capability reader: no DTO constructor. Only current authenticated prepare can expose plaintext to local authority. */
export function verifiedLegacyNoteForLocal(token:VerifiedLegacyNotePlan,local:BrowserLocalAuthorityRuntime,scope:BrowserSyncScope):NoteSyncPlaintext {
  const p=plans.get(token);if(!p||p.local!==local||!same(p.scope,scope)||!p.current()||!p.plaintext||p.proof.outcome!=='applied')fail('stale_source');return p.plaintext
}
export class BrowserLegacyNoteApply {
  constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthority,private readonly sessionCurrent:()=>boolean){}
  bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext):BrowserLegacyNoteApplyRuntime{return new BrowserLegacyNoteApplyRuntime(this.transaction,this.local.bind(auth,bindings,keys),this.sessionCurrent,auth,bindings,keys)}
}
export class BrowserLegacyNoteApplyRuntime {
  constructor(private readonly transaction:BrowserSyncTransaction,private readonly local:BrowserLocalAuthorityRuntime,private readonly sessionCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext){}
  private async guard(scope:BrowserSyncScope){if(!this.sessionCurrent()||this.auth.state!=='authenticated')fail('closed');const {context}=await this.bindings.ensureForCurrentUser(scope.accountId),lease=this.keys.leaseForAccount(scope.accountId);const current=()=>this.sessionCurrent()&&this.auth.isCurrent(context)&&!!lease?.isCurrent();if(!lease||context.userId!==scope.canonicalUserId||lease.localAccountId!==scope.accountId||lease.canonicalUserId!==scope.canonicalUserId||lease.authEpoch!==context.authEpoch||!current())fail('account_mismatch');return{lease,current}}
  private load(scope:BrowserSyncScope,sequence:number,dormant=false):Promise<Inventory>{return this.transaction(scope,['inbox','projectBindings','outbox','receipts','cursors',NOTE_HISTORY_STORE,NOTE_INTENT_STORE],'readonly',(tx,result,abort)=>{
    const incoming=tx.objectStore('inbox').getAll(range(scope.accountId)),bindings=tx.objectStore('projectBindings').getAll(range(scope.accountId)),out=tx.objectStore('outbox').getAll(range(scope.accountId)),receipts=tx.objectStore('receipts').getAll(range(scope.accountId)),intents=tx.objectStore(NOTE_INTENT_STORE).getAll(range(scope.accountId));let n=0;const finish=()=>{if(++n!==5)return;try{const rows=incoming.result.map(r=>validateBrowserInboxRecord(r,scope)),row=rows.find(r=>r.server_sequence===sequence);if(!row)fail('missing_history');const e=JSON.parse(row.wire_item).event;if(e.entity_type!=='note'||!(dormant?e.operation==='event'&&e.deleted_at===null&&row.protocol_version===3:['upsert','delete'].includes(e.operation)))fail('unsupported_local_source');const binding=bindings.result.find(b=>b.project_id===e.project_id);if(!binding)fail('ineligible_lineage');readBrowserSyncCursor(tx,scope,checkpoint=>{try{if(sequence>checkpoint.pull_cursor)fail('corrupt_record');const history=tx.objectStore(NOTE_HISTORY_STORE).getAll(historyRange(scope,e.project_id,e.entity_id));history.onsuccess=()=>{try{result({intents:intents.result.map(v=>validateNoteIntent(v,scope)),history:historySort(validateNoteHistorySet(scope,history.result)),checkpoint,binding:validateBrowserProjectBinding(binding,scope),rows,out:out.result,receipts:receipts.result})}catch(e){abort(e)}}}catch(e){abort(e)}},abort)}catch(e){abort(e)}};[incoming,bindings,out,receipts,intents].forEach(r=>r.onsuccess=finish)
  })}
  async prepare(scope:BrowserSyncScope,sequence:number):Promise<VerifiedLegacyNotePlan>{return this.prepareRoute(scope,sequence,false)}
  /** Internal dormant acceptance adapter. Never selected by normal apply or production composition. No Content ACK proof. */
  async prepareDormantOrdinary(scope:BrowserSyncScope,sequence:number):Promise<VerifiedLegacyNotePlan>{return this.prepareRoute(scope,sequence,true)}
  private async prepareRoute(scope:BrowserSyncScope,sequence:number,dormant:boolean):Promise<VerifiedLegacyNotePlan>{
    scope=snapshotBrowserSyncScope(scope);if(!Number.isSafeInteger(sequence)||sequence<1)fail('missing_history')
    const {lease,current}=await this.guard(scope),inventory=await this.load(scope,sequence,dormant),row=inventory.rows.find(r=>r.server_sequence===sequence)!,binding=inventory.binding
    if(binding.remote_state!=='active'||!(binding.mode==='import_remote'&&binding.phase==='captured'||binding.mode==='upload_existing'&&binding.phase==='completing'))fail('ineligible_lineage')
    const cohort=binding.mode==='upload_existing'?deriveInitialLegacyCohort(scope,binding,inventory.out,inventory.receipts):null
    const raw=JSON.parse(row.wire_item),reference=raw.event,{device_id:_source,server_sequence:_sequence,...event}=reference,item={event,object:raw.object}
    return lease.use(async amk=>{
      const prerequisite=dormant?await prepareNotePrerequisite(scope,row,binding,amk,current,this.transaction):undefined
      let plaintext:NoteSyncPlaintext;try{plaintext=prerequisite?prerequisite.plaintext:await openRetainedNote(scope,amk,row)}catch(e){if(row.state!=='received')fail('corrupt_record');throw e}const h=plaintext.header
      const records=inventory.history,candidates=records.filter((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'),groups=records.filter((r):r is BrowserNoteConflictGroup=>r.record_kind==='group'),versions=records.filter((r):r is BrowserNoteLocalVersion=>r.record_kind==='local_version')
      if(records.some(r=>r.bootstrap_id!==binding.bootstrap_id))fail('stale_lineage')
      for(const c of candidates)await openHistoryCandidate(scope,c,amk);for(const v of versions)await openFrozenLocalVersion(scope,v,amk)
      const add=(c:BrowserNoteCandidate)=>{const old=candidates.find(r=>r.event_id===c.event_id);if(old){if(old.wire_item!==c.wire_item||!same(old.header,c.header)||old.source_device_id!==c.source_device_id||old.protocol_version!==c.protocol_version)fail('conflicting_record')}else candidates.push(c)}
      // Explicit first-use reconstruction: immutable event+existing outcome only. Never current Note.
      for(const out of cohort?.rows??[]){const wire=JSON.parse(out.raw_body).items[0];if(wire.event.entity_id!==h.entity_id)continue;const found=candidates.find(c=>c.event_id===out.event_id);if(found){if(found.wire_item!==JSON.stringify(wire))fail('conflicting_record');continue}
        const synthetic={...row,record_version:1,state:'received',event_id:out.event_id,server_sequence:1,protocol_version:out.protocol_version,wire_item:JSON.stringify({...wire,event:{...wire.event,device_id:scope.deviceId,server_sequence:1}})} as BrowserInboxRecord
        const opened=await openRetainedNote(scope,amk,synthetic);add(await makeHistoryCandidate(scope,binding,out.protocol_version,scope.deviceId,wire,opened,'initial_backfill',null))
      }
      const applied=inventory.rows.filter(r=>r.state==='note_proven'&&r.note_proof.header.project_id===h.project_id&&r.note_proof.header.entity_id===h.entity_id)
      for(const prior of applied){if(prior.state!=='note_proven')fail('corrupt_record');await verifyStoredNoteProof(scope,amk,prior);if(prior.note_proof.bootstrap_id!==binding.bootstrap_id)fail('stale_lineage');if(prior.note_proof.outcome==='self_echo_applied'){requireOwnReceipt(scope,inventory,prior);if(!candidates.some(c=>c.event_id===prior.event_id))fail('candidate_history_unavailable');continue}
        if(!candidates.some(c=>c.event_id===prior.event_id)){const wire=JSON.parse(prior.wire_item),{device_id:source,server_sequence:_seq,...e}=wire.event,opened=await openRetainedNote(scope,amk,prior);add(await makeHistoryCandidate(scope,binding,prior.protocol_version,source,{event:e,object:wire.object},opened,'peer',null,prior.note_proof.local_note_digest))}
      }
      for(const group of groups)for(const member of group.members){
        if(member.source==='local_unsealed'){const frozen=versions.find(v=>v.version_id===member.version_id);if(!frozen||frozen.intent.mutation_generation!==member.local_mutation_generation)fail('corrupt_record');continue}
        const retained=inventory.rows.find(r=>r.event_id===member.event_id),candidate=candidates.find(c=>c.event_id===member.event_id)
        if(!retained||retained.server_sequence!==member.server_sequence||!candidate)fail('corrupt_record')
        if(member.source==='remote_applied'){
          if(retained.state!=='note_proven'||retained.note_proof.bootstrap_id!==group.bootstrap_id)fail('corrupt_record')
          await verifyStoredNoteProof(scope,amk,retained);if(retained.note_proof.outcome==='self_echo_applied')requireOwnReceipt(scope,inventory,retained)
        }else{
          if(retained.state!=='note_conflict_preserved')fail('corrupt_record');const p=retained.note_conflict_proof,wire=JSON.parse(retained.wire_item),localMember=group.members.find(m=>m.source==='local_unsealed');if(localMember){if(p.record_version!==2||p.local_version_digest!==versions.find(v=>v.version_id===localMember.version_id)?.record_digest||p.local_version_id!==localMember.version_id||p.local_mutation_generation!==(localMember as {local_mutation_generation:number}).local_mutation_generation)fail('corrupt_record')}else if(p.record_version!==1)fail('corrupt_record')
          if(p.group_id!==group.group_id||p.bootstrap_id!==group.bootstrap_id||p.conflict_generation!==member.conflict_generation||!same(p.header,candidate.header)||p.wire_digest!==await noteProofDigest({protocol_version:retained.protocol_version,event:wire.event,object:wire.object})||p.outcome_digest!==await noteOutcomeDigest(p))fail('corrupt_record')
        }
      }
      const outgoing=inventory.out.map(v=>validateBrowserUploadPair(v,inventory.receipts.find(p=>(p as {event_id:string}).event_id===(v as {event_id:string}).event_id),scope)).filter(r=>{const e=JSON.parse(r.raw_body).items[0].event;return e.project_id===h.project_id&&e.entity_id===h.entity_id&&e.entity_type==='note'})
      if(outgoing.some(r=>!candidates.some(c=>c.event_id===r.event_id)))fail('candidate_history_unavailable')
      let head=records.find((r):r is BrowserNoteHead=>r.record_kind==='head')
      if(!head&&candidates.length){const nativeHeads=[...applied.map(r=>({event:r.event_id,revision:r.state==='note_proven'?r.note_proof.header.revision:0})),...outgoing.map(r=>{const e=JSON.parse(r.raw_body).items[0].event;return{event:r.event_id,revision:e.revision}})],max=Math.max(...nativeHeads.map(r=>r.revision)),top=nativeHeads.filter(r=>r.revision===max)
        if(!top.length||new Set(top.map(r=>r.event)).size!==1)fail('candidate_history_unavailable');head=nextNoteHead(scope,binding,candidates,top[0]!.event)
      }
      if(dormant&&candidates.some(c=>c.event_id===h.event_id))fail('conflicting_record') // One immutable event authority; no cross-route overwrite or synthetic replay proof.
      const wireDigest=await noteProofDigest({protocol_version:row.protocol_version,event:reference,object:raw.object})
      let proof:NoteCausalOutcome,replay=false
      if(row.state==='applied')fail('corrupt_record')
      if(row.state==='note_proven'){
        proof=validateBrowserNoteProof(row.note_proof,scope);if(proof.outcome==='self_echo_applied')requireOwnReceipt(scope,inventory,row);await verifyStoredNoteProof(scope,amk,row);if(proof.bootstrap_id!==binding.bootstrap_id)fail('stale_lineage');replay=true
      }else if(row.state==='note_conflict_preserved'){
        proof=validateBrowserNoteConflictProof(row.note_conflict_proof,scope)
        const group=groups.find(g=>g.group_id===(proof as BrowserNoteConflictProof).group_id),member=group?.members.find(m=>m.event_id===row.event_id)
        if(!group||!member||member.source!=='remote'||member.server_sequence!==sequence||member.conflict_generation!==proof.conflict_generation||proof.bootstrap_id!==binding.bootstrap_id||proof.wire_digest!==wireDigest||!same(proof.header,h)||proof.mutation!==plaintext.mutation||await noteOutcomeDigest(proof)!==proof.outcome_digest)fail('corrupt_record');replay=true
      }else{
        const own=reference.device_id===scope.deviceId,linear=head&&candidates.find(c=>c.event_id===head!.linear_head_event_id)
        if(own){requireOwnReceipt(scope,inventory,row);if(!candidates.some(c=>c.event_id===h.event_id))fail('candidate_history_unavailable');if(linear&&linear.header.revision===h.revision&&linear.event_id!==h.event_id)fail('note_conflict_unproven')}
        const source=await this.local.readSnapshot(scope,binding.project_id)
        let preserve:BrowserNoteConflictGroup|undefined
        if(!own){
          const open=groups.find(g=>g.common_parent_event_id===h.parent_event_id&&g.tip_revision===h.revision)
          const localIntents=inventory.intents.filter(i=>i.project_id===h.project_id&&i.note_id===h.entity_id);if(localIntents.length>1)fail('corrupt_record');const localIntent=localIntents[0];if(localIntent&&localIntent.bootstrap_id!==binding.bootstrap_id)fail('stale_lineage');if(localIntent)await unsealedPlaintext(scope,localIntent,amk)
          const localSibling=!open&&localIntent&&h.revision>=2&&localIntent.revision===h.revision&&localIntent.parent_event_id===h.parent_event_id&&localIntent.event_id!==h.event_id&&candidates.some(c=>c.event_id===h.parent_event_id&&c.header.revision===h.revision-1)
          const sibling=!localIntent&&!open&&linear&&h.revision>=2&&linear.header.revision===h.revision&&linear.header.parent_event_id===h.parent_event_id
          if(open||localSibling||sibling){
            if(!open&&groups.length)fail('note_conflict_unproven') // Native reuses one open group; a different fork is not conflict_preserved.
            if(plaintext.mutation==='create')fail('note_conflict_unproven')
            if(open){preserve=structuredClone(open);if(preserve.members.some(m=>m.event_id===h.event_id))fail('conflicting_record');preserve.conflict_generation++;if(!Number.isSafeInteger(preserve.conflict_generation))fail('source_limit')}
            else if(localSibling){
              const localRecord=source.notes.find(n=>n.note_id===h.entity_id);if(!localRecord||!same(localRecord,localIntent!.snapshot))fail('note_conflict_unproven')
              const frozen=await freezeLocalVersion(scope,localIntent!,amk);versions.push(frozen);const group_id=crypto.randomUUID();preserve={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:h.project_id,note_id:h.entity_id,bootstrap_id:binding.bootstrap_id,record_kind:'group',record_id:group_id,group_id,common_parent_event_id:h.parent_event_id!,tip_revision:h.revision,conflict_generation:1,lifecycle:'open',members:[{version_id:frozen.version_id,event_id:localIntent!.event_id,source:'local_unsealed',server_sequence:null,conflict_generation:1,local_mutation_generation:localIntent!.mutation_generation}],tip_event_ids:[]}
            }else{
              const prior=applied.find(r=>r.event_id===linear!.event_id);if(!prior||prior.state!=='note_proven')fail('note_conflict_unproven')
              const localRecord=source.notes.find(n=>n.note_id===h.entity_id);if(!localRecord||!linear!.projection_digest||await noteProofDigest(localRecord)!==linear!.projection_digest)fail('note_conflict_unproven')
              const group_id=crypto.randomUUID();preserve={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:h.project_id,note_id:h.entity_id,bootstrap_id:binding.bootstrap_id,record_kind:'group',record_id:group_id,group_id,common_parent_event_id:h.parent_event_id!,tip_revision:h.revision,conflict_generation:1,lifecycle:'open',members:[{version_id:`applied:${scope.accountId}:${linear!.event_id}`,event_id:linear!.event_id,source:'remote_applied',server_sequence:prior.server_sequence,conflict_generation:1}],tip_event_ids:[]}
            }
            preserve.members.push({version_id:`remote:${scope.accountId}:${h.event_id}`,event_id:h.event_id,source:'remote',server_sequence:sequence,conflict_generation:preserve.conflict_generation});preserve.members.sort((a,b)=>a.event_id<b.event_id?-1:1);preserve.tip_event_ids=preserve.members.map(m=>m.event_id)
          }else{
            if(localIntent)fail('note_conflict_unproven') // Native pending branch prevents clean apply, even its purported child.
            if(h.revision===1){if(head||candidates.length||source.notes.some(n=>n.note_id===h.entity_id))fail('note_conflict_unproven')}
            else{if(!linear||linear.header.revision<h.revision-1)fail('note_orphan');if(linear.header.revision!==h.revision-1||linear.event_id!==h.parent_event_id)fail('note_conflict_unproven');if(!linear.projection_digest)fail('candidate_history_unavailable');const localRecord=source.notes.find(n=>n.note_id===h.entity_id);if(!localRecord||await noteProofDigest(localRecord)!==linear.projection_digest)fail('note_conflict_unproven')
              if(linear.origin!=='peer'){const out=outgoing.find(r=>r.event_id===linear.event_id),receipt=inventory.receipts.find(r=>(r as {event_id:string}).event_id===linear.event_id);if(!out||out.state!=='accepted'||!receipt)fail('candidate_history_unavailable')}
            }
          }
        }
        if(dormant&&preserve)fail('note_conflict_unproven')
        if(preserve){
          proof={record_version:1,owner_kind:'legacy_note',outcome:'conflict_preserved',account_id:scope.accountId,bootstrap_id:binding.bootstrap_id,protocol_version:row.protocol_version,reference:structuredClone(reference),header:structuredClone(h),mutation:plaintext.mutation as 'update'|'delete',wire_digest:wireDigest,outcome_digest:'',group_id:preserve.group_id,conflict_generation:preserve.conflict_generation}
          const localMember=preserve.members.find(m=>m.source==='local_unsealed');if(localMember){proof={...proof,record_version:2,local_version_digest:versions.find(v=>v.version_id===localMember.version_id)!.record_digest,local_version_id:localMember.version_id,local_mutation_generation:(localMember as {local_mutation_generation:number}).local_mutation_generation}}
          add(await makeHistoryCandidate(scope,binding,row.protocol_version,reference.device_id,item,plaintext,'peer',null));const at=groups.findIndex(g=>g.group_id===preserve!.group_id);if(at<0)groups.push(preserve);else groups[at]=preserve
          head=nextNoteHead(scope,binding,candidates,head!.linear_head_event_id,records.find((r):r is BrowserNoteHead=>r.record_kind==='head'))
          const token=Object.freeze({}) as VerifiedLegacyNotePlan,p:Plan={owner:this,scope,inventory,row,proof,current,local:this.local,sourceToken:source.token,replay:false,historyNext:historySort([...candidates,...groups,...versions,head])};proof.outcome_digest=await noteOutcomeDigest(proof);validateBrowserNoteConflictProof(proof,scope);validateNoteHistorySet(scope,p.historyNext);if(!current())fail('closed');plans.set(token,p);return token
        }
        const cleanProof:BrowserNoteProof|DormantNoteOutcome={record_version:1,owner_kind:dormant?'dormant_note_prerequisite':'legacy_note',outcome:own?'self_echo_applied':'applied',account_id:scope.accountId,bootstrap_id:binding.bootstrap_id,protocol_version:row.protocol_version,reference:structuredClone(reference),header:structuredClone(h),mutation:plaintext.mutation,wire_digest:wireDigest,outcome_digest:'',source_revision:null,local_note_digest:null};proof=cleanProof
        const token=Object.freeze({}) as VerifiedLegacyNotePlan,p:Plan={owner:this,scope,inventory,row,proof,current,local:this.local,plaintext,sourceToken:source.token,replay:false,historyNext:[]};p.dormant=dormant;plans.set(token,p)
        try{if(!own){const prepared=await this.local.prepareProtectedNoteApply(scope,source.token,token);p.source=prepared.token;cleanProof.source_revision=prepared.source_revision;cleanProof.local_note_digest=await noteProofDigest(prepared.note);if(prerequisite){const transport=await prepareNoteTransportCommit(prerequisite.certificate,plaintext,prepared.note);p.transportHook=transport.hook;add(transport.candidate)}else add(await makeHistoryCandidate(scope,binding,row.protocol_version,reference.device_id,item,plaintext,'peer',prepared.note));head=nextNoteHead(scope,binding,candidates,h.event_id,records.find((r):r is BrowserNoteHead=>r.record_kind==='head'))}
          proof.outcome_digest=await noteOutcomeDigest(proof);if(proof.owner_kind==='legacy_note')validateBrowserNoteProof(proof,scope);p.historyNext=historySort([...candidates,...groups,...versions,...(head?[head]:[])]);validateNoteHistorySet(scope,p.historyNext);if(!current())fail('closed');return token
        }finally{delete p.plaintext}
      }
      const token=Object.freeze({}) as VerifiedLegacyNotePlan,p:Plan={owner:this,scope,inventory,row,proof,current,local:this.local,replay,historyNext:historySort([...candidates,...groups,...versions,...(head?[head]:[])])};validateNoteHistorySet(scope,p.historyNext);if(!current())fail('closed');plans.set(token,p);return token
    })
  }
  async commit(token:VerifiedLegacyNotePlan):Promise<'applied'|'self_echo_applied'|'already_applied'|'conflict_preserved'>{
    const p=plans.get(token);if(!p||p.owner!==this)fail('stale_source');if(!p.current())fail('closed');let unsubscribe:(()=>void)|undefined
    return this.transaction<'applied'|'self_echo_applied'|'already_applied'|'conflict_preserved'>(p.scope,['inbox','projectBindings','outbox','receipts','cursors','localProjects','localNotes',NOTE_HISTORY_STORE,NOTE_INTENT_STORE,...(p.transportHook?['ownerHeads']:[])],'readwrite',(tx,result,abort)=>{
      unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')))
      const incoming=tx.objectStore('inbox').getAll(range(p.scope.accountId)),binding=tx.objectStore('projectBindings').get([p.scope.accountId,p.inventory.binding.project_id]),out=tx.objectStore('outbox').getAll(range(p.scope.accountId)),receipts=tx.objectStore('receipts').getAll(range(p.scope.accountId)),intents=tx.objectStore(NOTE_INTENT_STORE).getAll(range(p.scope.accountId));let n=0
      const finish=()=>{if(++n!==5)return;try{if(!p.current())fail('closed');const rows=incoming.result.map(r=>validateBrowserInboxRecord(r,p.scope));const committedReplay=!p.dormant&&!p.replay&&same(rows,p.inventory.rows.map(r=>r.event_id===p.row.event_id?proofRow(r,p.proof):r));if(!same(rows,p.inventory.rows)&&!committedReplay||!same(binding.result,p.inventory.binding)||!same(out.result,p.inventory.out)||!same(receipts.result,p.inventory.receipts)||!same(intents.result.map(v=>validateNoteIntent(v,p.scope)),p.inventory.intents))fail('stale_source');if(p.inventory.binding.mode==='upload_existing')deriveInitialLegacyCohort(p.scope,p.inventory.binding,out.result,receipts.result)
        const write=()=>{if(!p.current())fail('closed');if(!p.dormant&&!p.replay&&!committedReplay){const r=tx.objectStore('inbox').put(proofRow(p.row,p.proof));r.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))}}const complete=()=>result(p.proof.outcome==='conflict_preserved'?'conflict_preserved':p.replay||committedReplay?'already_applied':p.proof.outcome);if(p.transportHook)scheduleNoteTransportCommit(tx,p.transportHook,complete,abort);else complete()}
        readBrowserSyncCursor(tx,p.scope,checkpoint=>{try{if(!same(checkpoint,p.inventory.checkpoint))fail('stale_cursor');commitHistoryChange(tx,p.scope,p.inventory.binding.project_id,p.proof.header.entity_id,p.inventory.history,p.historyNext,p.current,()=>{if(committedReplay)write();else if(p.source)scheduleProtectedNoteApply(tx,p.scope,p.source,write,abort);else if(p.sourceToken)assertLocalSourceInTransaction(tx,p.scope,p.sourceToken,write,abort);else write()},abort,p.transportHook)}catch(e){abort(e)}},abort)
      }catch(e){abort(e)}};[incoming,binding,out,receipts,intents].forEach(r=>r.onsuccess=finish)
    }).finally(()=>unsubscribe?.())
  }
  async apply(scope:BrowserSyncScope,sequence:number){return this.commit(await this.prepare(scope,sequence))}
}
