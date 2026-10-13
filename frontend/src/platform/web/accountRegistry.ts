import { openFrozenLocalVersion } from './noteUnsealedVersion'
import { NOTE_HISTORY_STORE,validateNoteHistorySet } from './noteHistoryRecords'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { cloudProjectsApi, type CloudProjectBootstrapListResponse } from '@/api/cloudProjects'
import { BrowserPersistenceError } from './persistence'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { deriveInitialLegacyCohort } from './initialNoteCapture'
import { immutableWireIdentity, readBrowserSyncCursor, snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { browserAckPrerequisites, inspectBrowserAckInventory, type BrowserAckPrerequisites } from './ackPrerequisites'

export interface VerifiedAccountRegistry { readonly verifiedAccountRegistry: unique symbol }
export interface BrowserRegistryResult { bindings: readonly BrowserProjectBinding[]; unknown_projects: readonly string[]; unregistered_projects: readonly string[]; current_cursor:number; token:VerifiedAccountRegistry }
interface Proof {owner:BrowserAccountRegistryRuntime;scope:BrowserSyncScope;bindings:BrowserProjectBinding[];blocked:boolean;current:()=>boolean}
const proofs=new WeakMap<object,Proof>()
const same=(a:unknown,b:unknown)=>immutableWireIdentity(a)===immutableWireIdentity(b)
const range=(account:string)=>IDBKeyRange.bound([account],[account,[]])
const order=(a:BrowserProjectBinding,b:BrowserProjectBinding)=>a.project_id<b.project_id?-1:a.project_id>b.project_id?1:0
const safe=(v:unknown):v is number=>Number.isSafeInteger(v)&&(v as number)>=0
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)
const exact=(v:unknown,k:string[]):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===k.length&&k.every(key=>Object.hasOwn(v,key))
function fail(code:'registry_rejected'|'registry_conflict'|'stale_lineage'|'closed'|'registry_network_failed'='registry_rejected'):never{throw new BrowserPersistenceError(code)}
export function validateAccountRegistry(value:unknown):CloudProjectBootstrapListResponse {
  if(!exact(value,['projects','current_cursor'])||!safe(value.current_cursor)||!Array.isArray(value.projects)||value.projects.length>4096)fail()
  const ids=new Set<string>(),boots=new Set<string>()
  for(const p of value.projects){
    if(!exact(p,['project_id','bootstrap_id','origin_device_id','state','initial_event_count','initial_max_server_sequence'])||typeof p.project_id!=='string'||!p.project_id.length||p.project_id.length>512||ids.has(p.project_id))fail()
    ids.add(p.project_id)
    if(p.state==='legacy'){if(p.bootstrap_id!==null||p.origin_device_id!==null||p.initial_event_count!==null||p.initial_max_server_sequence!==null)fail()}
    else{
      if(!['initializing','active'].includes(p.state as string)||!uuid(p.bootstrap_id)||!uuid(p.origin_device_id)||boots.has(p.bootstrap_id))fail()
      boots.add(p.bootstrap_id)
      if(p.state==='initializing'){if(p.initial_event_count!==null||p.initial_max_server_sequence!==null)fail()}
      else if(!safe(p.initial_event_count)||!safe(p.initial_max_server_sequence)||(p.initial_event_count===0)!==(p.initial_max_server_sequence===0)||p.initial_max_server_sequence<p.initial_event_count||p.initial_max_server_sequence>value.current_cursor)fail()
    }
  }
  return structuredClone(value) as unknown as CloudProjectBootstrapListResponse
}
function targets(scope:BrowserSyncScope,rows:BrowserProjectBinding[],remote:CloudProjectBootstrapListResponse):{rows:BrowserProjectBinding[];unknown:string[];unregistered:string[]} {
  const unknown=remote.projects.filter(p=>!rows.some(r=>r.project_id===p.project_id)).map(p=>p.project_id).sort(),unregistered:string[]=[]
  const next=rows.map(old=>{
    const item=remote.projects.find(p=>p.project_id===old.project_id)
    if(!item){if(old.phase==='prepared'){unregistered.push(old.project_id);return old}fail('registry_conflict')}
    if(item.state==='legacy'||item.bootstrap_id!==old.bootstrap_id||remote.current_cursor<(old.remote_high_water??0)||old.remote_state==='active'&&item.state!=='active')fail('registry_conflict')
    if(old.mode==='upload_existing'){
      if(item.origin_device_id!==old.device_id)fail('registry_conflict')
      if(old.phase==='completing'){if(remote.current_cursor<old.initial_max_server_sequence!||item.state==='active'&&(item.initial_event_count!==old.initial_event_count||item.initial_max_server_sequence!==old.initial_max_server_sequence))fail('registry_conflict')}
      else if(item.state!=='initializing')fail('registry_conflict') // No missing local capture/completion proof synthesized.
    }else if(item.state!=='active')fail('registry_conflict') // Import has installation device, distinct remote origin.
    return validateBrowserProjectBinding({...old,phase:old.phase==='prepared'?'registered':old.phase,remote_state:item.state,remote_high_water:remote.current_cursor},scope)
  })
  return {rows:next,unknown,unregistered:unregistered.sort()}
}
export class BrowserAccountRegistry {
  constructor(private readonly transaction:BrowserSyncTransaction,private readonly sessionCurrent:()=>boolean){}
  bind(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,keys:RuntimeKeyContext):BrowserAccountRegistryRuntime{return new BrowserAccountRegistryRuntime(this.transaction,this.sessionCurrent,auth,bindings,keys)}
}
export class BrowserAccountRegistryRuntime {
  constructor(private readonly transaction:BrowserSyncTransaction,private readonly sessionCurrent:()=>boolean,private readonly auth:NormalUserAuthRuntime,private readonly bindings:AuthoritativeAccountBinding,private readonly keys:RuntimeKeyContext){}
  private async guard(scope:BrowserSyncScope):Promise<()=>boolean>{
    if(!this.sessionCurrent()||this.auth.state!=='authenticated')fail('closed')
    const {context}=await this.bindings.ensureForCurrentUser(scope.accountId),lease=this.keys.leaseForAccount(scope.accountId)
    if(!lease||context.userId!==scope.canonicalUserId||lease.localAccountId!==scope.accountId||lease.canonicalUserId!==context.userId||lease.authEpoch!==context.authEpoch)throw new BrowserPersistenceError('account_mismatch')
    const current=()=>this.sessionCurrent()&&this.auth.isCurrent(context)&&lease.isCurrent();if(!current())fail('closed');return current
  }
  private local(scope:BrowserSyncScope):Promise<BrowserProjectBinding[]>{return this.transaction(scope,['projectBindings'],'readonly',(tx,result,abort)=>{const r=tx.objectStore('projectBindings').getAll(range(scope.accountId));r.onsuccess=()=>{try{result(r.result.map(v=>validateBrowserProjectBinding(v,scope)).sort(order))}catch(e){abort(e)}}})}
  async reconcile(scope:BrowserSyncScope):Promise<BrowserRegistryResult>{
    scope=snapshotBrowserSyncScope(scope);const current=await this.guard(scope),old=await this.local(scope)
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000),unsub=this.auth.onInvalidated(()=>controller.abort())
    let remote:CloudProjectBootstrapListResponse
    try{if(!current())fail('closed');const response=await this.auth.authorized(token=>{if(!current())fail('closed');return cloudProjectsApi.listBootstraps(token,controller.signal)});if(!current()||response.context.userId!==scope.canonicalUserId)fail('closed');remote=validateAccountRegistry(response.value)}catch(e){if(!current())fail('closed');if(e instanceof BrowserPersistenceError)throw e;fail('registry_network_failed')}finally{clearTimeout(timeout);unsub()}
    const target=targets(scope,old,remote);let unsubscribe:(()=>void)|undefined
    const committed=await this.transaction<BrowserProjectBinding[]>(scope,['projectBindings','outbox','receipts'],'readwrite',(tx,result,abort)=>{
      unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')))
      const rows=tx.objectStore('projectBindings').getAll(range(scope.accountId)),out=tx.objectStore('outbox').getAll(range(scope.accountId)),receipts=tx.objectStore('receipts').getAll(range(scope.accountId));let n=0
      const finish=()=>{if(++n!==3)return;try{
        if(!current())fail('closed');const actual=rows.result.map(v=>validateBrowserProjectBinding(v,scope)).sort(order)
        if(!same(actual,old))fail('stale_lineage') // Full account set CAS, not independent item updates.
        for(const row of actual)if(row.mode==='upload_existing'&&row.phase==='completing')deriveInitialLegacyCohort(scope,row,out.result,receipts.result)
        target.rows.forEach((r,i)=>{if(!same(r,actual[i])){const w=tx.objectStore('projectBindings').put(r);w.onsuccess=()=>{if(!current())abort(new BrowserPersistenceError('closed'))}}});result(target.rows)
      }catch(e){abort(e)}};rows.onsuccess=finish;out.onsuccess=finish;receipts.onsuccess=finish
    }).finally(()=>unsubscribe?.())
    if(!current())fail('closed')
    const token=Object.freeze({}) as VerifiedAccountRegistry
    proofs.set(token,{owner:this,scope,bindings:structuredClone(committed),blocked:!!(target.unknown.length||target.unregistered.length),current})
    return Object.freeze({bindings:Object.freeze(committed),unknown_projects:Object.freeze(target.unknown),unregistered_projects:Object.freeze(target.unregistered),current_cursor:remote.current_cursor,token})
  }
  async ackPrerequisites(scope:BrowserSyncScope,projectId:string,token?:VerifiedAccountRegistry):Promise<BrowserAckPrerequisites>{
    scope=snapshotBrowserSyncScope(scope);const current=await this.guard(scope),proof=token&&proofs.get(token)
    const verifiedHistory=await this.transaction<unknown[]>(scope,[NOTE_HISTORY_STORE],'readonly',(tx,result,abort)=>{const r=tx.objectStore(NOTE_HISTORY_STORE).getAll(range(scope.accountId));r.onsuccess=()=>{try{if(!current())fail('closed');validateNoteHistorySet(scope,r.result);result(r.result)}catch(e){abort(e)}}})
    const frozen=validateNoteHistorySet(scope,verifiedHistory).filter(r=>r.record_kind==='local_version')
    if(frozen.length){const lease=this.keys.leaseForAccount(scope.accountId);if(!lease||!current())fail('closed');await lease.use(async amk=>{for(const v of frozen)await openFrozenLocalVersion(scope,v,amk)});if(!current())fail('closed')}
    return this.transaction(scope,['projectBindings','outbox','inbox','cursors','receipts','ownerHeads',NOTE_HISTORY_STORE],'readonly',(tx,result,abort)=>{
      const b=tx.objectStore('projectBindings').getAll(range(scope.accountId)),incoming=tx.objectStore('inbox').getAll(range(scope.accountId)),heads=tx.objectStore('ownerHeads').getAll(range(scope.accountId)),history=tx.objectStore(NOTE_HISTORY_STORE).getAll(range(scope.accountId));let n=0
      const finish=()=>{if(++n!==4)return;try{
        if(!current())fail('closed');if(!same(history.result,verifiedHistory))fail('registry_conflict');const rows=b.result.map(v=>validateBrowserProjectBinding(v,scope)).sort(order),row=rows.find(r=>r.project_id===projectId);if(!row)fail('registry_conflict')
        const registryCurrent=!!proof&&proof.owner===this&&same(proof.scope,scope)&&proof.current()&&!proof.blocked&&same(rows,proof.bindings)
        readBrowserSyncCursor(tx,scope,cursor=>{try{const inventory=inspectBrowserAckInventory(scope,cursor,incoming.result,heads.result,rows,history.result);if(!current())fail('closed');result(browserAckPrerequisites(row,cursor,inventory,registryCurrent))}catch(e){abort(e)}},abort)
      }catch(e){abort(e)}};b.onsuccess=finish;incoming.onsuccess=finish;heads.onsuccess=finish;history.onsuccess=finish
    })
  }
}
