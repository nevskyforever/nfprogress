// @vitest-environment node
import {afterEach,expect,it,vi} from 'vitest'
import {continuationFixture} from './resolutionContinuation.testFixture'
import {BrowserV10OrdinaryApply,type OHistoryToken} from './v10OrdinaryApply'
import {BrowserResolutionPrefix,type GHistoryToken,type QHistoryToken} from './resolutionPrefix'
import type {HHistoryToken} from './resolutionContinuation'
import {BrowserV10Recovery} from './v10Recovery'
import * as historical from './resolutionHistorical'
import {scope} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'

afterEach(()=>vi.restoreAllMocks())
const strategies=['choose_version','manual_merge','delete','keep_both'] as const
async function setup(strategy:typeof strategies[number]='keep_both'){
 const f=await continuationFixture(strategy,true,undefined,false,2,true);let active=true
 const ordinary=(tx:BrowserSyncTransaction=f.f.transaction)=>new BrowserV10OrdinaryApply(tx,f.f.localOwner,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const q=(tx:BrowserSyncTransaction=f.f.transaction)=>new BrowserResolutionPrefix(tx,()=>active).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const g=new BrowserResolutionPrefix(f.f.transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 return{...f,ordinary:ordinary(),q:q(),g,createO:ordinary,createQ:q,close:()=>{active=false;f.close()}}
}

for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of strategies)it(`Legacy3 O/Q ${strategy}, ordinary${protocol}/ID${compressed?1:0}: create update delete and cursor-only commit`,async()=>{
 const f=await setup(strategy)
 const h=await f.receive({protocol,compressed,deleted:strategy==='delete'});await f.runtime.apply(scope,h.sequence)
 if(strategy==='keep_both'){const retained=await f.receive({id:'retained-note',protocol,compressed});await f.runtime.apply(scope,retained.sequence)}
 const create=await f.receive({id:'independent-note',parent:null,revision:1,protocol,compressed,content:'O_CREATE'});expect(await f.ordinary.apply(scope,create.sequence)).toBe('applied')
 const update=await f.receive({id:'independent-note',parent:create.event_id,revision:2,protocol,compressed,content:'O_UPDATE'});expect(await f.ordinary.apply(scope,update.sequence)).toBe('applied')
 const remove=await f.receive({id:'independent-note',parent:update.event_id,revision:3,protocol,compressed,deleted:true});expect(await f.ordinary.apply(scope,remove.sequence)).toBe('applied')
 expect(await f.ordinary.reconcile(scope,remove.sequence)).toBe('already_applied')
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow()
 const certificate=await f.q.prepare(scope),result=await f.q.calculate(certificate)
 expect(result).toMatchObject({current_proven_prefix:0,candidate_proven_prefix:remove.sequence,pull_cursor:remove.sequence,first_blocking_sequence:null,blocker:null,readOnly:true,ackAuthorized:false,counts:{resolution:1}})
 expect(result.counts[protocol===2?'legacy':'content']).toBeGreaterThanOrEqual(4);expect(f.before()).toEqual(before)
 const commit=await f.q.prepareCommit(certificate);expect(await f.q.commit(commit)).toBe('advanced');expect(await f.q.commit(commit)).toBe('already_proven')
 const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=remove.sequence;expect(f.before()).toEqual(expected)
 expect(await f.q.commit(await f.q.prepareCommit(await f.q.prepare(scope)))).toBe('no_progress')
})

it('O transaction abort and Q stale full-inventory CAS preserve every store',async()=>{
 const f=await setup('choose_version'),create=await f.receive({id:'independent-note',parent:null,revision:1,protocol:3}),before=f.before()
 const abort:BrowserSyncTransaction=async(...args)=>{if(args[2]==='readwrite')throw Error('INJECTED_ABORT');return f.f.transaction(...args)}
 await expect(f.createO(abort).apply(scope,create.sequence)).rejects.toThrow('INJECTED_ABORT');expect(f.before()).toEqual(before)
 await f.ordinary.apply(scope,create.sequence);const token=await f.q.prepareCommit(await f.q.prepare(scope));(f.f.db.ownerHeads![0] as any).head_revision++
 const stale=f.before();await expect(f.q.commit(token)).rejects.toThrow();expect(f.before()).toEqual(stale)
})

it('private O and Q requests are one-use and reject owner/token substitution',async()=>{
 const f=await setup('choose_version'),create=await f.receive({id:'independent-note',parent:null,revision:1,protocol:3}),otherO=f.createO(),otherQ=f.createQ()
 const originalO=historical.authenticateOContinuationHistory,originalQ=historical.authenticateQContinuationHistory
 await expect(originalO({} as OHistoryToken,f.ordinary)).rejects.toThrow();await expect(originalQ({} as QHistoryToken,f.q)).rejects.toThrow()
 vi.spyOn(historical,'authenticateOContinuationHistory').mockImplementation(async(token,owner)=>{
  await expect(originalO(token,otherO)).rejects.toThrow();await expect(originalQ(token as never,f.q)).rejects.toThrow();await expect(historical.authenticateHContinuationHistory(token as unknown as HHistoryToken,f.runtime)).rejects.toThrow();await expect(historical.authenticateGContinuationHistory(token as unknown as GHistoryToken,f.g)).rejects.toThrow()
  const value=await originalO(token,owner);await expect(originalO(token,owner)).rejects.toThrow();return value
 })
 expect(await f.ordinary.apply(scope,create.sequence)).toBe('applied');vi.restoreAllMocks()
 vi.spyOn(historical,'authenticateQContinuationHistory').mockImplementation(async(token,owner)=>{
  await expect(originalQ(token,otherQ)).rejects.toThrow();await expect(originalO(token as never,f.ordinary)).rejects.toThrow();await expect(historical.authenticateHContinuationHistory(token as unknown as HHistoryToken,f.runtime)).rejects.toThrow();await expect(historical.authenticateGContinuationHistory(token as unknown as GHistoryToken,f.g)).rejects.toThrow()
  const value=await originalQ(token,owner);await expect(originalQ(token,owner)).rejects.toThrow();return value
 })
 expect((await f.q.calculate(await f.q.prepare(scope))).candidate_proven_prefix).toBe(create.sequence)
})

it('H continues original and retained roles after O without borrowing O authority',async()=>{
 const f=await setup('keep_both'),create=await f.receive({id:'independent-note',parent:null,revision:1,protocol:3,compressed:true});await f.ordinary.apply(scope,create.sequence)
 const original=await f.receive({protocol:3,compressed:true});expect(await f.runtime.apply(scope,original.sequence)).toBe('applied')
 const retained=await f.receive({id:'retained-note',protocol:2});expect(await f.runtime.apply(scope,retained.sequence)).toBe('applied')
 const before=f.before(),result=await f.q.calculate(await f.q.prepare(scope));expect(result).toMatchObject({candidate_proven_prefix:retained.sequence,first_blocking_sequence:null,counts:{resolution:1}});expect(f.before()).toEqual(before)
})

it('explicit mixed recovery uses Q authentication and commits only the prefix',async()=>{
 const f=await setup('choose_version'),create=await f.receive({id:'independent-note',parent:null,revision:1,protocol:3,compressed:true});await f.ordinary.apply(scope,create.sequence)
 const before=f.before(),recovery=new BrowserV10Recovery(f.f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const result=await recovery.run(scope);expect(result).toMatchObject({ready:false,declarationAllowed:false,ackAuthorized:false,applied:[],blocker:null,more:false,prefix:{candidate_proven_prefix:create.sequence}})
 const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=create.sequence;expect(f.before()).toEqual(expected)
})

for(const kind of ['raw3','other-project','own-device','resurrection'] as const)it(`Legacy3 O rejects ${kind} without durable change`,async()=>{
 const f=await setup('choose_version'),create=await f.receive({id:'independent-note',parent:null,revision:1,protocol:kind==='raw3'?3:2,rawLegacyOn3:kind==='raw3'}),row=f.f.db.inbox.at(-1) as any
 if(kind==='other-project'){const wire=JSON.parse(row.wire_item);wire.event.project_id='other';row.wire_item=JSON.stringify(wire)}
 if(kind==='own-device'){const wire=JSON.parse(row.wire_item);wire.event.device_id=scope.deviceId;row.wire_item=JSON.stringify(wire)}
 if(kind==='resurrection'){
  await f.ordinary.apply(scope,create.sequence);const remove=await f.receive({id:'independent-note',parent:create.event_id,revision:2,protocol:2,deleted:true});await f.ordinary.apply(scope,remove.sequence)
  const resurrection=await f.receive({id:'independent-note',parent:remove.event_id,revision:3,protocol:2});const before=f.before();await expect(f.ordinary.apply(scope,resurrection.sequence)).rejects.toThrow();expect(f.before()).toEqual(before);return
 }
 const before=f.before();await expect(f.ordinary.apply(scope,create.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
})
