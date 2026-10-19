// @vitest-environment node

import {afterEach,describe,it,expect,vi} from 'vitest'
import {plannerFixture} from './resolutionPlanner.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import {authenticateResolutionHistory} from './resolutionAuthentication'
import {type BrowserSyncTransaction} from './syncDurability'
import {BrowserResolutionPlanner,type ResolutionApplyToken} from './resolutionPlanner'
import type {LocalNoteSource,NativeLocalProject} from './localAuthorityRecords'
import * as objectCrypto from '@/crypto'
import {validateNoteHistorySet} from './noteHistoryRecords'
afterEach(()=>vi.restoreAllMocks())
const strategies=['choose_version','manual_merge','delete','keep_both'] as const
async function prepared(strategy:typeof strategies[number]='keep_both',legacy=false){
 const f=await plannerFixture(strategy,2,false,legacy),runtime=f.runtime.atomicApply(),plan=await f.runtime.prepare(scope,f.sequence),token=await runtime.prepare(plan.token)
 return{f,runtime,token,before:f.before()}
}
function inventory(f:Awaited<ReturnType<typeof plannerFixture>>){const d=f.f.db;return{history:d.legacyNoteHistory!,rows:d.inbox,bindings:d.projectBindings,owners:d.ownerHeads!,out:d.outbox,receipts:d.receipts,localNotes:d.localNotes,intents:d.legacyNoteIntents,cursor:d.cursors[0] as any}}
describe('dormant atomic Resolution-v2',()=>{
 for(const legacy of [false,true])for(const strategy of strategies)it(`${legacy?'protocol2':'protocol3'} ${strategy}: genuine commit / reader / zero-write replay`,async()=>{
  const {f,runtime,token,before}=await prepared(strategy,legacy)
  expect(f.before()).toEqual(before);expect(await runtime.commit(token)).toEqual({status:'applied'})
  const d=f.f.db,history=d.legacyNoteHistory as any[],row=d.inbox.find((r:any)=>r.server_sequence===f.sequence) as any
  expect(row.record_version).toBe(10);expect(row.wire_item).toBe(f.received.wire_item)
  expect(history.filter(r=>r.record_kind==='resolution')).toHaveLength(1)
  for(const kind of ['candidate','group','local_version'])expect(history.filter(r=>r.record_kind===kind)).toEqual(before.legacyNoteHistory!.filter((r:any)=>r.record_kind===kind))
  expect(history.filter(r=>r.record_kind==='group_transition')).toHaveLength(1)
  expect(history.filter(r=>r.record_kind==='head')).toHaveLength(strategy==='keep_both'?2:1)
  expect((d.localProjects![0] as any).source_revision).toBe((before.localProjects![0] as any).source_revision+1)
  expect(d.localNotes).toHaveLength(before.localNotes!.length+(strategy==='keep_both'?1:0))
  expect((await authenticateResolutionHistory(scope,inventory(f),amk,()=>true)).resolutions).toBe(1)
  for(const store of ['cursors','outbox','receipts','legacyNoteIntents'])expect(d[store]).toEqual(before[store])
  const after=f.before(),writes=f.f.calls.filter((c:any)=>c.mode==='readwrite').length
  expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
  expect(f.before()).toEqual(after);expect(f.f.calls.filter((c:any)=>c.mode==='readwrite')).toHaveLength(writes)
  expect(()=>validateNoteHistorySet(scope,history)).toThrow()
  const snapshot=await f.f.local.readSnapshot(scope,'p')
  await f.f.local.withDecryptedSnapshot(scope,snapshot.token,async (source:{project:NativeLocalProject;notes:readonly LocalNoteSource[];source_revision:number})=>{
   const original=source.notes.find(n=>n.note.id==='content-note')!
   expect(original.state).toBe(strategy==='delete'?'tombstone':'live')
   expect(original.state==='live'?original.note.revision:original.revision).toBe(0)
   if(strategy==='keep_both')expect(source.notes.find(n=>n.note.id==='retained-note')).toBeDefined()
  })
 })
 it('rejects forged and cross-runtime tokens',async()=>{
  const {f,runtime,token}=await prepared();await expect(runtime.commit({} as ResolutionApplyToken)).rejects.toThrow();await expect(f.runtime.atomicApply().commit(token)).rejects.toThrow();await expect(runtime.prepare({} as never)).rejects.toThrow()
 })
 for(const mutate of ['source','group','metadata','cursor','inbox','publication','intent','outbox','clone','binding'] as const)it(`CAS rejects changed ${mutate} before writes`,async()=>{
  const {f,runtime,token}=await prepared(),d=f.f.db
  if(mutate==='source')(d.localProjects![0] as any).source_revision++
  if(mutate==='group')(d.legacyNoteHistory!.find((h:any)=>h.record_kind==='group') as any).conflict_generation++
  if(mutate==='metadata')(d.ownerHeads![0] as any).head_revision++
  if(mutate==='cursor')(d.cursors[0] as any).pull_cursor++
  if(mutate==='inbox')(d.inbox.at(-1) as any).wire_item+=' '
  if(mutate==='publication')d.inbox.splice(1,1)
  if(mutate==='intent')d.legacyNoteIntents!.push({account_id:scope.accountId,event_id:'new'})
  if(mutate==='outbox')d.outbox.push({account_id:scope.accountId,event_id:'new'})
  if(mutate==='clone')d.localNotes!.push({...d.localNotes![0] as any,note_id:'retained-note',project_id:'other'})
  if(mutate==='binding')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  const changed=f.before();await expect(runtime.commit(token)).rejects.toThrow();expect(f.before()).toEqual(changed)
 })
 for(const invalidation of ['key','logout','profile'] as const)it(`rejects ${invalidation} invalidation`,async()=>{
  const {f,runtime,token}=await prepared();if(invalidation==='key')f.f.lock();else if(invalidation==='profile')f.close();else await f.f.auth.logout()
  const before=f.before();await expect(runtime.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 for(const part of ['resolution','group_transition','head','inbox','source','ciphertext','parent','sequence'] as const)it(`replay rejects corrupted ${part}`,async()=>{
  const {f,runtime,token}=await prepared();await runtime.commit(token);const d=f.f.db
  if(['resolution','group_transition','head'].includes(part))d.legacyNoteHistory=d.legacyNoteHistory!.filter((r:any)=>r.record_kind!==part)
  if(part==='inbox')d.inbox.pop()
  if(part==='source')(d.localNotes![0] as any).source_revision++
  if(part==='ciphertext'){const r=d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any;r.evidence_envelope.ciphertext=(r.evidence_envelope.ciphertext[0]==='A'?'B':'A')+r.evidence_envelope.ciphertext.slice(1)}
  if(part==='parent')d.inbox.splice(2,1)
  if(part==='sequence')(d.inbox.at(-1) as any).server_sequence++
  const before=f.before();await expect(runtime.reconcile(scope,f.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 for(let fault=0;fault<9;fault++)it(`failure at write boundary ${fault} preserves every store`,async()=>{
  const f=await plannerFixture('keep_both');let armed=false,n=0
  const transaction:BrowserSyncTransaction=(s,stores,mode,schedule)=>f.f.transaction(s,stores,mode,(tx:IDBTransaction,result:(v:any)=>void,abort:(e:unknown)=>void)=>{
   const proxy=new Proxy(tx,{get:(target,key)=>key==='objectStore'?(name:string)=>{
    const store=target.objectStore(name)
    return new Proxy(store,{get:(store,key)=>{
     const method=Reflect.get(store,key)
     if((key==='add'||key==='put')&&mode==='readwrite')return(...args:any[])=>{if(armed&&n++===fault)throw new DOMException('injected','QuotaExceededError');return method.apply(store,args)}
     return typeof method==='function'?method.bind(store):method
    }})
   }:Reflect.get(target,key)})
   schedule(proxy,result,abort)
  })
  const planner=new BrowserResolutionPlanner(transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),runtime=planner.atomicApply(),plan=await planner.prepare(scope,f.sequence),token=await runtime.prepare(plan.token),before=f.before();armed=true
  if(fault===8)f.f.abort()
  await expect(runtime.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
})

for(const route of [{stage:true},{format:'plain' as const},{compressed:true}])it(`genuine Content route ${JSON.stringify(route)}`,async()=>{
 const f=await plannerFixture('keep_both',2,false,false,route),runtime=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,f.sequence)
 await runtime.commit(await runtime.prepare(p.token));expect((await authenticateResolutionHistory(scope,inventory(f),amk,()=>true)).resolutions).toBe(1);expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
})
it('real accepted local frozen parent remains unchanged',async()=>{
 const f=await plannerFixture('choose_version',2,true),before=f.before(),runtime=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,f.sequence)
 await runtime.commit(await runtime.prepare(p.token));expect(f.f.db.outbox).toEqual(before.outbox);expect(f.f.db.receipts).toEqual(before.receipts);expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
})
for(const invalidate of ['key','logout','profile'] as const)it(`in-flight ${invalidate} aborts every pending write`,async()=>{
 const f=await plannerFixture('keep_both');let armed=false
 const transaction:BrowserSyncTransaction=(s,stores,mode,schedule)=>f.f.transaction(s,stores,mode,(tx:IDBTransaction,result:(v:any)=>void,abort:(e:unknown)=>void)=>{
  const proxy=new Proxy(tx,{get:(target,key)=>key==='objectStore'?(name:string)=>{
   const store=target.objectStore(name)
   return new Proxy(store,{get:(store,key)=>{
    const method=Reflect.get(store,key)
    if(key==='add'&&name==='legacyNoteHistory')return(...args:any[])=>{
     const request=method.apply(store,args)
     if(armed){let success:(()=>void)|null=null;Object.defineProperty(request,'onsuccess',{get:()=>()=>{if(invalidate==='key')f.f.lock();else if(invalidate==='logout')void f.f.auth.logout();else f.close();success?.()},set:value=>{success=value}})}
     return request
    }
    return typeof method==='function'?method.bind(store):method
   }})
  }:Reflect.get(target,key)})
  schedule(proxy,result,abort)
 })
 const planner=new BrowserResolutionPlanner(transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),runtime=planner.atomicApply(),p=await planner.prepare(scope,f.sequence),token=await runtime.prepare(p.token),before=f.before();armed=true
 await expect(runtime.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const missing of ['parent','publication','metadata','wire'] as const)it(`fresh preparation blocks ${missing} and preserves received row`,async()=>{
 const f=await plannerFixture(),plan=await f.runtime.prepare(scope,f.sequence),d=f.f.db
 if(missing==='parent')d.legacyNoteHistory=d.legacyNoteHistory!.filter((r:any)=>r.event_id!==f.resolution.header.parent_event_id)
 if(missing==='publication')d.inbox.splice(2,1)
 if(missing==='metadata')d.ownerHeads=[]
 if(missing==='wire'){const wire=JSON.parse(f.received.wire_item);wire.object.ciphertext=(wire.object.ciphertext[0]==='A'?'B':'A')+wire.object.ciphertext.slice(1);f.received.wire_item=JSON.stringify(wire)}
 const before=f.before();await expect(f.runtime.atomicApply().prepare(plan.token)).rejects.toThrow();expect(f.before()).toEqual(before)
})

it('replay never generates a fresh encryption nonce',async()=>{
 const {f,runtime,token}=await prepared();await runtime.commit(token)
 const encrypt=vi.spyOn(objectCrypto,'encryptObjectBytes').mockImplementation(async()=>{throw Error('replay encrypted')})
 expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'});expect(encrypt).not.toHaveBeenCalled()
})
it('new auth epoch rejects both commit and prior private handoff',async()=>{
 const {f,runtime,token}=await prepared();await f.f.auth.login('fixture','fixture');const before=f.before()
 await expect(runtime.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const count of [3,64])it(`genuine ${count}-parent apply preserves all publications`,async()=>{
 const f=await plannerFixture('choose_version',count),runtime=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,f.sequence)
 await runtime.commit(await runtime.prepare(p.token));expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
},30000)
it('keep_both accepts an authenticated future child reference without allocating its event',async()=>{
 const f=await plannerFixture('keep_both'),{contentRow}=await import('./noteTransport.testFixture')
 await contentRow(f.f,f.sequence+1,{id:'retained-note',mutation:'update',revision:4,parent:f.resolution.header.event_id})
 const child=structuredClone(f.f.db.inbox.at(-1)),runtime=f.runtime.atomicApply(),p=await f.runtime.prepare(scope,f.sequence)
 await runtime.commit(await runtime.prepare(p.token));expect(f.f.db.inbox.at(-1)).toEqual(child)
 expect((f.f.db.legacyNoteHistory as any[]).filter(r=>r.record_kind==='resolution')).toHaveLength(1)
 expect(await runtime.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
})
