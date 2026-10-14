import type {NormalUserAuthRuntime}from'@/auth/userAuth'
import type {AuthoritativeAccountBinding}from'@/auth/accountBinding'
import type {RuntimeKeyContext}from'@/auth/keyContext'
import{BrowserPersistenceError}from'./persistence'
import{snapshotBrowserSyncScope,immutableWireIdentity,readBrowserSyncCursor,validateBrowserInboxRecord,type BrowserSyncScope,type BrowserSyncTransaction}from'./syncDurability'
import{openHistoryCandidate}from'./noteHistory'
import{openFrozenLocalVersion}from'./noteUnsealedVersion'
import{validateNoteHistorySet}from'./noteHistoryRecords'
import{verifyStoredNoteProof,openRetainedNote,noteOutcomeDigest,noteProofDigest}from'./legacyNoteApply'
import{validateBrowserProjectBinding}from'./projectBindings'
import{currentRegistryForPrefix,type VerifiedAccountRegistry}from'./accountRegistry'
import{PREFIX_STORES,calculateBrowserPrefix,type BrowserPrefixInventory,type BrowserPrefixResult}from'./provenPrefixRecords'
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
function fail(code:'closed'|'corrupt_record'|'stale_cursor'|'account_mismatch'='corrupt_record'):never{throw new BrowserPersistenceError(code)}
export interface VerifiedBrowserPrefix{readonly verifiedBrowserPrefix:unique symbol}
interface Plan{owner:BrowserProvenPrefixRuntime;scope:BrowserSyncScope;inventory:BrowserPrefixInventory;result:BrowserPrefixResult;current:()=>boolean}
const plans=new WeakMap<object,Plan>()
export class BrowserProvenPrefix{
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly current:()=>boolean){}
 bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext){return new BrowserProvenPrefixRuntime(this.transaction,this.current,auth,bindings,keys)}
}
export class BrowserProvenPrefixRuntime{
 constructor(private readonly transaction:BrowserSyncTransaction,private readonly sessionCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext){}
 private async guard(scope:BrowserSyncScope){if(!this.sessionCurrent()||this.auth.state!=='authenticated')fail('closed');const {context}=await this.bindings.ensureForCurrentUser(scope.accountId),lease=this.keys.leaseForAccount(scope.accountId),current=()=>this.sessionCurrent()&&this.auth.isCurrent(context)&&!!lease?.isCurrent();if(!lease||context.userId!==scope.canonicalUserId||lease.localAccountId!==scope.accountId||lease.canonicalUserId!==scope.canonicalUserId||lease.authEpoch!==context.authEpoch||!current())fail('account_mismatch');return{lease,current}}
 private read(tx:IDBTransaction,scope:BrowserSyncScope,done:(v:BrowserPrefixInventory)=>void,abort:(e:unknown)=>void){const names=['inbox','outbox','receipts','projectBindings','ownerHeads','legacyNoteHistory'],requests=names.map(n=>tx.objectStore(n).getAll(IDBKeyRange.bound([scope.accountId],[scope.accountId,[]])));let count=0;const finish=()=>{if(++count!==requests.length)return;readBrowserSyncCursor(tx,scope,cursor=>{try{done({rows:requests[0]!.result,out:requests[1]!.result,receipts:requests[2]!.result,bindings:requests[3]!.result,owners:requests[4]!.result,history:requests[5]!.result,cursor:{pull_cursor:cursor.pull_cursor,ack_cursor:cursor.ack_cursor,proven_prefix:cursor.proven_prefix,next_local_ordinal:cursor.next_local_ordinal}})}catch(e){abort(e)}},abort)};requests.forEach(r=>r.onsuccess=finish)}
 async prepare(scope:BrowserSyncScope):Promise<VerifiedBrowserPrefix>{scope=snapshotBrowserSyncScope(scope);const{lease,current}=await this.guard(scope),inventory=await this.transaction<BrowserPrefixInventory>(scope,PREFIX_STORES,'readonly',(tx,result,abort)=>this.read(tx,scope,result,abort)),result=calculateBrowserPrefix(scope,inventory)
 await lease.use(async amk=>{for(const h of validateNoteHistorySet(scope,inventory.history)){if(h.record_kind==='candidate')await openHistoryCandidate(scope,h,amk);else if(h.record_kind==='local_version')await openFrozenLocalVersion(scope,h,amk)}for(const raw of inventory.rows){const row=validateBrowserInboxRecord(raw,scope);if(row.state==='note_proven')await verifyStoredNoteProof(scope,amk,row);else if(row.state==='note_conflict_preserved'){const decoded=await openRetainedNote(scope,amk,row),p=row.note_conflict_proof,wire=JSON.parse(row.wire_item);if(!same(decoded.header,p.header)||decoded.mutation!==p.mutation||await noteOutcomeDigest(p)!==p.outcome_digest||await noteProofDigest({protocol_version:row.protocol_version,event:wire.event,object:wire.object})!==p.wire_digest)fail()}}})
 if(!current())fail('closed');const token=Object.freeze({}) as VerifiedBrowserPrefix;plans.set(token,{owner:this,scope,inventory,result,current});return token}
 private plan(token:VerifiedBrowserPrefix){const p=plans.get(token);if(!p||p.owner!==this)fail();if(!p.current())fail('closed');return p}
 result(token:VerifiedBrowserPrefix):BrowserPrefixResult{return structuredClone(this.plan(token).result)}
 async calculate(scope:BrowserSyncScope){return this.result(await this.prepare(scope))}
 async commit(token:VerifiedBrowserPrefix):Promise<'advanced'|'already_proven'|'no_progress'>{const p=this.plan(token);let unsubscribe:(()=>void)|undefined;return this.transaction<'advanced'|'already_proven'|'no_progress'>(p.scope,PREFIX_STORES,'readwrite',(tx,result,abort)=>{unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')));this.read(tx,p.scope,v=>{if(!p.current())fail('closed');const target=p.result.candidate_proven_prefix,already=v.cursor.proven_prefix===target&&target>p.inventory.cursor.proven_prefix,expected=already?{...p.inventory,cursor:{...p.inventory.cursor,proven_prefix:target}}:p.inventory;if(!same(v,expected))fail('stale_cursor');const recalculated=calculateBrowserPrefix(p.scope,v);if(recalculated.candidate_proven_prefix!==target)fail('stale_cursor');if(already){result('already_proven');return}if(target===v.cursor.proven_prefix){result('no_progress');return}const write=tx.objectStore('cursors').put({record_version:1,account_id:p.scope.accountId,device_id:p.scope.deviceId,...v.cursor,proven_prefix:target});write.onsuccess=()=>{if(!p.current())abort(new BrowserPersistenceError('closed'))};result('advanced')},abort)}).finally(()=>unsubscribe?.())}
 async advance(scope:BrowserSyncScope){const token=await this.prepare(scope),status=await this.commit(token);return{status,...this.result(token)}}
 /** No network or ACK write. Mode/reader registration prerequisites are deliberately unavailable. */
 async ackStatus(scope:BrowserSyncScope,registry?:VerifiedAccountRegistry){scope=snapshotBrowserSyncScope(scope);const token=await this.prepare(scope),p=this.plan(token),v=p.inventory,candidate_ack_cursor=v.cursor.proven_prefix,current_ack_cursor=v.cursor.ack_cursor,bindings=v.bindings.map(b=>validateBrowserProjectBinding(b,scope)),required=Math.max(0,...bindings.map(b=>Math.max(b.remote_high_water??0,b.initial_max_server_sequence??0)));let code:string
 if(candidate_ack_cursor===current_ack_cursor)code=p.result.candidate_proven_prefix>candidate_ack_cursor?'safe_note_prefix_available':p.result.blocker??'no_ack_progress';else if(!currentRegistryForPrefix(registry,scope,bindings))code='registry_reconciliation_required';else if(v.cursor.pull_cursor<required)code='pull_required';else code='ack_transport_unavailable'
 return{code,current_ack_cursor,candidate_ack_cursor,proven_prefix:v.cursor.proven_prefix,...p.result,ack_eligible:false as const,ready:false as const}}
}
