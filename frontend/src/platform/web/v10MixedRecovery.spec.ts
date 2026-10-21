// @vitest-environment node
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {BrowserV10Recovery} from './v10Recovery'
import {BrowserV10OrdinaryApplyRuntime} from './v10OrdinaryApply'
import {BrowserResolutionContinuationRuntime} from './resolutionContinuation'
import {BrowserResolutionPrefixRuntime} from './resolutionPrefix'
import {scope,amk} from './bootstrap.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {stageRow} from './stageApply.testFixture'
import {orderRow} from './stageOrder.testFixture'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {encodeNoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {BrowserDeviceRegistration} from './deviceRegistration'
import {recoveryFixture} from './v10Recovery.testFixture'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import type {BrowserSyncTransaction} from './syncDurability'
afterEach(()=>vi.restoreAllMocks())
type Fixture=Awaited<ReturnType<typeof ordinaryV10Fixture>>
function create(f:Fixture,tx:BrowserSyncTransaction=f.transaction,current=()=>true){return new BrowserV10Recovery(tx,f.f.localOwner,current).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)}
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`manual mixed recovery ${protocol}/ID${compressed?1:0}/${strategy}`,()=>{
 let f:Fixture,k:ReturnType<typeof create>
 beforeEach(async()=>{f=await ordinaryV10Fixture(strategy,protocol,compressed);k=create(f)},5000)
 it('routes real independent create through O and advances only its proven local prefix',async()=>{
  const a=await f.receive(),before=f.before(),owner=vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'commit'),h=vi.spyOn(BrowserResolutionContinuationRuntime.prototype,'prepare')
  const r=await k.run(scope,{replay:{since:a.since,rawPage:a.rawPage}})
  expect(r).toMatchObject({applied:[{sequence:a.sequence,route:protocol===2?'legacy':'content',status:'applied'}],blocker:null,more:false,ready:false,declarationAllowed:false,ackAuthorized:false,readiness:null,replayed_events:1,prefix:{candidate_proven_prefix:a.sequence}})
  expect(owner).toHaveBeenCalledOnce();expect(h).not.toHaveBeenCalled();expect((f.f.db.cursors[0] as any).proven_prefix).toBe(a.sequence)
  for(const row of before.inbox){
   const stored=f.f.db.inbox.find((r:any)=>r.event_id===(row as any).event_id)
   expect((stored as any).wire_item).toBe((row as any).wire_item)
   if((row as any).event_id!==a.event_id)expect(stored).toEqual(row)
  }
  expect(f.f.db.legacyNoteHistory!.filter((r:any)=>r.record_kind!=='head')).toEqual(expect.arrayContaining(before.legacyNoteHistory!.filter((r:any)=>r.record_kind!=='head')))
  for(const key of ['outbox','receipts','ownerHeads','legacyNoteIntents','projectBindings'])expect(f.f.db[key]).toEqual(before[key])
 })
 it('keeps original H ownership beside a real independent O outcome',async()=>{
  const o=await f.receive();await f.owner.apply(scope,o.sequence)
  const h=await f.receive('content-note',f.children[0]!.event_id,5,strategy==='delete'),ordinary=vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare')
  expect(await k.run(scope)).toMatchObject({applied:[{sequence:h.sequence,route:'continuation'}],blocker:null,prefix:{candidate_proven_prefix:h.sequence}})
  expect(ordinary).not.toHaveBeenCalled();const stable=f.before();expect((await k.run(scope)).applied).toEqual([]);expect(f.before()).toEqual(stable)
 })
 if(strategy==='keep_both')it('routes retained tombstones exclusively through H',async()=>{
  const o=await f.receive();await f.owner.apply(scope,o.sequence)
  const h=await f.receive('retained-note',f.children[1]!.event_id,5,true)
  expect(await k.run(scope)).toMatchObject({applied:[{sequence:h.sequence,route:'continuation'}],blocker:null})
  expect(f.f.db.localNotes!.find((n:any)=>n.note_id==='retained-note')).toMatchObject({deleted:true})
 })
})
describe('mixed K boundaries and recovery',()=>{
 let f:Fixture,k:ReturnType<typeof create>,o:Awaited<ReturnType<Fixture['receive']>>
 beforeEach(async()=>{f=await ordinaryV10Fixture();k=create(f);o=await f.receive();await f.owner.apply(scope,o.sequence)},5000)
 describe('bounded genuine pass and manual continuation',()=>{
  let a:Awaited<ReturnType<Fixture['receive']>>,h:Awaited<ReturnType<Fixture['receive']>>,bounded:Awaited<ReturnType<typeof k.run>>
  beforeEach(async()=>{a=await f.receive('independent',o.event_id,2);h=await f.receive('content-note',f.children[0]!.event_id,5);bounded=await k.run(scope,{maxEvents:1})},5000)
  it('uses earliest pending and commits only its exact bounded prefix',()=>{
   expect(bounded).toMatchObject({applied:[{sequence:a.sequence,route:'content'}],blocker:{sequence:h.sequence,kind:'budget_exhausted',retryable:true},prefix:{candidate_proven_prefix:a.sequence},more:true})
   expect(f.f.db.inbox.find((r:any)=>r.event_id===h.event_id)).toMatchObject({state:'received'})
  })
  it('fresh manual pass resumes H from the fully reloaded source',async()=>{expect(await k.run(scope)).toMatchObject({applied:[{sequence:h.sequence,route:'continuation'}],blocker:null,prefix:{candidate_proven_prefix:h.sequence}})})
 })
 it('routes a genuine ordinary update through O',async()=>{
  const a=await f.receive('independent',o.event_id,2);expect(await k.run(scope)).toMatchObject({applied:[{sequence:a.sequence,route:'content'}],blocker:null})
 })
 it('routes genuine delete and retains all baseline tombstones',async()=>{
  const a=await f.receive('independent',o.event_id,2);await f.owner.apply(scope,a.sequence)
  const d=await f.receive('independent',a.event_id,3,true),before=f.before()
  expect(await k.run(scope)).toMatchObject({applied:[{sequence:d.sequence,status:'applied'}],blocker:null,prefix:{candidate_proven_prefix:d.sequence}})
  expect(f.f.db.localNotes!.find((n:any)=>n.note_id==='independent')).toMatchObject({deleted:true})
  expect(f.f.db.localNotes!.find((n:any)=>n.note_id==='baseline-deleted')).toEqual(before.localNotes!.find((n:any)=>n.note_id==='baseline-deleted'))
 })
 describe('genuine H-owned fork',()=>{
  let first:Awaited<ReturnType<Fixture['receive']>>,fork:Awaited<ReturnType<Fixture['receive']>>,later:Awaited<ReturnType<Fixture['receive']>>
  beforeEach(async()=>{first=await f.receive('content-note',f.children[0]!.event_id,5);await f.h.apply(scope,first.sequence);fork=await f.receive('content-note',f.children[0]!.event_id,5);later=await f.receive('later')},5000)
  it('preserves with no projection and blocks later received Notes',async()=>{
  const before=f.before(),r=await k.run(scope)
  expect(r).toMatchObject({applied:[{sequence:fork.sequence,route:'continuation',status:'conflict_preserved'}],blocker:{sequence:fork.sequence,kind:'unresolved_fork'},prefix:{candidate_proven_prefix:first.sequence,first_blocking_sequence:fork.sequence},more:true})
  expect(f.f.db.localProjects).toEqual(before.localProjects);expect(f.f.db.localNotes).toEqual(before.localNotes)
  expect(f.f.db.legacyNoteHistory!.find((c:any)=>c.record_kind==='candidate'&&c.event_id===fork.event_id)).toMatchObject({projection:null,projection_digest:null})
  expect(f.f.db.inbox.find((r:any)=>r.event_id===later.event_id)).toMatchObject({state:'received'})
  })
  it('a fresh pass stops on the persisted fork without replay promotion',async()=>{
   await f.h.apply(scope,fork.sequence);const before=f.before(),r=await k.run(scope)
   expect(r).toMatchObject({applied:[],blocker:{sequence:fork.sequence,kind:'unresolved_fork'}})
   const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=first.sequence;expect(f.before()).toEqual(expected)
  })
 })
 for(const kind of ['unrelated','own','resurrection','orphan'] as const)it(`earliest ${kind} is an explicit barrier, no default fallback`,async()=>{
  const a=await f.receive(kind==='resurrection'?'content-note':'blocked',kind==='resurrection'?f.children[0]!.event_id:kind==='orphan'?crypto.randomUUID():null,kind==='resurrection'?5:kind==='orphan'?2:1,false,kind==='unrelated'?{project:'q',protocol:2}:kind==='own'?{device:scope.deviceId}:{})
  if(kind==='resurrection'){
   await f.h.apply(scope,a.sequence);const d=await f.receive('content-note',a.event_id,6,true);await f.h.apply(scope,d.sequence);await f.receive('content-note',d.event_id,7)
  }
  const before=f.before(),r=await k.run(scope)
  expect(r.applied).toEqual([]);expect(r.blocker).toMatchObject({sequence:(f.f.db.cursors[0] as any).pull_cursor,kind:kind==='orphan'?'dependency_unavailable':'unsupported_route'})
  const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=r.prefix?.candidate_proven_prefix??(expected.cursors[0] as any).proven_prefix;expect(f.before()).toEqual(expected)
 })
 for(const family of ['metadata','stage','stage_order'] as const)it(`genuine received post-F ${family} remains explicitly deferred`,async()=>{
  const sequence=(f.f.db.cursors[0] as any).pull_cursor+1
  // Sender-only received ciphertext, never a fabricated applied proof.
  if(family==='metadata')await metadataRow(f.f,sequence,{revision:2,parent:f.m.event.header.event_id,compressed:true})
  else if(family==='stage')await stageRow({...f.f,metadataEvent:f.m.event} as never,sequence,{compressed:true})
  else await orderRow({...f.f,metadataEvent:f.m.event,stageEvents:[]} as never,sequence,{compressed:true})
  const before=f.before(),r=await k.run(scope)
  expect(r).toMatchObject({applied:[],blocker:{sequence,kind:'unsupported_route',reason:'post_F_structural_route'},prefix:{candidate_proven_prefix:sequence-1}})
  const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=sequence-1;expect(f.before()).toEqual(expected)
 })
 for(const protocol of [2,3] as const)it(`authentic new Resolution protocol${protocol} stays a generation barrier`,async()=>{
  const sequence=(f.f.db.cursors[0] as any).pull_cursor+1,payload=structuredClone(f.resolution);payload.header.event_id=crypto.randomUUID()
  const raw=protocol===2?encodeNoteSyncResolutionV2(payload):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:'44444444-4444-4444-8444-444444444444',dependencies:{bootstrap_id:f.f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:payload}),frame=protocol===3?compressCanonicalFrame(raw):raw
  const encrypted=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
  try{await f.f.sync.commitInboundPage(scope,sequence-1,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event:{event_id:payload.header.event_id,device_id:'44444444-4444-4444-8444-444444444444',server_sequence:sequence,project_id:'p',entity_id:'content-note',entity_type:'note',operation:protocol===2?'resolution':'event',revision:payload.header.revision,updated_at:payload.header.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(encrypted.nonce),ciphertext:encodeBase64Url(encrypted.ciphertext)}}],next_cursor:sequence,has_more:false}))}finally{raw.fill(0);frame.fill(0);encrypted.nonce.fill(0);encrypted.ciphertext.fill(0)}
  const before=f.before();expect(await k.run(scope)).toMatchObject({applied:[],blocker:{sequence,kind:'unsupported_generation'},prefix:null});expect(f.before()).toEqual(before)
 })
 it('a later unsupported author cannot be hidden to authorize an earlier Note',async()=>{
  const first=await f.receive('first'),later=await f.receive('own',null,1,false,{device:scope.deviceId}),before=f.before()
  expect(await k.run(scope)).toMatchObject({applied:[],blocker:{sequence:first.sequence,kind:'unsupported_route'},prefix:null})
  expect(f.before()).toEqual(before);expect(later.sequence).toBeGreaterThan(first.sequence)
 })
 for(const kind of ['gap','proof','source','unknown','root'] as const)it(`never hides ${kind} or manufactures applied evidence`,async()=>{
  const a=await f.receive('pending'),d=f.f.db
  if(kind==='gap')d.inbox=d.inbox.filter((r:any)=>r.event_id!==a.event_id)
  if(kind==='proof')(d.inbox.find((r:any)=>r.event_id===o.event_id) as any).content_note_proof.outcome_digest='0'.repeat(64)
  if(kind==='source')(d.localNotes![0] as any).envelope.ciphertext='AA'
  if(kind==='unknown')(d.inbox.at(-1) as any).record_version=99
  if(kind==='root')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).evidence_envelope.ciphertext='AA'
  const before=f.before()
  if(kind==='gap')expect(await k.run(scope)).toMatchObject({applied:[],blocker:{sequence:a.sequence,kind:'missing_sequence'},prefix:null})
  else await expect(k.run(scope)).rejects.toThrow()
  expect(f.before()).toEqual(before)
 })
 it('stale complete source during owner preparation rejects before any commit',async()=>{
  const a=await f.receive('pending'),actual=BrowserV10OrdinaryApplyRuntime.prototype.prepare,commit=vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'commit')
  vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare').mockImplementation(async function(this:BrowserV10OrdinaryApplyRuntime,...args){const plan=await actual.apply(this,args);await f.receive('concurrent');return plan})
  await expect(k.run(scope)).rejects.toMatchObject({code:'stale_source'});expect(commit).not.toHaveBeenCalled()
  expect(f.f.db.inbox.find((r:any)=>r.event_id===a.event_id)).toMatchObject({state:'received'})
 })
 it('two genuine manual bindings cannot double-apply the same prepared source',async()=>{
  const a=await f.receive('raced');let release:()=>void=()=>{},entered:()=>void=()=>{},calls=0
  const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>entered=r),actual=BrowserV10OrdinaryApplyRuntime.prototype.prepare
  vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare').mockImplementation(async function(this:BrowserV10OrdinaryApplyRuntime,...args){const plan=await actual.apply(this,args);if(calls++===0){entered();await gate}return plan})
  const first=k.run(scope);await ready;expect(await create(f).run(scope)).toMatchObject({applied:[{sequence:a.sequence}],blocker:null});const before=f.before();release();await expect(first).rejects.toMatchObject({code:'stale_source'});expect(f.before()).toEqual(before)
 })
 describe('native event transaction abort',()=>{
  let a:Awaited<ReturnType<Fixture['receive']>>,before:ReturnType<Fixture['before']>
  beforeEach(async()=>{
   a=await f.receive('pending');before=f.before();const actual=BrowserV10OrdinaryApplyRuntime.prototype.commit
   vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'commit').mockImplementationOnce(async function(this:BrowserV10OrdinaryApplyRuntime,token){f.f.abort();try{return await actual.call(this,token)}finally{f.f.abort(false)}})
   await expect(k.run(scope)).rejects.toThrow()
  },5000)
  it('retains exact original queue/source with no partial O outcome',()=>{expect(f.before()).toEqual(before)})
  it('fresh manual retry applies the retained event once',async()=>{expect(await k.run(scope)).toMatchObject({applied:[{sequence:a.sequence}],blocker:null})})
 })
 describe('native prefix transaction abort after real O commit',()=>{
  let a:Awaited<ReturnType<Fixture['receive']>>
  beforeEach(async()=>{
   a=await f.receive('pending');vi.spyOn(BrowserResolutionPrefixRuntime.prototype,'commit').mockRejectedValueOnce(Error('native prefix abort'))
   await expect(k.run(scope)).rejects.toThrow()
  },5000)
  it('retains only genuinely produced applied evidence',()=>{expect(f.f.db.inbox.find((r:any)=>r.event_id===a.event_id)).toMatchObject({state:'content_note_proven'})})
  it('a new pass commits prefix without duplicating an already applied event',async()=>{expect(await k.run(scope)).toMatchObject({applied:[],prefix:{candidate_proven_prefix:a.sequence},blocker:null})})
 })
 for(const kind of ['key','auth','profile','epoch'] as const)it(`revokes prepared event commit on ${kind}`,async()=>{
  await f.receive('pending');let live=true;k=create(f,f.transaction,()=>live)
  const actual=BrowserV10OrdinaryApplyRuntime.prototype.prepare
  vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare').mockImplementation(async function(this:BrowserV10OrdinaryApplyRuntime,...args){const plan=await actual.apply(this,args);if(kind==='key')f.f.lock();if(kind==='auth')await f.f.auth.logout();if(kind==='profile')live=false;if(kind==='epoch')await f.f.auth.login('fixture','fixture');return plan})
  const before=f.before();await expect(k.run(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 it('a genuine registered-device lease revocation aborts prepared event authority',async()=>{
  let active=true
  const device=await new BrowserDeviceRegistration(f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never).registerVerified(scope)
  k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,device)
  await f.receive('pending');const actual=BrowserV10OrdinaryApplyRuntime.prototype.prepare
  vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare').mockImplementation(async function(this:BrowserV10OrdinaryApplyRuntime,...args){const plan=await actual.apply(this,args);active=false;return plan})
  const before=f.before();await expect(k.run(scope)).rejects.toMatchObject({code:'closed'});expect(f.before()).toEqual(before)
 })
 it('excludes competing manual passes and exposes no owners or private tokens',async()=>{
  await f.receive('pending');let release:()=>void=()=>{},entered:()=>void=()=>{}
  const ready=new Promise<void>(r=>entered=r),gate=new Promise<void>(r=>release=r),actual=BrowserV10OrdinaryApplyRuntime.prototype.prepare
  vi.spyOn(BrowserV10OrdinaryApplyRuntime.prototype,'prepare').mockImplementation(async function(this:BrowserV10OrdinaryApplyRuntime,...args){const plan=await actual.apply(this,args);entered();await gate;return plan})
  const first=k.run(scope);await ready;await expect(k.run(scope)).rejects.toMatchObject({code:'closed'});release();await first
  expect(Object.keys(k)).toEqual(['run']);expect(Object.isFrozen(k)).toBe(true)
 })
 for(const key of ['accountId','canonicalUserId','deviceId'] as const)it(`rejects foreign ${key} before writes`,async()=>{
  const before=f.before();await expect(k.run({...scope,[key]:crypto.randomUUID()})).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 for(const maxEvents of [0,33])it(`rejects unbounded event budget ${maxEvents}`,async()=>{
  const before=f.before();await expect(k.run(scope,{maxEvents})).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 it('fabricated registration cannot bind an effective recovery path',async()=>{
  const bad=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,{} as never),before=f.before()
  await expect(bad.run(scope)).rejects.toMatchObject({code:'closed'});expect(f.before()).toEqual(before)
 })
 it('leaves default K/G barred and sends no HTTP, ACK, capability or publication',async()=>{
  const a=await f.receive('pending'),before=f.before(),http=vi.spyOn(globalThis,'fetch')
  await expect(f.runtime.run(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
  expect(await k.run(scope)).toMatchObject({applied:[{sequence:a.sequence}],ready:false,ackAuthorized:false,declarationAllowed:false,readiness:null})
  expect(http).not.toHaveBeenCalled();expect((f.f.db.cursors[0] as any).ack_cursor).toBe(0)
 })
})
for(const compressed of [false,true])describe(`real Stage/plain dependency ID${compressed?1:0}`,()=>{
 let f:Fixture,k:ReturnType<typeof create>,a:Awaited<ReturnType<Fixture['receive']>>
 beforeEach(async()=>{f=await ordinaryV10Fixture('keep_both',3,compressed,true);k=create(f);a=await f.receive('stage-plain',null,1,false,{format:'plain'})},5000)
 it('admits only the genuine Note owner',async()=>{expect(await k.run(scope)).toMatchObject({applied:[{sequence:a.sequence,route:'content'}],blocker:null})})
})
for(const protocol of [2,3] as const)describe(`historical cross-role source ordering protocol${protocol}`,()=>{
 let f:Awaited<ReturnType<typeof recoveryFixture>>
 beforeEach(async()=>{
  f=await recoveryFixture('keep_both',protocol,false,false,true,true);await f.runtime.run(scope,{maxEvents:f.r.sequence})
  const h=new BrowserResolutionContinuation(f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  await h.apply(scope,f.children[1]!.sequence);await h.apply(scope,f.children[0]!.sequence)
 },5000)
 it('retains F/H-only compatibility without forcing the stricter O cohort',async()=>{
  const k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  expect(await k.run(scope)).toMatchObject({applied:[],blocker:null,prefix:{candidate_proven_prefix:f.sequence},ready:false})
 })
})
