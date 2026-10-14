import { openNoteTransport } from './noteTransport'
import { isDeferredNoteTransportCandidate, type VerifiedNoteTransportCommit } from './noteTransportPrerequisite'
import { openFrozenLocalVersion } from './noteUnsealedVersion'
import { canonical } from '@/cloud/projectMetadataCodec'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { decryptObjectBytes,type AccountMasterKey } from '@/crypto'
import { decodeBase64Url } from '@/api/base64url'
import { type NoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError } from './persistence'
import { noteProofDigest } from './legacyNoteApply'
import { immutableWireIdentity,snapshotBrowserSyncScope,type BrowserSyncScope,type BrowserSyncTransaction } from './syncDurability'
import { deriveInitialLegacyCohort } from './initialNoteCapture'
import { validateBrowserProjectBinding,type BrowserProjectBinding } from './projectBindings'
import { NOTE_HISTORY_STORE,validateNoteHistoryRecord,validateNoteHistorySet,noteFrontier,type BrowserNoteCandidate,type BrowserNoteHead,type BrowserNoteHistoryRecord,type BrowserNoteLocalVersion } from './noteHistoryRecords'
import { localId,localExact,validateLocalNote,type LocalNoteRecord } from './localAuthorityRecords'
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
export const historyRange=(scope:BrowserSyncScope,project?:string,note?:string)=>IDBKeyRange.bound([scope.accountId,...(project?[project]:[]),...(note?[note]:[])],[scope.accountId,...(project?[project]:[]),...(note?[note]:[]),[]])
function fail(code:'candidate_history_unavailable'|'corrupt_record'|'stale_authority'|'closed'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
export async function candidateDigest(c:BrowserNoteCandidate):Promise<string>{const {record_digest:_digest,...data}=c;return noteProofDigest(data)}
/** Internal writer material: only authenticated capture/apply/backfill opaque plans persist it. */
export async function makeHistoryCandidate(scope:BrowserSyncScope,binding:BrowserProjectBinding,protocol:2|3,source:string,item:unknown,plaintext:NoteSyncPlaintext,origin:BrowserNoteCandidate['origin'],projection:LocalNoteRecord|null,projectionDigest:string|null=null,mutationGeneration=1):Promise<BrowserNoteCandidate>{
 const wire_item=JSON.stringify(item),h=plaintext.header
 const candidate:BrowserNoteCandidate={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:h.project_id,note_id:h.entity_id,bootstrap_id:binding.bootstrap_id,record_kind:'candidate',record_id:h.event_id,event_id:h.event_id,source_device_id:source,protocol_version:protocol,origin,mutation_generation:origin==='peer'?null:mutationGeneration,header:structuredClone(h),wire_item,wire_digest:await noteProofDigest({protocol_version:protocol,item}),record_digest:'',projection:projection&&structuredClone(projection),projection_digest:projection?await noteProofDigest(projection):projectionDigest}
 candidate.record_digest=await candidateDigest(candidate);return validateNoteHistoryRecord(candidate,scope) as BrowserNoteCandidate
}
async function verifyProjection(scope:BrowserSyncScope,c:BrowserNoteCandidate,value:NoteSyncPlaintext,amk:AccountMasterKey):Promise<void>{
 const p=c.projection;if(!p)return;let nonce:Uint8Array|undefined,ciphertext:Uint8Array|undefined,bytes:Uint8Array|undefined
 try{nonce=decodeBase64Url(p.envelope.nonce);ciphertext=decodeBase64Url(p.envelope.ciphertext);bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:c.project_id,entityId:c.note_id,entityType:'note'},{crypto_version:1,aad_version:1,nonce,ciphertext})
  const raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes),opened=JSON.parse(raw)
  if(canonical(opened)!==raw||!localExact(opened,['local_format','kind','account_id','device_id','project_id','note_id','source_revision','source'])||opened.local_format!==1||opened.kind!=='note'||opened.account_id!==scope.accountId||opened.device_id!==scope.deviceId||opened.project_id!==c.project_id||opened.note_id!==c.note_id||opened.source_revision!==p.source_revision)fail()
  const source=validateLocalNote(opened.source,c.project_id);if(source.note.id!==c.note_id||(source.state==='tombstone')!==p.deleted||(source.state==='live'?source.note.revision:source.revision)!==p.note_revision||(value.mutation==='delete')!==(source.state==='tombstone'))fail()
  const local={...source.note} as Record<string,unknown>;delete local.revision;const remote={...value.note} as Record<string,unknown>
  for(const field of value.mutation==='delete'?['deleted_at']:['created_at','updated_at']){local[field]=canonicalizeSyncTimestamp(local[field] as string);remote[field]=canonicalizeSyncTimestamp(remote[field] as string)}
  if(!same(local,remote))fail()
 }finally{bytes?.fill(0);nonce?.fill(0);ciphertext?.fill(0)}
}
export async function openHistoryCandidate(scope:BrowserSyncScope,c:BrowserNoteCandidate,amk:AccountMasterKey):Promise<NoteSyncPlaintext>{
 validateNoteHistoryRecord(c,scope);const item=JSON.parse(c.wire_item)
 try{if(await candidateDigest(c)!==c.record_digest||await noteProofDigest({protocol_version:c.protocol_version,item})!==c.wire_digest)fail()
  const {plaintext:value,content}=await openNoteTransport(scope,amk,c.protocol_version,c.wire_item,c.record_version===1?'legacy':'content_note_v1')
  if(!same(value.header,c.header))fail()
  if(c.record_version===2){const p=c.transport_proof!,{proof_digest:_digest,...body}=p
   if(!content||content.dependencies.bootstrap_id!==c.bootstrap_id||await noteProofDigest(value)!==p.logical_digest||await noteProofDigest(body)!==p.proof_digest)fail()
  }
  if(c.projection!==null&&await noteProofDigest(c.projection)!==c.projection_digest)fail();await verifyProjection(scope,c,value,amk);return value
 }catch{return fail()}
}
export function nextNoteHead(scope:BrowserSyncScope,binding:BrowserProjectBinding,candidates:BrowserNoteCandidate[],linear:string,previous?:BrowserNoteHead):BrowserNoteHead{
 const c=candidates.find(c=>c.event_id===linear);if(!c)fail();const revision=(previous?.head_revision??0)+1;if(!Number.isSafeInteger(revision))fail()
 return validateNoteHistoryRecord({record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:binding.project_id,note_id:c.note_id,bootstrap_id:binding.bootstrap_id,record_kind:'head',record_id:'head',head_revision:revision,linear_head_event_id:linear,tip_event_ids:noteFrontier(candidates)},scope) as BrowserNoteHead
}
/** Synchronous SAME transaction scheduling. No raw public history put operation. */
export function commitHistoryChange(tx:IDBTransaction,scope:BrowserSyncScope,project:string,note:string,expected:BrowserNoteHistoryRecord[],next:BrowserNoteHistoryRecord[],current:()=>boolean,ready:()=>void,abort:(e:unknown)=>void,transport?:VerifiedNoteTransportCommit):void{
 const request=tx.objectStore(NOTE_HISTORY_STORE).getAll(historyRange(scope,project,note))
 request.onsuccess=()=>{try{if(!current())fail('closed');const actual=validateNoteHistorySet(scope,request.result).sort((a,b)=>{const x=`${a.record_kind}:${a.record_id}`,y=`${b.record_kind}:${b.record_id}`;return x<y?-1:x>y?1:0});if(same(actual,next)){ready();return}if(!same(actual,expected))fail('stale_authority');validateNoteHistorySet(scope,next)
  for(const r of next){const old=actual.find(a=>a.record_kind===r.record_kind&&a.record_id===r.record_id);if(old&&(r.record_kind==='candidate'||r.record_kind==='local_version')&&!same(old,r))fail();if(old&&r.record_kind==='head'&&!same(old,r)&&r.head_revision!==(old as BrowserNoteHead).head_revision+1)fail();if(!same(old,r)&&!isDeferredNoteTransportCandidate(transport,r)){const w=tx.objectStore(NOTE_HISTORY_STORE).put(r);w.onsuccess=()=>{if(!current())abort(new BrowserPersistenceError('closed'))}}}
  if(actual.some(r=>!next.some(n=>n.record_kind===r.record_kind&&n.record_id===r.record_id)))fail();ready()
 }catch(e){abort(e)}}
}
export interface VerifiedNoteBackfill {readonly verifiedNoteBackfill:unique symbol}
interface Backfill {owner:BrowserLegacyNoteHistoryRuntime;scope:BrowserSyncScope;binding:BrowserProjectBinding;out:unknown[];receipts:unknown[];history:BrowserNoteHistoryRecord[];candidates:BrowserNoteCandidate[];current:()=>boolean}
const backfills=new WeakMap<object,Backfill>()
export class BrowserLegacyNoteHistory {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly sessionCurrent:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext){return new BrowserLegacyNoteHistoryRuntime(this.transaction,this.sessionCurrent,auth,bindings,keys)}
}
export class BrowserLegacyNoteHistoryRuntime {
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly sessionCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext){}
 private async guard(scope:BrowserSyncScope){if(!this.sessionCurrent()||this.auth.state!=='authenticated')fail('closed');const {context}=await this.bindings.ensureForCurrentUser(scope.accountId),lease=this.keys.leaseForAccount(scope.accountId),current=()=>this.sessionCurrent()&&this.auth.isCurrent(context)&&!!lease?.isCurrent();if(!lease||context.userId!==scope.canonicalUserId||lease.localAccountId!==scope.accountId||lease.canonicalUserId!==scope.canonicalUserId||lease.authEpoch!==context.authEpoch||!current())throw new BrowserPersistenceError('account_mismatch');return{lease,current}}
 async read(scope:BrowserSyncScope,project:string,note:string):Promise<BrowserNoteHistoryRecord[]>{scope=snapshotBrowserSyncScope(scope);localId(project);localId(note);const {current}=await this.guard(scope);return this.transaction(scope,[NOTE_HISTORY_STORE],'readonly',(tx,result,abort)=>{const r=tx.objectStore(NOTE_HISTORY_STORE).getAll(historyRange(scope,project,note));r.onsuccess=()=>{try{if(!current())fail('closed');result(validateNoteHistorySet(scope,r.result))}catch(e){abort(e)}}})}
 async withDecryptedCandidate<T>(scope:BrowserSyncScope,project:string,note:string,event:string,consume:(value:NoteSyncPlaintext)=>Promise<T>):Promise<T>{scope=snapshotBrowserSyncScope(scope);const {lease,current}=await this.guard(scope),rows=await this.read(scope,project,note),c=rows.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===event);if(!c)fail('candidate_history_unavailable');return lease.use(async amk=>{const value=await openHistoryCandidate(scope,c,amk);if(!current())fail('closed');const result=await consume(value);if(!current())fail('closed');return result})}
 async withDecryptedLocalVersion<T>(scope:BrowserSyncScope,project:string,note:string,id:string,consume:(value:NoteSyncPlaintext)=>Promise<T>):Promise<T>{scope=snapshotBrowserSyncScope(scope);const {lease,current}=await this.guard(scope),rows=await this.read(scope,project,note),v=rows.find((r):r is BrowserNoteLocalVersion=>r.record_kind==='local_version'&&r.version_id===id);if(!v)fail('candidate_history_unavailable');return lease.use(async amk=>{const value=await openFrozenLocalVersion(scope,v,amk);if(!current())fail('closed');const result=await consume(value);if(!current())fail('closed');return result})}
 async prepareInitialBackfill(scope:BrowserSyncScope,project:string):Promise<VerifiedNoteBackfill>{
  scope=snapshotBrowserSyncScope(scope);const {lease,current}=await this.guard(scope)
  const state=await this.transaction<{binding:BrowserProjectBinding;out:unknown[];receipts:unknown[];history:BrowserNoteHistoryRecord[]}>(scope,['projectBindings','outbox','receipts',NOTE_HISTORY_STORE],'readonly',(tx,result,abort)=>{const b=tx.objectStore('projectBindings').get([scope.accountId,project]),out=tx.objectStore('outbox').getAll(historyRange(scope)),receipts=tx.objectStore('receipts').getAll(historyRange(scope)),history=tx.objectStore(NOTE_HISTORY_STORE).getAll(historyRange(scope,project));let n=0;const done=()=>{if(++n!==4)return;try{result({binding:validateBrowserProjectBinding(b.result,scope),out:out.result,receipts:receipts.result,history:validateNoteHistorySet(scope,history.result)})}catch(e){abort(e)}};[b,out,receipts,history].forEach(r=>r.onsuccess=done)})
  const cohort=deriveInitialLegacyCohort(scope,state.binding,state.out,state.receipts),candidates=await lease.use(async amk=>{const result:BrowserNoteCandidate[]=[];for(const out of cohort.rows){const item=JSON.parse(out.raw_body).items[0],existing=state.history.find((r):r is BrowserNoteCandidate=>r.record_kind==='candidate'&&r.event_id===out.event_id);if(existing){await openHistoryCandidate(scope,existing,amk);if(existing.wire_item!==JSON.stringify(item))fail();continue}
    const skeleton={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,project_id:project,note_id:item.event.entity_id,bootstrap_id:state.binding.bootstrap_id,record_kind:'candidate',record_id:out.event_id,event_id:out.event_id,source_device_id:scope.deviceId,protocol_version:out.protocol_version,origin:'initial_backfill',mutation_generation:1,header:{...item.event,parent_event_id:null},wire_item:JSON.stringify(item),wire_digest:await noteProofDigest({protocol_version:out.protocol_version,item}),record_digest:'',projection:null,projection_digest:null} as BrowserNoteCandidate
    skeleton.record_digest=await candidateDigest(skeleton);const decoded=await openHistoryCandidate(scope,skeleton,amk);result.push(await makeHistoryCandidate(scope,state.binding,out.protocol_version,scope.deviceId,item,decoded,'initial_backfill',null))
   }return result})
  if(!current())fail('closed');const token=Object.freeze({}) as VerifiedNoteBackfill;backfills.set(token,{owner:this,scope,...state,candidates,current});return token
 }
 async commitInitialBackfill(token:VerifiedNoteBackfill):Promise<number>{const p=backfills.get(token);if(!p||p.owner!==this)fail('candidate_history_unavailable');if(!p.current())fail('closed');let unsubscribe:(()=>void)|undefined
  return this.transaction<number>(p.scope,['projectBindings','outbox','receipts',NOTE_HISTORY_STORE],'readwrite',(tx,result,abort)=>{unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')));const b=tx.objectStore('projectBindings').get([p.scope.accountId,p.binding.project_id]),out=tx.objectStore('outbox').getAll(historyRange(p.scope)),receipts=tx.objectStore('receipts').getAll(historyRange(p.scope)),history=tx.objectStore(NOTE_HISTORY_STORE).getAll(historyRange(p.scope,p.binding.project_id));let n=0;const done=()=>{if(++n!==4)return;try{if(!p.current())fail('closed');if(!same(b.result,p.binding)||!same(out.result,p.out)||!same(receipts.result,p.receipts)||!same(history.result,p.history))fail('stale_authority');deriveInitialLegacyCohort(p.scope,p.binding,out.result,receipts.result);for(const c of p.candidates){const r=tx.objectStore(NOTE_HISTORY_STORE).add(c);r.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))}}result(p.candidates.length)}catch(e){abort(e)}};[b,out,receipts,history].forEach(r=>r.onsuccess=done)}).finally(()=>unsubscribe?.())
 }
 async backfillInitial(scope:BrowserSyncScope,project:string){return this.commitInitialBackfill(await this.prepareInitialBackfill(scope,project))}
}
