import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { decodeBase64Url } from '@/api/base64url'
import { decryptObjectBytes, type AccountMasterKey } from '@/crypto'
import { decodeNoteSyncPlaintext, noteSyncEligibility, type NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { BrowserPersistenceError, type BrowserPersistenceCode } from './persistence'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { immutableWireIdentity, readBrowserSyncCursor, snapshotBrowserSyncScope, validateBrowserInboxRecord, validateBrowserUploadPair, type BrowserSyncScope, type BrowserSyncTransaction, type BrowserInboxRecord, type BrowserSyncCheckpoint } from './syncDurability'
import { BrowserLocalAuthority, assertLocalSourceInTransaction, scheduleProtectedNoteApply, type BrowserLocalAuthorityRuntime, type ProtectedNoteSourcePlan, type LocalSourceToken } from './localAuthority'
import { validateBrowserNoteProof, type BrowserNoteProof } from './noteApplyRecords'
import { deriveInitialLegacyCohort } from './initialNoteCapture'

export interface VerifiedLegacyNotePlan {readonly verifiedLegacyNotePlan:unique symbol}
interface Inventory {checkpoint:BrowserSyncCheckpoint;binding:BrowserProjectBinding;rows:BrowserInboxRecord[];out:unknown[];receipts:unknown[]}
interface Plan {owner:BrowserLegacyNoteApplyRuntime;scope:BrowserSyncScope;inventory:Inventory;row:BrowserInboxRecord;proof:BrowserNoteProof;current:()=>boolean;local:BrowserLocalAuthorityRuntime;plaintext?:NoteSyncPlaintext;source?:ProtectedNoteSourcePlan;sourceToken?:LocalSourceToken;replay:boolean}
const plans=new WeakMap<object,Plan>()
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const range=(a:string)=>IDBKeyRange.bound([a],[a,[]])
function fail(code:BrowserPersistenceCode):never{throw new BrowserPersistenceError(code)}
export async function noteProofDigest(value:unknown):Promise<string>{const bytes=new TextEncoder().encode(immutableWireIdentity(value));let digest:Uint8Array|undefined;try{digest=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));return Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('')}finally{bytes.fill(0);digest?.fill(0)}}
async function noteOutcomeDigest(p:BrowserNoteProof):Promise<string>{const {outcome_digest:_digest,...body}=p;return noteProofDigest(body)}
async function openRetainedNote(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord):Promise<NoteSyncPlaintext>{
  const wire=JSON.parse(row.wire_item),r=wire.event;let nonce:Uint8Array|undefined,ciphertext:Uint8Array|undefined,bytes:Uint8Array|undefined
  try{nonce=decodeBase64Url(wire.object.nonce);ciphertext=decodeBase64Url(wire.object.ciphertext);bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:r.project_id,entityId:r.entity_id,entityType:'note'},{crypto_version:wire.object.crypto_version,aad_version:wire.object.aad_version,nonce,ciphertext})
    const value=decodeNoteSyncPlaintext(bytes),h=value.header
    if(!noteSyncEligibility(value).eligible||value.note.stage_id!==null||value.note.source_type!=='project'||value.note.source_map_id!==null||value.note.source_node_id!==null)fail('unsupported_local_source')
    if(h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.entity_id||h.operation!==r.operation||h.revision!==r.revision||canonicalizeSyncTimestamp(h.updated_at)!==canonicalizeSyncTimestamp(r.updated_at)||(h.deleted_at===null)!==(r.deleted_at===null)||h.deleted_at!==null&&canonicalizeSyncTimestamp(h.deleted_at)!==canonicalizeSyncTimestamp(r.deleted_at))fail('note_rejected')
    return value
  }catch(e){if(e instanceof BrowserPersistenceError)throw e;return fail('note_rejected')}finally{nonce?.fill(0);ciphertext?.fill(0);bytes?.fill(0)}
}
async function verifyStoredNoteProof(scope:BrowserSyncScope,amk:AccountMasterKey,row:BrowserInboxRecord):Promise<void>{
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
  private load(scope:BrowserSyncScope,sequence:number):Promise<Inventory>{return this.transaction(scope,['inbox','projectBindings','outbox','receipts','cursors'],'readonly',(tx,result,abort)=>{
    const incoming=tx.objectStore('inbox').getAll(range(scope.accountId)),bindings=tx.objectStore('projectBindings').getAll(range(scope.accountId)),out=tx.objectStore('outbox').getAll(range(scope.accountId)),receipts=tx.objectStore('receipts').getAll(range(scope.accountId));let n=0;const finish=()=>{if(++n!==4)return;try{const rows=incoming.result.map(r=>validateBrowserInboxRecord(r,scope)),row=rows.find(r=>r.server_sequence===sequence);if(!row)fail('missing_history');const e=JSON.parse(row.wire_item).event;if(e.entity_type!=='note'||!['upsert','delete'].includes(e.operation))fail('unsupported_local_source');const binding=bindings.result.find(b=>b.project_id===e.project_id);if(!binding)fail('ineligible_lineage');readBrowserSyncCursor(tx,scope,checkpoint=>{try{if(sequence>checkpoint.pull_cursor)fail('corrupt_record');result({checkpoint,binding:validateBrowserProjectBinding(binding,scope),rows,out:out.result,receipts:receipts.result})}catch(e){abort(e)}},abort)}catch(e){abort(e)}};[incoming,bindings,out,receipts].forEach(r=>r.onsuccess=finish)
  })}
  async prepare(scope:BrowserSyncScope,sequence:number):Promise<VerifiedLegacyNotePlan>{
    scope=snapshotBrowserSyncScope(scope);if(!Number.isSafeInteger(sequence)||sequence<1)fail('missing_history');const {lease,current}=await this.guard(scope),inventory=await this.load(scope,sequence),row=inventory.rows.find(r=>r.server_sequence===sequence)!,binding=inventory.binding
    if(binding.remote_state!=='active'||!(binding.mode==='import_remote'&&binding.phase==='captured'||binding.mode==='upload_existing'&&binding.phase==='completing'))fail('ineligible_lineage')
    if(binding.mode==='upload_existing')deriveInitialLegacyCohort(scope,binding,inventory.out,inventory.receipts)
    const wire=JSON.parse(row.wire_item),reference=wire.event,digest=await noteProofDigest({protocol_version:row.protocol_version,event:reference,object:wire.object})
    if(row.state==='applied')fail('corrupt_record')
    if(row.state==='note_proven'){
      const proof=validateBrowserNoteProof(row.note_proof,scope);if(proof.outcome==='self_echo_applied')requireOwnReceipt(scope,inventory,row);if(proof.bootstrap_id!==binding.bootstrap_id||proof.wire_digest!==digest)fail('corrupt_record');await lease.use(amk=>verifyStoredNoteProof(scope,amk,row));if(!current())fail('closed');const token=Object.freeze({}) as VerifiedLegacyNotePlan;plans.set(token,{owner:this,scope,inventory,row,proof,current,local:this.local,replay:true});return token
    }
    return lease.use(async amk=>{
      try{
        const plaintext=await openRetainedNote(scope,amk,row),h=plaintext.header
        const notes=inventory.rows.filter(r=>r.state==='note_proven'&&r.note_proof.header.project_id===h.project_id&&r.note_proof.header.entity_id===h.entity_id)
        for(const history of notes)await verifyStoredNoteProof(scope,amk,history)
        const heads=notes.map(r=>{if(r.state!=='note_proven')fail('corrupt_record');if(r.note_proof.bootstrap_id!==binding.bootstrap_id)fail('corrupt_record');return{event:r.event_id,revision:r.note_proof.header.revision,row:r}})
        const outgoing=inventory.out.map(v=>validateBrowserUploadPair(v,inventory.receipts.find(p=>(p as {event_id:string}).event_id===(v as {event_id:string}).event_id),scope)).filter(r=>{const e=JSON.parse(r.raw_body).items[0].event;return e.project_id===h.project_id&&e.entity_id===h.entity_id&&e.entity_type==='note'})
        outgoing.forEach(r=>{const e=JSON.parse(r.raw_body).items[0].event;if(!['upsert','delete'].includes(e.operation))fail('unsupported_local_source');heads.push({event:e.event_id,revision:e.revision,row:undefined as never})})
        const max=Math.max(0,...heads.map(h=>h.revision)),top=heads.filter(h=>h.revision===max);if(new Set(top.map(h=>h.event)).size>1)fail('note_conflict_unproven')
        const own=reference.device_id===scope.deviceId
        if(own){requireOwnReceipt(scope,inventory,row);if(notes.some(r=>r.state==='note_proven'&&r.note_proof.header.revision===h.revision&&r.event_id!==h.event_id))fail('note_conflict_unproven')}
        else if(h.revision===1?max!==0:h.revision!==max+1||!top.some(t=>t.event===h.parent_event_id))fail(max<h.revision-1?'note_orphan':'note_conflict_unproven')
        const proof:BrowserNoteProof={record_version:1,owner_kind:'legacy_note',outcome:own?'self_echo_applied':'applied',account_id:scope.accountId,bootstrap_id:binding.bootstrap_id,protocol_version:row.protocol_version,reference:structuredClone(reference),header:structuredClone(h),mutation:plaintext.mutation,wire_digest:digest,outcome_digest:'',source_revision:null,local_note_digest:null}
        const token=Object.freeze({}) as VerifiedLegacyNotePlan,p:Plan={owner:this,scope,inventory,row,proof,current,local:this.local,plaintext,replay:false};plans.set(token,p)
        try{const source=await this.local.readSnapshot(scope,binding.project_id);p.sourceToken=source.token
          if(!own){const parent=notes.find(r=>r.event_id===h.parent_event_id);await this.local.withDecryptedSnapshot(scope,source.token,async data=>{const local=data.notes.find(n=>n.note.id===h.entity_id),record=source.notes.find(n=>n.note_id===h.entity_id);if(h.revision===1){if(local)fail('note_conflict_unproven')}
            else if(parent?.state==='note_proven'&&parent.note_proof.outcome==='applied'){if(!record||await noteProofDigest(record)!==parent.note_proof.local_note_digest)fail('note_conflict_unproven')}
            else fail('self_echo_unavailable') // No native unsealed-generation history for a peer child of own outbox yet.
          });const prepared=await this.local.prepareProtectedNoteApply(scope,source.token,token);p.source=prepared.token;proof.source_revision=prepared.source_revision;proof.local_note_digest=await noteProofDigest(prepared.note)}
          proof.outcome_digest=await noteOutcomeDigest(proof);validateBrowserNoteProof(proof,scope);if(!current())fail('closed');return token
        }finally{delete p.plaintext}
      }catch(e){if(e instanceof BrowserPersistenceError)throw e;fail('note_rejected')}
    })
  }
  async commit(token:VerifiedLegacyNotePlan):Promise<'applied'|'self_echo_applied'|'already_applied'>{
    const p=plans.get(token);if(!p||p.owner!==this)fail('stale_source');if(!p.current())fail('closed');let unsubscribe:(()=>void)|undefined
    return this.transaction<'applied'|'self_echo_applied'|'already_applied'>(p.scope,['inbox','projectBindings','outbox','receipts','cursors','localProjects','localNotes'],'readwrite',(tx,result,abort)=>{
      unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')))
      const incoming=tx.objectStore('inbox').getAll(range(p.scope.accountId)),binding=tx.objectStore('projectBindings').get([p.scope.accountId,p.inventory.binding.project_id]),out=tx.objectStore('outbox').getAll(range(p.scope.accountId)),receipts=tx.objectStore('receipts').getAll(range(p.scope.accountId));let n=0
      const finish=()=>{if(++n!==4)return;try{if(!p.current())fail('closed');const rows=incoming.result.map(r=>validateBrowserInboxRecord(r,p.scope));const committedReplay=!p.replay&&same(rows,p.inventory.rows.map(r=>r.event_id===p.row.event_id?{...r,record_version:3,state:'note_proven',note_proof:p.proof}:r));if(!same(rows,p.inventory.rows)&&!committedReplay||!same(binding.result,p.inventory.binding)||!same(out.result,p.inventory.out)||!same(receipts.result,p.inventory.receipts))fail('stale_source');if(p.inventory.binding.mode==='upload_existing')deriveInitialLegacyCohort(p.scope,p.inventory.binding,out.result,receipts.result)
        const write=()=>{if(!p.current())fail('closed');if(!p.replay&&!committedReplay){const r=tx.objectStore('inbox').put({...p.row,record_version:3,state:'note_proven',note_proof:p.proof});r.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))}}result(p.replay||committedReplay?'already_applied':p.proof.outcome)}
        readBrowserSyncCursor(tx,p.scope,checkpoint=>{try{if(!same(checkpoint,p.inventory.checkpoint))fail('stale_cursor');if(committedReplay)write();else if(p.source)scheduleProtectedNoteApply(tx,p.scope,p.source,write,abort);else if(p.sourceToken)assertLocalSourceInTransaction(tx,p.scope,p.sourceToken,write,abort);else write()}catch(e){abort(e)}},abort)
      }catch(e){abort(e)}};[incoming,binding,out,receipts].forEach(r=>r.onsuccess=finish)
    }).finally(()=>unsubscribe?.())
  }
  async apply(scope:BrowserSyncScope,sequence:number){return this.commit(await this.prepare(scope,sequence))}
}
