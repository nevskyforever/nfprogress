// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {scope} from './bootstrap.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {bindPrivateMetadataHandoff,type PrivateMetadataHandoffPlan} from './importedMetadataApply'
import {resolutionInventoryStores} from './resolutionPlanner'
import {BrowserHistoricalPrefixQualification} from './historicalPrefixQualification'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Recovery} from './v10Recovery'
import type {BrowserSyncTransaction} from './syncDurability'
import * as readers from './canonicalReaders'

type Fixture=Awaited<ReturnType<typeof ordinaryV10Fixture>>
const create=(f:Fixture,tx:BrowserSyncTransaction=f.transaction,current=()=>true)=>bindPrivateMetadataHandoff(tx,current,f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
async function candidate(f:Fixture,operation:'update'|'delete'='update',protocol:2|3=3){
 const head=f.f.db.ownerHeads!.find((h:any)=>h.owner_kind==='project_metadata') as any,prior=head.history.find((p:any)=>p.event_id===head.tip_event_ids[0])
 const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:prior.revision+1,parent:prior.event_id,compressed:operation==='update',change:e=>{if(operation==='delete'){e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}}})
 // Sender chooses a genuine supported transport; no outcome or proof is inserted.
 ;(m.row as any).protocol_version=protocol;return m
}
const untouched=(before:ReturnType<Fixture['before']>,after:ReturnType<Fixture['before']>)=>{
 for(const name of ['localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','outbox','receipts','projectBindings','cursors'] as const)expect(after[name]).toEqual(before[name])
 expect(after.inbox.filter((r:any)=>r.state!=='applied')).toEqual(before.inbox.filter((r:any)=>r.state!=='applied'&&r.server_sequence!==(before.cursors[0] as any).pull_cursor))
}
afterEach(()=>vi.restoreAllMocks())
for(const protocol of [2,3] as const)for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`private owner F${protocol}/${strategy}`,()=>{
 let f:Fixture
 beforeEach(async()=>{f=await ordinaryV10Fixture(strategy,protocol,false)},5000)
 for(const operation of ['update','delete'] as const)it(`atomically commits genuine ${operation} with Metadata protocol3`,async()=>{
  const m=await candidate(f,operation,3),before=f.before(),writer=create(f)
  const nonce=vi.spyOn(crypto,'getRandomValues').mockImplementation(()=>{throw Error('NO_HANDOFF_NONCES')}),http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_HTTP'))
  const token=await writer.prepare(scope,m.reference.server_sequence);expect(f.before()).toEqual(before)
  expect(await writer.commit(token)).toEqual({status:'applied',ready:false,ackAuthorized:false,cursorCommitAuthorized:false})
  const after=f.before();untouched(before,after)
  const changed=Object.keys(before).filter(name=>JSON.stringify(before[name as keyof typeof before])!==JSON.stringify(after[name as keyof typeof after]));expect(changed.sort()).toEqual(['inbox','ownerHeads'])
  expect(after.inbox.find((r:any)=>r.event_id===m.reference.event_id)).toMatchObject({state:'applied',applied_proof:{event_id:m.reference.event_id,operation}})
  expect((after.inbox.find((r:any)=>r.event_id===m.reference.event_id) as any).wire_item).toBe(m.row.wire_item)
  expect(await writer.replay(scope,1)).toMatchObject({status:'already_applied'});expect(await create(f).replay(scope,m.reference.server_sequence)).toMatchObject({status:'already_applied'})
  await expect(writer.commit(token)).rejects.toMatchObject({code:'invalid_plan'});expect(f.before()).toEqual(after);expect(nonce).not.toHaveBeenCalled();expect(http).not.toHaveBeenCalled()
  if(operation==='delete'){
   const g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
   // With Content F (or later Content) the original STOP still applies.
   if(protocol===3){await expect(g.prepare(scope)).rejects.toThrow();await expect(k.run(scope)).rejects.toThrow()}
  }
 },5000)
})
describe('private plan CAS, rollback and revocation',()=>{
 let f:Fixture,m:Awaited<ReturnType<typeof candidate>>,writer:ReturnType<typeof create>,token:PrivateMetadataHandoffPlan
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{m=await candidate(f);writer=create(f);token=await writer.prepare(scope,m.reference.server_sequence)},5000)
 for(const name of resolutionInventoryStores)it(`full-account CAS rejects a changed ${name}`,async()=>{
  const map:Record<string,string>={inbox:'inbox',outbox:'outbox',receipts:'receipts',projectBindings:'projectBindings',ownerHeads:'ownerHeads',legacyNoteHistory:'legacyNoteHistory',legacyNoteIntents:'legacyNoteIntents',localProjects:'localProjects',localNotes:'localNotes',cursors:'cursors'},rows=f.f.db[map[name]! as keyof typeof f.f.db] as any[]
  // Negative tampering only; every positive fixture remains genuine.
  if(rows.length)rows[0].negative_race=true;else rows.push({account_id:scope.accountId,negative_race:true})
  const before=f.before();await expect(writer.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before);await expect(writer.commit(token)).rejects.toMatchObject({code:'invalid_plan'})
 },5000)
 it('preserves all ten stores after transaction rollback and consumes the plan',async()=>{
  f.f.abort();const before=f.before();await expect(writer.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before);f.f.abort(false)
  await expect(writer.commit(token)).rejects.toMatchObject({code:'invalid_plan'});expect(await writer.commit(await writer.prepare(scope,m.reference.server_sequence))).toMatchObject({status:'applied'})
 },5000)
 for(const mode of ['key','logout','epoch','device','profile'] as const)it(`rejects ${mode} lifecycle changes`,async()=>{
  let active=true
  if(mode==='device')writer=bindPrivateMetadataHandoff(f.transaction,()=>true,f.f.auth,f.f.bindings as never,f.f.keys as never,{} as never)
  else if(mode==='profile'){writer=create(f,f.transaction,()=>active);token=await writer.prepare(scope,m.reference.server_sequence);active=false}
  else if(mode==='key')f.f.lock();else if(mode==='logout')await f.f.auth.logout();else await f.f.auth.login('fixture','fixture')
  const before=f.before();await expect(mode==='device'?writer.prepare(scope,m.reference.server_sequence):writer.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('rejects public diagnostics and a foreign runtime plan',async()=>{
  const before=f.before(),oldOwnerPlan=await f.f.metadata.prepareVerified(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  await expect(writer.commit(oldOwnerPlan as never)).rejects.toMatchObject({code:'invalid_plan'})
  await expect(create(f).commit(token)).rejects.toMatchObject({code:'invalid_plan'})
  const publicReader=new BrowserHistoricalPrefixQualification(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  await expect(publicReader.inspect(scope)).rejects.toThrow() // Pending Metadata is NOT grandfathered by .15.
  for(const value of [{readOnly:true,commitAuthorized:false},Object.freeze({}),null])await expect(writer.commit(value as never)).rejects.toMatchObject({code:'invalid_plan'})
  expect(f.before()).toEqual(before);expect(await writer.commit(token)).toMatchObject({status:'applied'})
 },5000)
 it('reports durable commit when post-commit authentication fails, never false rollback',async()=>{
  let committed=false
  const tx:BrowserSyncTransaction=async(...args)=>{if(committed&&args[2]==='readonly')throw Error('POST_COMMIT_READ_FAILURE');const r=await f.transaction(...args);if(args[2]==='readwrite')committed=true;return r}
  writer=create(f,tx);token=await writer.prepare(scope,m.reference.server_sequence)
  await expect(writer.commit(token)).rejects.toMatchObject({code:'post_commit_verification_failed',commitMayHaveOccurred:true})
  expect(f.f.db.inbox.find((r:any)=>r.event_id===m.reference.event_id)).toMatchObject({state:'applied'})
  expect(await create(f).replay(scope,m.reference.server_sequence)).toMatchObject({status:'already_applied'})
 },5000)
 it('reports actual post-commit authentication rejection without rewriting the committed evidence',async()=>{
  let committed=false
  const tx:BrowserSyncTransaction=async(...args)=>{const r=await f.transaction(...args);if(args[2]==='readwrite')committed=true;return r}
  writer=create(f,tx);token=await writer.prepare(scope,m.reference.server_sequence)
  const open=readers.openBrowserCanonicalObject,spy=vi.spyOn(readers,'openBrowserCanonicalObject').mockImplementation(async(...args)=>{if(committed)throw Error('POST_COMMIT_AUTH_REJECTION');return open(...args)})
  await expect(writer.commit(token)).rejects.toMatchObject({code:'post_commit_verification_failed',commitMayHaveOccurred:true})
  expect(f.f.db.inbox.find((r:any)=>r.event_id===m.reference.event_id)).toMatchObject({state:'applied'});spy.mockRestore()
  expect(await create(f).replay(scope,m.reference.server_sequence)).toMatchObject({status:'already_applied'})
 },5000)
 it('rejects revocation during fresh owner preparation',async()=>{
  const open=readers.openBrowserCanonicalObject;let fired=false
  vi.spyOn(readers,'openBrowserCanonicalObject').mockImplementation(async(...args)=>{const r=await open(...args);if(!fired){fired=true;f.f.lock()}return r})
  const before=f.before();await expect(create(f).prepare(scope,m.reference.server_sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('rechecks full inventory within the actual write transaction',async()=>{
  const tx:BrowserSyncTransaction=(s,stores,mode,run)=>{
   if(mode==='readwrite'){
    expect(stores).toEqual(resolutionInventoryStores)
    ;(f.f.db.localProjects![1] as any).negative_race='unrelated-project'
   }
   return f.transaction(s,stores,mode,run)
  }
  writer=create(f,tx);token=await writer.prepare(scope,m.reference.server_sequence)
  await expect(writer.commit(token)).rejects.toMatchObject({code:'stale_source'});expect(f.f.db.inbox.find((r:any)=>r.event_id===m.reference.event_id)).toMatchObject({state:'received'})
 },5000)
})
describe('actual owner barriers',()=>{
 let f:Fixture
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 for(const operation of ['reactivate','delete-again','second-create','wrong-parent','suffix','earlier-content'] as const)it(`blocks ${operation}`,async()=>{
  const writer=create(f)
  if(operation==='reactivate'||operation==='delete-again'){
   const d=await candidate(f,'delete');await writer.commit(await writer.prepare(scope,d.reference.server_sequence))
  }
  if(operation==='earlier-content')await f.receive('unapplied-before-delete')
  let m=await candidate(f,operation==='reactivate'?'update':'delete')
  if(operation==='second-create'||operation==='wrong-parent'){
   // Replace only the received candidate with a new genuine encrypted sender event.
   f.f.db.inbox.pop();(f.f.db.cursors[0] as any).pull_cursor--
   m=await metadataRow(f.f,m.reference.server_sequence,{revision:operation==='second-create'?1:2,parent:operation==='second-create'?undefined:crypto.randomUUID()})
  }
  if(operation==='suffix')await candidate(f)
  const before=f.before();await expect(writer.prepare(scope,m.reference.server_sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('reports the unsupported no-head create baseline without minting an owner plan',async()=>{
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1)
  // Negative missing-genesis evidence, never a fabricated positive Legacy-F baseline.
  f.f.db.ownerHeads=[];const before=f.before()
  await expect(create(f).prepare(scope,m.reference.server_sequence)).rejects.toMatchObject({code:'unsupported_create_baseline'});expect(f.before()).toEqual(before)
 },5000)
 it('rejects Metadata transport2 at the frozen durable parser boundary',async()=>{
  const m=await candidate(f,'update',2),before=f.before()
  await expect(create(f).prepare(scope,m.reference.server_sequence)).rejects.toMatchObject({code:'corrupt_record'});expect(f.before()).toEqual(before)
 },5000)
 it('keeps later received Content pending through deletion without granting first apply',async()=>{
  const d=await candidate(f,'delete'),pending=await f.receive('unapplied-after-delete'),writer=create(f),before=f.before()
  await writer.commit(await writer.prepare(scope,d.reference.server_sequence));expect(f.f.db.inbox.find((r:any)=>r.event_id===pending.event_id)).toMatchObject({state:'received'})
  expect(f.f.db.localProjects).toEqual(before.localProjects);expect(f.f.db.localNotes).toEqual(before.localNotes)
  await expect(f.owner.apply(scope,pending.sequence)).rejects.toThrow()
 },5000)
})
