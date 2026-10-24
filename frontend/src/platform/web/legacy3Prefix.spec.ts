// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {continuationFixture} from './resolutionContinuation.testFixture'
import {BrowserResolutionPrefix,type GHistoryToken} from './resolutionPrefix'
import * as history from './resolutionHistorical'
import {scope} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'
import {BrowserV10OrdinaryApply} from './v10OrdinaryApply'
import {noteProofDigest} from './legacyNoteApply'
afterEach(()=>vi.restoreAllMocks())
const strategies=['choose_version','manual_merge','delete','keep_both'] as const
async function setup(strategy:typeof strategies[number]='keep_both',prefixFamilies?:{compressed:boolean}){
 const f=await continuationFixture(strategy,true,undefined,false,2,true,prefixFamilies);let active=true
 const create=(tx:BrowserSyncTransaction=f.f.transaction)=>new BrowserResolutionPrefix(tx,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const q=new BrowserResolutionPrefix(f.f.transaction,()=>active).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 return{...f,g:create(),q,create,close:()=>{active=false;f.close()}}
}
const result=async(f:Awaited<ReturnType<typeof setup>>)=>f.g.calculate(await f.g.prepare(scope))
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of strategies)it(`Legacy3 G ${strategy}, ordinary${protocol}/ID${compressed?1:0}: exact history and cursor-only commit`,async()=>{
 const f=await setup(strategy),initial=f.before()
 expect(await result(f)).toMatchObject({current_proven_prefix:0,candidate_proven_prefix:f.sequence,counts:{metadata:1,resolution:1},readOnly:true,ackAuthorized:false});expect(f.before()).toEqual(initial)
 const first=await f.receive({protocol,compressed,deleted:strategy==='delete'});await f.runtime.apply(scope,first.sequence)
 let last=first
 if(strategy==='keep_both'){last=await f.receive({id:'retained-note',protocol,compressed});await f.runtime.apply(scope,last.sequence)}
 const child=await f.receive({id:last.plaintext.note.id,parent:last.event_id,revision:5,deleted:true,protocol,compressed});await f.runtime.apply(scope,child.sequence)
 const before=f.before(),certificate=await f.g.prepare(scope),r=await f.g.calculate(certificate)
 expect(r).toMatchObject({candidate_proven_prefix:child.sequence,first_blocking_sequence:null,blocker:null,counts:{resolution:1,metadata:1}})
 expect(Object.values(r.counts).reduce((a,b)=>a+b,0)).toBe(child.sequence);expect(f.before()).toEqual(before)
 const commit=await f.g.prepareCommit(certificate);expect(await f.g.commit(commit)).toBe('advanced');expect(await f.g.commit(commit)).toBe('already_proven')
 const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=child.sequence;expect(f.before()).toEqual(expected)
 expect(await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))).toBe('no_progress')
 await expect(f.q.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(expected)
})
it('reauthenticates a later H outcome after committed G prefix',async()=>{
 const f=await setup();await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))
 const child=await f.receive({protocol:3,compressed:true}),before=f.before()
 expect(await result(f)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:child.sequence,blocker:'unproven_family'});expect(f.before()).toEqual(before)
 await f.runtime.apply(scope,child.sequence);expect(await result(f)).toMatchObject({current_proven_prefix:f.sequence,candidate_proven_prefix:child.sequence})
})
for(const compressed of [false,true])it(`actual pre-F Stage/StageOrder owners qualify ID${compressed?1:0}`,async()=>{
 const f=await setup('choose_version',{compressed}),child=await f.receive({protocol:3,compressed});await f.runtime.apply(scope,child.sequence)
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,first_blocking_sequence:null,counts:{resolution:1,metadata:2,stage:1,stage_order:1}});expect(f.before()).toEqual(before)
})
it('earliest missing row caps prefix; corruption inside a claimed prefix rejects',async()=>{
 const f=await setup(),first=await f.receive();await f.runtime.apply(scope,first.sequence)
 const gap=await f.receive({parent:first.event_id,revision:5,deleted:true}),later=await f.receive({parent:gap.event_id,revision:6,deleted:true})
 f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.server_sequence!==gap.sequence)
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:first.sequence,first_blocking_sequence:gap.sequence,blocker:'missing_sequence'});expect(f.before()).toEqual(before)
 ;(f.f.db.cursors[0] as any).proven_prefix=later.sequence;const corrupt=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(corrupt)
})
for(const protocol of [2,3] as const)it(`unresolved ordinary${protocol} H sibling stays unqualified`,async()=>{
 const f=await setup(),first=await f.receive({protocol});await f.runtime.apply(scope,first.sequence)
 const fork=await f.receive({protocol});expect(await f.runtime.apply(scope,fork.sequence)).toBe('conflict_preserved')
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:first.sequence,first_blocking_sequence:fork.sequence,blocker:'unproven_family'})
 await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)));const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=first.sequence;expect(f.before()).toEqual(expected)
})
for(const family of ['raw3','unknown','other-project','received'] as const)it(`unqualified ${family} event cannot be skipped`,async()=>{
 const f=await setup(),child=await f.receive({protocol:family==='raw3'||family==='unknown'?3:2,rawLegacyOn3:family==='raw3'}),row=f.f.db.inbox.at(-1) as any
 if(family==='unknown'||family==='other-project'){const w=JSON.parse(row.wire_item);if(family==='unknown')w.event.entity_type='document';else w.event.project_id='unrelated';row.wire_item=JSON.stringify(w)}
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:child.sequence,blocker:'unproven_family'});expect(f.before()).toEqual(before)
})
for(const field of ['root','proof','wire','envelope','role','parent','retained','source','member','metadata','bootstrap','generation','resource'] as const)it(`G rejects ${field} without mutation or invented blocker`,async()=>{
 const f=await setup(),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 const d=f.f.db,r=d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any,root=d.inbox.find((row:any)=>row.event_id===r.event_id) as any
 if(field==='root')d.legacyNoteHistory=d.legacyNoteHistory!.filter((h:any)=>h.record_kind!=='resolution')
 if(field==='proof'){root.resolution_proof.outcome_digest='0'.repeat(64);root.resolution_proof.outcome_digest=await noteProofDigest(root.resolution_proof)}
 if(field==='wire'){const w=JSON.parse(root.wire_item);w.object.ciphertext='AA';root.wire_item=JSON.stringify(w)}
 if(field==='envelope')r.evidence_envelope.ciphertext='AA'
 if(field==='role')(d.legacyNoteHistory!.find((h:any)=>h.record_kind==='head'&&h.note_id==='retained-note') as any).node_ref.result_role='original'
 if(field==='parent')d.legacyNoteHistory=d.legacyNoteHistory!.filter((h:any)=>h.event_id!==f.parents[0]!.event_id)
 if(field==='retained')(d.localNotes!.find((n:any)=>n.note_id==='retained-note') as any).envelope.ciphertext='AA'
 if(field==='source')(d.localProjects![0] as any).source_revision++
 if(field==='member')d.localNotes=d.localNotes!.filter((n:any)=>n.note_id!=='retained-note')
 if(field==='metadata')d.ownerHeads=[]
 if(field==='bootstrap')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
 if(field==='generation')d.legacyNoteHistory!.push({...r,event_id:crypto.randomUUID()})
 if(field==='resource')root.wire_item+=' '.repeat(17*1024*1024)
 const before=f.before();if(field==='metadata')expect(await result(f)).toMatchObject({candidate_proven_prefix:0,first_blocking_sequence:1,blocker:'unproven_family'});else await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const store of ['inbox','cursors','ownerHeads','localProjects','localNotes','legacyNoteHistory','projectBindings','legacyNoteIntents'] as const)it(`complete G CAS rejects ${store} drift`,async()=>{
 const f=await setup(),token=await f.g.prepareCommit(await f.g.prepare(scope)),d=f.f.db
 if(store==='cursors')(d.cursors[0] as any).pull_cursor++
 else if(store==='inbox')(d.inbox[0] as any).wire_item+=' '
 else if(store==='legacyNoteHistory')(d.legacyNoteHistory![0] as any).head_revision=999
 else if(store==='legacyNoteIntents')d.legacyNoteIntents!.push({record_version:2,account_id:scope.accountId} as never)
 else (d[store][0] as any).source_revision=999
 const before=f.before();await expect(f.g.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const kind of ['key','logout','profile','relogin','device'] as const)it(`G authority expires on ${kind}`,async()=>{
 const f=await setup(),token=await f.g.prepareCommit(await f.g.prepare(scope))
 if(kind==='key')f.f.lock();else if(kind==='logout')await f.f.auth.logout();else if(kind==='profile')f.close();else if(kind==='relogin')await f.f.auth.login('fixture','fixture');else vi.spyOn(f.f.auth,'isCurrent').mockReturnValue(false)
 const before=f.before();await expect(f.g.commit(token)).rejects.toThrow();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const key of ['accountId','canonicalUserId','deviceId'] as const)it(`wrong ${key} rejects G`,async()=>{
 const f=await setup(),before=f.before();await expect(f.g.prepare({...scope,[key]:crypto.randomUUID()})).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('private G request cannot cross H/Q/owner or be reused and cleans failures',async()=>{
 const f=await setup(),other=f.create(),original=history.authenticateGContinuationHistory
 await expect(original({} as GHistoryToken,f.g)).rejects.toThrow()
 vi.spyOn(history,'authenticateGContinuationHistory').mockImplementation(async(token,owner)=>{
  await expect(original(token,other)).rejects.toThrow();await expect(original(token,f.q)).rejects.toThrow();await expect(history.authenticateHContinuationHistory(token as never,f.runtime)).rejects.toThrow()
  const r=await original(token,owner);await expect(original(token,owner)).rejects.toThrow();return r
 })
 const before=f.before();expect(await result(f)).toMatchObject({counts:{resolution:1}});expect(f.before()).toEqual(before)
 vi.restoreAllMocks();let captured:Parameters<typeof original>|undefined
 vi.spyOn(history,'authenticateGContinuationHistory').mockImplementation(async(...args)=>{captured=args;f.close();return original(...args)})
 await expect(f.g.prepare(scope)).rejects.toThrow();await expect(original(...captured!)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('H diagnostics and G certificate cannot authorize Q, another G, commit or ACK',async()=>{
 const f=await setup(),h=await f.runtime.history(scope),g=await f.g.prepare(scope),before=f.before()
 for(const action of [()=>f.g.calculate(h as never),()=>f.g.commit(g as never),()=>f.q.calculate(g),()=>f.create().calculate(g),()=>f.f.proven.prepare(scope)])await expect(action()).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('transaction failure retains all stores and actual retry succeeds',async()=>{
 const f=await setup(),before=f.before(),tx:BrowserSyncTransaction=async(...args)=>{if(args[2]==='readwrite')throw Error('INJECTED_ABORT');return f.f.transaction(...args)}
 const g=f.create(tx);await expect(g.commit(await g.prepareCommit(await g.prepare(scope)))).rejects.toThrow();expect(f.before()).toEqual(before)
 expect(await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))).toBe('advanced')
})
it('Q retains the O/source-authority prerequisite',async()=>{
 const f=await setup(),child=await f.receive({id:'independent',parent:null,revision:1,protocol:3}),before=f.before()
 const o=new BrowserV10OrdinaryApply(f.f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await expect(o.apply(scope,child.sequence)).rejects.toThrow();await expect(f.q.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})

for(const family of ['stage','stage_order','other'] as const)it(`missing actual ${family} owner blocks the earliest account event`,async()=>{
 const f=await setup('choose_version',{compressed:true}),row=f.f.db.inbox.find((r:any)=>{const e=JSON.parse(r.wire_item).event;return family==='other'?e.project_id==='other':e.entity_type===family}) as any
 f.f.db.ownerHeads=f.f.db.ownerHeads!.filter((o:any)=>family==='other'?o.owner_id!=='other':o.owner_kind!==family)
 const before=f.before();const r=await result(f);expect(r.first_blocking_sequence).toBe(row.server_sequence);expect(r.blocker).toBe('unproven_family');expect(f.before()).toEqual(before)
})
it('a genuine additional received Resolution remains unqualified',async()=>{
 const f=await setup(),{sealResolutionFixture}=await import('./resolution.testFixture'),payload=structuredClone(f.resolution)
 payload.header.event_id=crypto.randomUUID();const object=await sealResolutionFixture(payload),sequence=f.sequence+1,event={...JSON.parse(f.received.wire_item).event,event_id:payload.header.event_id,server_sequence:sequence}
 await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event,object}],next_cursor:sequence,has_more:false}))
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:sequence,blocker:'unproven_family'});expect(f.before()).toEqual(before)
})

it('a caller cannot turn a Q runtime into the private G entry with a public flag',async()=>{
 const f=await setup(),before=f.before();Object.assign(f.q,{mixedSources:false,allowLegacy3:true})
 await expect(f.q.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('successful Legacy3 G remains negative-only reader readiness',async()=>{
 const f=await setup(),{BrowserNoteReaderReadiness}=await import('./noteReaderReadiness'),before=f.before()
 const value=await new BrowserNoteReaderReadiness(f.f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device).inspect(scope)
 expect(value).toMatchObject({readOnly:true,ready:false,declarationAllowed:false,writerAuthorized:false,serverGate:'not_checked'})
 expect(value.blockers).toContain('production_v10_reader_dispatch_incomplete');expect(f.before()).toEqual(before)
})
