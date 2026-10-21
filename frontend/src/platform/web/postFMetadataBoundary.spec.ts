// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Recovery} from './v10Recovery'
import {scope} from './bootstrap.testFixture'

afterEach(()=>vi.restoreAllMocks())
it('a wholly Legacy F/H/O control still qualifies its genuine Metadata tombstone',async()=>{
 const f=await ordinaryV10Fixture('keep_both',2),o=await f.receive()
 await f.owner.apply(scope,o.sequence)
 const sequence=o.sequence+1,m=await metadataRow(f.f,sequence,{revision:2,parent:f.m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}})
 const before=f.before()
 expect(await f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)).toBe('applied')
 const g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 expect(await g.calculate(await g.prepare(scope))).toMatchObject({candidate_proven_prefix:sequence})
 expect(f.f.db.localProjects).toEqual(before.localProjects)
 expect(f.f.db.localNotes).toEqual(before.localNotes)
})
for(const protocol of [2,3] as const)for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)for(const compressed of protocol===2?[false]:[false,true])describe(`post-F Metadata deletion contract boundary F${protocol}/ID${compressed?1:0}/${strategy}`,()=>{
 let f:Awaited<ReturnType<typeof ordinaryV10Fixture>>
 beforeEach(async()=>{
  f=await ordinaryV10Fixture(strategy,protocol,compressed)
  const o=await f.receive('independent',null,1,false,{protocol:3,compressed:true})
  await f.owner.apply(scope,o.sequence)
 },5000)
 it('genuine owner tombstone invalidates retained Content authentication; mixed K must stay blocked',async()=>{
  const g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  await g.commit(await g.prepareCommit(await g.prepare(scope)))
  const updateSequence=(f.f.db.cursors[0] as {pull_cursor:number}).pull_cursor+1
  const update=await metadataRow(f.f,updateSequence,{revision:2,parent:f.m.event.header.event_id,compressed:true})
  // Positive control: a genuine compressed update remains historically readable.
  expect(await f.f.metadata.apply(scope,update.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)).toBe('applied')
  expect(await g.calculate(await g.prepare(scope))).toMatchObject({candidate_proven_prefix:updateSequence})
  await g.commit(await g.prepareCommit(await g.prepare(scope)))
  const sequence=updateSequence+1
  // The production compressor keeps this small tombstone in ID0. No padding or
  // fake proof is introduced to force ID1; the preceding real update uses ID1.
  const m=await metadataRow(f.f,sequence,{revision:3,parent:update.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}})
  const before=f.before(),k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  expect(await k.run(scope)).toMatchObject({applied:[],blocker:{sequence,reason:'post_F_structural_route'},ready:false})
  expect(f.before()).toEqual(before)
  // Disposable counterexample via the REAL existing owner, not a fabricated proof.
  expect(await f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)).toBe('applied')
  expect(f.f.db.inbox.find((r:any)=>r.event_id===m.event.header.event_id)).toMatchObject({state:'applied',applied_proof:{operation:'delete'}})
  expect(f.f.db.localProjects).toEqual(before.localProjects)
  expect(f.f.db.localNotes).toEqual(before.localNotes)
  expect(f.f.db.legacyNoteHistory).toEqual(before.legacyNoteHistory)
  const after=f.before(),code=protocol===2?'stale_authority':'corrupt_record'
  await expect(g.prepare(scope)).rejects.toMatchObject({code})
  await expect(k.run(scope)).rejects.toMatchObject({code})
  expect(f.before()).toEqual(after) // Rejected authentication cannot repair history.
 })
})
