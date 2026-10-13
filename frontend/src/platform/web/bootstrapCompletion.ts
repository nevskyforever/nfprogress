import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import { cloudProjectsApi, type CloudProjectBootstrapCompletion } from '@/api/cloudProjects'
import { BrowserPersistenceError } from './persistence'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'
import { deriveInitialLegacyCohort } from './initialNoteCapture'
import { immutableWireIdentity, snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'

const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b)
const range = (account: string) => IDBKeyRange.bound([account], [account, []])
const safe = (n: unknown): n is number => Number.isSafeInteger(n) && (n as number) >= 0
const exact = (v: unknown, keys: string[]): v is Record<string,unknown> => !!v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v,k))
function fail(code: 'closed' | 'stale_lineage' | 'invalid_lineage_transition' | 'bootstrap_incomplete' | 'bootstrap_response_rejected' | 'bootstrap_completion_failed' | 'corrupt_record'): never { throw new BrowserPersistenceError(code) }
export const BOOTSTRAP_COMPLETION_TIMEOUT_MS = 30_000
function completing(row: BrowserProjectBinding): void { if (row.mode !== 'upload_existing' || row.phase !== 'completing') fail('invalid_lineage_transition') }
/** Exact backend response, not HTTP2xx, proves remote active. No caller-supplied evidence commit API. */
export function validateBootstrapCompletionResponse(scope: BrowserSyncScope, expected: BrowserProjectBinding, value: unknown): BrowserProjectBinding {
  const old = validateBrowserProjectBinding(expected,scope); completing(old)
  if (!exact(value,['project','current_cursor']) || !safe(value.current_cursor) || !exact(value.project,['project_id','bootstrap_id','origin_device_id','state','initial_event_count','initial_max_server_sequence'])) fail('bootstrap_response_rejected')
  const p = value.project
  if (p.project_id !== old.project_id || p.bootstrap_id !== old.bootstrap_id || p.origin_device_id !== old.device_id || p.state !== 'active'
    || p.initial_event_count !== old.initial_event_count || p.initial_max_server_sequence !== old.initial_max_server_sequence
    || value.current_cursor < old.remote_high_water! || value.current_cursor < old.initial_max_server_sequence!) fail('bootstrap_response_rejected')
  return validateBrowserProjectBinding({...old,remote_state:'active',remote_high_water:value.current_cursor},scope)
}
export class BrowserBootstrapCompletion {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly sessionCurrent: () => boolean) {}
  bind(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, keys: RuntimeKeyContext): BrowserBootstrapCompletionRuntime { return new BrowserBootstrapCompletionRuntime(this.transaction,this.sessionCurrent,auth,bindings,keys) }
}
export class BrowserBootstrapCompletionRuntime {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly sessionCurrent: () => boolean, private readonly auth: NormalUserAuthRuntime, private readonly bindings: AuthoritativeAccountBinding, private readonly keys: RuntimeKeyContext) {}
  private async guard(scope: BrowserSyncScope): Promise<() => boolean> {
    if (!this.sessionCurrent() || this.auth.state !== 'authenticated') fail('closed')
    const {context} = await this.bindings.ensureForCurrentUser(scope.accountId), lease = this.keys.leaseForAccount(scope.accountId)
    const current = () => this.sessionCurrent() && this.auth.isCurrent(context) && !!lease?.isCurrent()
    if (!lease || context.userId !== scope.canonicalUserId || lease.canonicalUserId !== context.userId || lease.localAccountId !== scope.accountId || lease.authEpoch !== context.authEpoch) throw new BrowserPersistenceError('account_mismatch')
    if (!current()) fail('closed')
    return current
  }
  private async proof(scope: BrowserSyncScope, expected: BrowserProjectBinding, current: () => boolean): Promise<BrowserProjectBinding> {
    return this.transaction(scope,['projectBindings','outbox','receipts'],'readonly',(tx,result,abort) => {
      this.read(tx,scope,(row,out,receipts) => { try {
        if (!current()) fail('closed'); if (!same(row,expected)) fail('stale_lineage'); completing(row)
        deriveInitialLegacyCohort(scope,row,out,receipts); result(row)
      } catch(e) {abort(e)} },abort,expected.project_id)
    })
  }
  private read(tx: IDBTransaction, scope: BrowserSyncScope, consume: (row: BrowserProjectBinding, out: unknown[], receipts: unknown[]) => void, abort: (e: unknown) => void, projectId: string): void {
    // Project ID is supplied by the verified expected binding, never a registry sweep.
    const binding = tx.objectStore('projectBindings').get([scope.accountId,projectId]), out = tx.objectStore('outbox').getAll(range(scope.accountId)), receipts = tx.objectStore('receipts').getAll(range(scope.accountId))
    let count = 0
    const finish = () => { if (++count !== 3) return; try {consume(validateBrowserProjectBinding(binding.result,scope),out.result,receipts.result)} catch(e){abort(e)} }
    binding.onsuccess=finish;out.onsuccess=finish;receipts.onsuccess=finish
  }
  async markCompleting(scope: BrowserSyncScope, expected: BrowserProjectBinding): Promise<BrowserProjectBinding> {
    scope=snapshotBrowserSyncScope(scope);expected=validateBrowserProjectBinding(expected,scope)
    if (expected.mode !== 'upload_existing' || !['captured','completing'].includes(expected.phase)) fail('invalid_lineage_transition')
    const current=await this.guard(scope);let unsubscribe:(()=>void)|undefined
    return this.transaction<BrowserProjectBinding>(scope,['projectBindings','outbox','receipts'],'readwrite',(tx,result,abort)=>{
      unsubscribe=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')))
      this.read(tx,scope,(row,out,receipts)=>{try{
        if(!current())fail('closed')
        const status=deriveInitialLegacyCohort(scope,row,out,receipts).status
        if(!status.complete || status.accepted_count!==row.initial_event_count)fail('bootstrap_incomplete')
        if(expected.phase==='completing'&&!same(row,expected))fail('stale_lineage')
        const target=validateBrowserProjectBinding({...expected,phase:'completing',initial_max_server_sequence:status.max_server_sequence},scope)
        if(row.phase==='completing'){
          if(!same(row,target))fail('stale_lineage');result(row);return
        }
        if(row.mode!=='upload_existing'||row.phase!=='captured'||row.remote_state!=='initializing')fail('invalid_lineage_transition')
        if(!same(row,expected))fail('stale_lineage')
        const write=tx.objectStore('projectBindings').put(target)
        write.onsuccess=()=>{if(!current())abort(new BrowserPersistenceError('closed'))}
        result(target)
      }catch(e){abort(e)}},abort,expected.project_id)
    }).finally(()=>unsubscribe?.())
  }
  async completeRemote(scope: BrowserSyncScope, expected: BrowserProjectBinding): Promise<BrowserProjectBinding> {
    scope=snapshotBrowserSyncScope(scope);expected=validateBrowserProjectBinding(expected,scope);completing(expected)
    const current=await this.guard(scope), old=await this.proof(scope,expected,current)
    if(old.remote_state==='active')return old // Exact durable replay; no repeat HTTP/ready.
    const body:CloudProjectBootstrapCompletion={bootstrap_id:old.bootstrap_id,device_id:old.device_id,initial_event_count:old.initial_event_count,initial_max_server_sequence:old.initial_max_server_sequence!}
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),BOOTSTRAP_COMPLETION_TIMEOUT_MS)
    const unsubscribe=this.auth.onInvalidated(()=>controller.abort())
    let target:BrowserProjectBinding
    try{
      if(!current())fail('closed')
      const response=await this.auth.authorized(token=>{if(!current())fail('closed');return cloudProjectsApi.completeBootstrap(token,old.project_id,body,controller.signal)})
      if(!current()||response.context.userId!==scope.canonicalUserId)fail('closed')
      target=validateBootstrapCompletionResponse(scope,old,response.value)
    }catch(e){if(!current())fail('closed');if(e instanceof BrowserPersistenceError)throw e;fail('bootstrap_completion_failed')}
    finally{clearTimeout(timeout);unsubscribe()}
    // HTTP has finished. Never keep a transaction alive across the request.
    let unsub:(()=>void)|undefined
    return this.transaction<BrowserProjectBinding>(scope,['projectBindings','outbox','receipts'],'readwrite',(tx,result,abort)=>{
      unsub=this.auth.onInvalidated(()=>abort(new BrowserPersistenceError('closed')))
      this.read(tx,scope,(row,out,receipts)=>{try{
        if(!current())fail('closed')
        deriveInitialLegacyCohort(scope,row,out,receipts)
        if(same(row,target)){result(row);return}
        if(!same(row,old))fail('stale_lineage')
        const write=tx.objectStore('projectBindings').put(target)
        write.onsuccess=()=>{if(!current())abort(new BrowserPersistenceError('closed'))}
        result(target)
      }catch(e){abort(e)}},abort,old.project_id)
    }).finally(()=>unsub?.())
  }
}
