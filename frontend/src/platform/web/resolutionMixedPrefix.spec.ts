// @vitest-environment node
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {recoveryFixture} from './v10Recovery.testFixture'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {scope,amk} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'
import * as historical from './resolutionHistorical'
import * as mixed from './mixedSourceValidation'
import {canonical} from '@/cloud/projectMetadataCodec'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {encodeNoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {compressCanonicalFrame} from '@/cloud/frameCompression'
afterEach(()=>vi.restoreAllMocks())
type Fixture=Awaited<ReturnType<typeof ordinaryV10Fixture>>
function create(f:Fixture,tx:BrowserSyncTransaction=f.transaction,current=()=>true){return new BrowserResolutionPrefix(tx,current).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)}
async function calculate(g:ReturnType<typeof create>){return g.calculate(await g.prepare(scope))}
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`mixed prefix protocol${protocol}/ID${compressed?1:0}/${strategy}`,()=>{
 let f:Fixture,g:ReturnType<typeof create>,ordinary:Awaited<ReturnType<Fixture['receive']>>
 beforeEach(async()=>{f=await ordinaryV10Fixture(strategy,protocol,compressed);g=create(f);ordinary=await f.receive();expect(await f.owner.apply(scope,ordinary.sequence)).toBe('applied')},5000)
 it('qualifies real O create/update/delete and H source transitions without writes',async()=>{
  const h=await f.receive('content-note',f.children[0]!.event_id,5,strategy==='delete');await f.h.apply(scope,h.sequence)
  const update=await f.receive('independent',ordinary.event_id,2);await f.owner.apply(scope,update.sequence)
  const deleted=await f.receive('independent',update.event_id,3,true);await f.owner.apply(scope,deleted.sequence)
  const before=f.before(),http=vi.spyOn(globalThis,'fetch'),token=await g.prepare(scope),r=await g.calculate(token)
  expect(r).toMatchObject({readOnly:true,ackAuthorized:false,current_proven_prefix:(before.cursors[0] as {proven_prefix:number}).proven_prefix,candidate_proven_prefix:deleted.sequence,first_blocking_sequence:null,counts:{resolution:1,metadata:1}})
  expect(r.counts.legacy+r.counts.content+r.counts.resolution+r.counts.metadata).toBe(deleted.sequence)
  expect(f.before()).toEqual(before);expect(http).not.toHaveBeenCalled()
  expect(f.f.db.localNotes!.find((n:any)=>n.note_id==='independent')).toMatchObject({deleted:true,note_revision:0})
 })
 it('commits only the contiguous local cursor with exact idempotency and fresh replay',async()=>{
  const before=f.before(),http=vi.spyOn(globalThis,'fetch'),token=await g.prepare(scope),plan=await g.prepareCommit(token)
  expect(await g.commit(plan)).toBe('advanced');expect(await g.commit(plan)).toBe('already_proven')
  const expected=structuredClone(before);(expected.cursors[0] as {proven_prefix:number}).proven_prefix=ordinary.sequence;expect(f.before()).toEqual(expected)
  expect((await calculate(g)).candidate_proven_prefix).toBe(ordinary.sequence)
  expect(await g.commit(await g.prepareCommit(await g.prepare(scope)))).toBe('no_progress');expect(http).not.toHaveBeenCalled()
 })
 if(strategy==='keep_both')it('authenticates both H roles and retained tombstones in exact mixed order',async()=>{
  const retained=await f.receive('retained-note',f.children[1]!.event_id,5,true);await f.h.apply(scope,retained.sequence)
  const update=await f.receive('baseline-live',(f.f.db.legacyNoteHistory!.find((h:any)=>h.record_kind==='head'&&h.note_id==='baseline-live') as any).linear_head_event_id,3);await f.owner.apply(scope,update.sequence)
  const original=await f.receive('content-note',f.children[0]!.event_id,5);await f.h.apply(scope,original.sequence)
  expect(await calculate(g)).toMatchObject({candidate_proven_prefix:original.sequence,first_blocking_sequence:null})
  expect(f.f.db.localNotes!.find((n:any)=>n.note_id==='retained-note')).toMatchObject({deleted:true})
 })
})
describe('mixed prefix certificates and barriers',()=>{
 let f:Fixture,g:ReturnType<typeof create>,ordinary:Awaited<ReturnType<Fixture['receive']>>
 beforeEach(async()=>{f=await ordinaryV10Fixture();g=create(f);ordinary=await f.receive();await f.owner.apply(scope,ordinary.sequence)},5000)
 it('keeps default G and K fail-closed, including a pending H descendant',async()=>{
  const h=await f.receive('content-note',f.children[0]!.event_id,5),before=f.before()
  expect(await calculate(g)).toMatchObject({candidate_proven_prefix:ordinary.sequence,first_blocking_sequence:h.sequence,blocker:'unproven_family'})
  await expect(f.g.prepare(scope)).rejects.toThrow();await expect(f.runtime.run(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
  await f.h.apply(scope,h.sequence);expect((await calculate(g)).candidate_proven_prefix).toBe(h.sequence)
 })
 for(const protocol of [2,3] as const)describe(`preserved H fork protocol${protocol}`,()=>{
  let first:Awaited<ReturnType<Fixture['receive']>>,sibling:Awaited<ReturnType<Fixture['receive']>>
  beforeEach(async()=>{
   first=await f.receive('content-note',f.children[0]!.event_id,5,false,{protocol});await f.h.apply(scope,first.sequence)
   sibling=await f.receive('content-note',f.children[0]!.event_id,5,false,{protocol});expect(await f.h.apply(scope,sibling.sequence)).toBe('conflict_preserved')
  },5000)
  it('caps only the genuine incoming sequence without granting N authority',async()=>{
  const before=f.before(),r=await calculate(g)
  expect(r).toMatchObject({candidate_proven_prefix:first.sequence,first_blocking_sequence:sibling.sequence,blocker:'unproven_family'})
  expect(f.f.db.legacyNoteHistory!.find((c:any)=>c.record_kind==='candidate'&&c.event_id===sibling.event_id)).toMatchObject({projection:null,projection_digest:null})
  expect((f.f.db.inbox.find((a:any)=>a.event_id===sibling.event_id) as any).state).toBe(protocol===2?'note_conflict_preserved':'content_note_conflict_preserved')
  await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'unresolved_fork'})
  expect(f.before()).toEqual(before)
  })
  it('commits only preceding applied evidence and never promotes conflict replay',async()=>{
  const before=f.before()
  await g.commit(await g.prepareCommit(await g.prepare(scope)))
  const expected=structuredClone(before);(expected.cursors[0] as {proven_prefix:number}).proven_prefix=first.sequence;expect(f.before()).toEqual(expected)
  expect(await calculate(g)).toMatchObject({current_proven_prefix:first.sequence,candidate_proven_prefix:first.sequence,first_blocking_sequence:sibling.sequence})
  expect(await f.h.reconcile(scope,sibling.sequence)).toBe('already_applied')
  expect((await calculate(g)).candidate_proven_prefix).toBe(first.sequence)
  })
 })
 for(const kind of ['O-proof','baseline-proof','F-evidence','H-proof','candidate','membership','counter','bootstrap','dependency','duplicate','future'] as const)it(`rejects ${kind}, never historical fallback or writes`,async()=>{
  const d=f.f.db
  if(kind==='O-proof')(d.inbox.find((r:any)=>r.event_id===ordinary.event_id) as any).content_note_proof.outcome_digest='0'.repeat(64)
  if(kind==='baseline-proof')(d.inbox.find((r:any)=>JSON.parse(r.wire_item).event.entity_id==='baseline-live') as any).content_note_proof.outcome_digest='0'.repeat(64)
  if(kind==='F-evidence')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).evidence_envelope.ciphertext='AA'
  if(kind==='H-proof')(d.inbox.find((r:any)=>r.event_id===f.children[0]!.event_id) as any).content_note_proof.outcome_digest='0'.repeat(64)
  if(kind==='candidate')d.legacyNoteHistory=d.legacyNoteHistory!.filter((r:any)=>r.event_id!==ordinary.event_id)
  if(kind==='membership')d.localNotes=d.localNotes!.filter((r:any)=>r.note_id!=='baseline-deleted')
  if(kind==='counter')(d.localProjects![0] as any).source_revision++
  if(kind==='bootstrap')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  if(kind==='dependency')d.ownerHeads=[]
  if(kind==='duplicate')d.inbox.push(structuredClone(d.inbox.at(-1)!))
  if(kind==='future')(d.inbox.at(-1) as any).record_version=99
  const before=f.before(),old=vi.spyOn(historical,'verifyContinuationSources')
  await expect(g.prepare(scope)).rejects.toThrow();expect(old).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
 })
 it('missing received sequence is an explicit complete-witness barrier',async()=>{
  await f.receive('unapplied');f.f.db.inbox.pop();const before=f.before(),old=vi.spyOn(historical,'verifyContinuationSources')
  await expect(g.prepare(scope)).rejects.toMatchObject({code:'missing_sequence'});expect(old).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
 })
 for(const protocol of [2,3] as const)it(`genuine encrypted new Resolution protocol${protocol} cannot acquire G authority`,async()=>{
  const sequence=(f.f.db.cursors[0] as {pull_cursor:number}).pull_cursor+1,header={...f.resolution.header,event_id:crypto.randomUUID()},payload={...f.resolution,header}
  const raw=protocol===2?encodeNoteSyncResolutionV2(payload):frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:'44444444-4444-4444-8444-444444444444',dependencies:{bootstrap_id:f.f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:payload})
  const frame=protocol===3?compressCanonicalFrame(raw):raw,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
  try{await f.f.sync.commitInboundPage(scope,sequence-1,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event:{event_id:header.event_id,device_id:'44444444-4444-4444-8444-444444444444',server_sequence:sequence,project_id:'p',entity_id:'content-note',entity_type:'note',operation:protocol===2?'resolution':'event',revision:header.revision,updated_at:header.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false}))}finally{raw.fill(0);frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  const before=f.before();await expect(g.prepare(scope)).rejects.toMatchObject({code:'unsupported_generation'});expect(f.before()).toEqual(before)
 })
 it('genuine pending own-authored wire is not publication or source authority',async()=>{
  await f.receive('own',null,1,false,{device:scope.deviceId});const before=f.before()
  await expect(g.prepare(scope)).rejects.toMatchObject({code:'unsupported_local_source'});expect(f.before()).toEqual(before)
 })
 it('corruption inside a claimed prefix never resets or advances it',async()=>{
  const first=await f.receive('content-note',f.children[0]!.event_id,5);await f.h.apply(scope,first.sequence)
  const fork=await f.receive('content-note',f.children[0]!.event_id,5);await f.h.apply(scope,fork.sequence)
  ;(f.f.db.cursors[0] as {proven_prefix:number}).proven_prefix=fork.sequence
  const before=f.before();await expect(g.prepare(scope)).rejects.toMatchObject({code:'corrupt_record'});expect(f.before()).toEqual(before)
 })
 for(const kind of ['counter','membership','note'] as const)it(`rejects authentic AEAD with unexplained ${kind} drift`,async()=>{
  const row=(kind==='note'?f.f.db.localNotes!.find((n:any)=>n.note_id==='independent'):f.f.db.localProjects!.find((p:any)=>p.project_id==='p')) as any
  const bytes=await historical.openHistoricalJson(scope,'p',kind==='note'?'independent':'p',kind==='note'?'note':'project_metadata',row.envelope,amk,()=>true)
  let payload:any;try{payload=JSON.parse(new TextDecoder().decode(bytes))}finally{bytes.fill(0)}
  if(kind==='counter'){payload.source_revision++;row.source_revision++}else if(kind==='membership')payload.member_ids.push('invented');else payload.source.note.content='UNEXPLAINED_AUTHENTIC_AEAD'
  const raw=new TextEncoder().encode(canonical(payload)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:kind==='note'?'independent':'p',entityType:kind==='note'?'note':'project_metadata'},raw)
  try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  const before=f.before();await expect(g.prepare(scope)).rejects.toMatchObject({code:'source_mismatch'});expect(f.before()).toEqual(before)
 })
 for(const kind of ['wire','source','head','cursor','binding','owner','outbox'] as const)it(`exact full inventory CAS rejects ${kind} changes after prepare`,async()=>{
  const token=await g.prepare(scope),plan=await g.prepareCommit(token),d=f.f.db
  if(kind==='wire')(d.inbox.at(-1) as any).wire_item+=' '
  if(kind==='source')(d.localProjects![0] as any).source_revision++
  if(kind==='head')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='head') as any).head_revision++
  if(kind==='cursor')(d.cursors[0] as {next_local_ordinal:number}).next_local_ordinal++
  if(kind==='binding')(d.projectBindings[0] as any).remote_high_water++
  if(kind==='owner')(d.ownerHeads![0] as any).bootstrap_id=crypto.randomUUID()
  if(kind==='outbox')d.outbox.push({account_id:scope.accountId,event_id:crypto.randomUUID()})
  const before=f.before();await expect(g.calculate(token)).rejects.toMatchObject({code:'stale_source'});await expect(g.commit(plan)).rejects.toMatchObject({code:'stale_source'});expect(f.before()).toEqual(before)
 })
 it('pins source changes from a real competing O owner, with safe fresh retry',async()=>{
  const pending=await f.receive('another'),token=await g.prepare(scope),plan=await g.prepareCommit(token)
  await f.owner.apply(scope,pending.sequence);const before=f.before()
  await expect(g.commit(plan)).rejects.toMatchObject({code:'stale_source'});expect(f.before()).toEqual(before)
  expect(await g.commit(await g.prepareCommit(await g.prepare(scope)))).toBe('advanced')
 })
 it('does not mint a certificate if an actual O apply changes inventory during authentication',async()=>{
  const pending=await f.receive('during-prepare'),actual=mixed.validateMixedPrefixInventory
  vi.spyOn(mixed,'validateMixedPrefixInventory').mockImplementation(async(...args)=>{const result=await actual(...args);await f.owner.apply(scope,pending.sequence);return result})
  await expect(g.prepare(scope)).rejects.toMatchObject({code:'stale_source'})
  expect((f.f.db.cursors[0] as {proven_prefix:number}).proven_prefix).toBe(f.sequence)
 })
 for(const kind of ['key','logout','epoch','profile'] as const)it(`revokes both certificates and commit plans on ${kind}`,async()=>{
  let active=true;g=create(f,f.transaction,()=>active)
  const token=await g.prepare(scope),plan=await g.prepareCommit(token)
  if(kind==='key')f.f.lock();if(kind==='logout')await f.f.auth.logout();if(kind==='epoch')await f.f.auth.login('fixture','fixture');if(kind==='profile')active=false
  const before=f.before();await expect(g.calculate(token)).rejects.toThrow();await expect(g.commit(plan)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 for(const kind of ['abort','key'] as const)it(`rolls back cursor-only commit on ${kind}`,async()=>{
  let armed=false
  const tx:BrowserSyncTransaction=(s,stores,mode,schedule)=>f.transaction(s,stores,mode,(tx,result,abort)=>{
   const proxy=new Proxy(tx,{get:(target,key)=>key==='objectStore'?(name:string)=>{
    const store=target.objectStore(name);return new Proxy(store,{get:(target,key)=>{
     const method=Reflect.get(target,key)
     if(key==='put'&&mode==='readwrite')return(...args:any[])=>{expect(name).toBe('cursors');const r=method.apply(target,args);if(armed&&kind==='key')f.f.lock();return r}
     return typeof method==='function'?method.bind(target):method
    }})
   }:Reflect.get(target,key)})
   schedule(proxy,result,abort)
  })
  g=create(f,tx);const plan=await g.prepareCommit(await g.prepare(scope)),before=f.before();armed=true;if(kind==='abort')f.f.abort()
  await expect(g.commit(plan)).rejects.toThrow();expect(f.before()).toEqual(before)
  if(kind==='abort'){f.f.abort(false);expect(await g.commit(await g.prepareCommit(await g.prepare(scope)))).toBe('advanced')}
 })
 it('rejects foreign runtime, N diagnostics, fabricated results and old ACK consumption',async()=>{
  const token=await g.prepare(scope),plan=await g.prepareCommit(token),other=create(f),before=f.before()
  for(const fake of [{},await f.witness.inspect(scope),await g.calculate(token)]){await expect(g.calculate(fake as never)).rejects.toThrow();await expect(g.commit(fake as never)).rejects.toThrow()}
  await expect(other.calculate(token)).rejects.toThrow();await expect(other.commit(plan)).rejects.toThrow();await expect(f.f.proven.ackOnce(token as never)).rejects.toThrow();expect(f.before()).toEqual(before)
 })
 it('read-only witness is separate from private certificate minting and sends no HTTP',async()=>{
  const validate=vi.spyOn(mixed,'validateMixedPrefixInventory'),old=vi.spyOn(historical,'verifyContinuationSources'),http=vi.spyOn(globalThis,'fetch'),before=f.before()
  const token=await g.prepare(scope);expect(validate).toHaveBeenCalledTimes(1);expect(old).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
  const other=create(f);await expect(other.prepareCommit(token)).rejects.toThrow();expect('prepareAck'in g).toBe(false);expect(http).not.toHaveBeenCalled()
 })
})
for(const protocol of [2,3] as const)it(`keeps accepted historical cross-role ordering protocol${protocol}`,async()=>{
 const f=await recoveryFixture('keep_both',protocol,false,false,true,true);await f.runtime.run(scope,{maxEvents:f.r.sequence})
 const h=new BrowserResolutionContinuation(f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await h.apply(scope,f.children[1]!.sequence);await h.apply(scope,f.children[0]!.sequence)
 const g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),check=vi.spyOn(mixed,'validateMixedPrefixInventory')
 expect(await calculate(g)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:null});expect(check).not.toHaveBeenCalled()
 await expect(new (await import('./mixedSourceWitness')).BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device).inspect(scope)).rejects.toMatchObject({code:'revision_order'})
})
it('preserves actual Metadata/Stage/StageOrder owners and Content plain dependencies',async()=>{
 const f=await ordinaryV10Fixture('keep_both',3,true,true),o=await f.receive('plain',null,1,false,{format:'plain'});await f.owner.apply(scope,o.sequence)
 const g=create(f);expect(await calculate(g)).toMatchObject({candidate_proven_prefix:o.sequence,counts:{metadata:1,stage:1,stage_order:1,resolution:1}})
})
