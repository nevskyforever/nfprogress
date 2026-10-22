// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {pendingMetadata,applyFamilyMetadata,createMetadataPrefix,type MetadataFixture} from './postFMetadata.testFixture'
import {bindPrivateMetadataHandoff} from './importedMetadataApply'
import {BrowserHistoricalPrefixQualification} from './historicalPrefixQualification'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {resolutionInventoryStores} from './resolutionPlanner'
import {scope} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'

afterEach(()=>vi.restoreAllMocks())
describe('private historical cursor authority after real Metadata deletion',()=>{
 let f:MetadataFixture,d:Awaited<ReturnType<typeof pendingMetadata>>,prefix:ReturnType<typeof createMetadataPrefix>,oldCertificate:unknown
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{
  const e=await f.receive('retained-content',null,1,false,{protocol:3,compressed:true});await f.owner.apply(scope,e.sequence)
  const u=await pendingMetadata(f);await applyFamilyMetadata(f,u)
  const old=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  oldCertificate=await old.prepare(scope);await old.commit(await old.prepareCommit(oldCertificate as never))
  d=await pendingMetadata(f,'delete')
  const handoff=bindPrivateMetadataHandoff(f.transaction,()=>true,f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  await handoff.commit(await handoff.prepare(scope,d.reference.server_sequence));prefix=createMetadataPrefix(f)
 },5000)
 it('independently reauthenticates every family and writes only the native cursor',async()=>{
  const before=f.before(),certificate=await prefix.prepare(scope),result=await prefix.calculate(certificate),http=vi.spyOn(globalThis,'fetch'),nonces=vi.spyOn(crypto,'getRandomValues').mockImplementation(()=>{throw Error('NO_PREFIX_NONCE')})
  expect(result).toMatchObject({current_proven_prefix:d.reference.server_sequence-1,candidate_proven_prefix:d.reference.server_sequence,counts:{metadata:3,resolution:1,stage:0,stage_order:0}})
  expect(Object.values(result.counts).reduce((a,b)=>a+b,0)).toBe(d.reference.server_sequence)
  const token=await prefix.prepareCommit(certificate);expect(await prefix.commit(token)).toBe('advanced')
  const expected=structuredClone(before);(expected.cursors[0] as any).proven_prefix=d.reference.server_sequence;expect(f.before()).toEqual(expected)
  await expect(prefix.commit(token)).rejects.toMatchObject({code:'invalid_token'});await expect(prefix.prepareCommit(certificate)).rejects.toMatchObject({code:'invalid_token'})
  const after=f.before();expect(await prefix.commit(await prefix.prepareCommit(await prefix.prepare(scope)))).toBe('no_progress');expect(f.before()).toEqual(after)
  expect(http).not.toHaveBeenCalled();expect(nonces).not.toHaveBeenCalled()
 },5000)
 it('cannot turn a real .15 diagnostic, a G/Q token, or a foreign instance token into cursor authority',async()=>{
  const diagnostic=await new BrowserHistoricalPrefixQualification(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device).inspect(scope),before=f.before()
  expect(diagnostic).toMatchObject({candidate_historical_prefix:d.reference.server_sequence,cursorCommitAuthorized:false,ackAuthorized:false})
  for(const value of [diagnostic,oldCertificate,{},null]){await expect(prefix.prepareCommit(value as never)).rejects.toMatchObject({code:'invalid_token'});await expect(prefix.commit(value as never)).rejects.toMatchObject({code:'invalid_token'})}
  const certificate=await prefix.prepare(scope),other=createMetadataPrefix(f)
  await expect(other.calculate(certificate)).rejects.toMatchObject({code:'invalid_token'})
  const token=await prefix.prepareCommit(certificate);await expect(other.commit(token)).rejects.toMatchObject({code:'invalid_token'});expect(f.before()).toEqual(before)
 },5000)
 for(const store of resolutionInventoryStores)it(`pins the complete ${store} inventory in the cursor transaction`,async()=>{
  const plan=await prefix.prepareCommit(await prefix.prepare(scope)),rows=f.f.db[store as keyof typeof f.f.db] as any[]
  if(rows.length)rows[0].negative_race='full-account';else rows.push({account_id:scope.accountId,negative_race:'full-account'})
  const before=f.before();await expect(prefix.commit(plan)).rejects.toThrow();expect(f.before()).toEqual(before);await expect(prefix.commit(plan)).rejects.toMatchObject({code:'invalid_token'})
 },5000)
 it('checks the full inventory inside the same native transaction as the cursor put',async()=>{
  const tx:BrowserSyncTransaction=(...args)=>{if(args[2]==='readwrite'){expect(args[1]).toEqual(resolutionInventoryStores);(f.f.db.localProjects![1] as any).negative_race='foreign-project'}return f.transaction(...args)}
  const writer=createMetadataPrefix(f,tx),plan=await writer.prepareCommit(await writer.prepare(scope)),old=(f.f.db.cursors[0] as any).proven_prefix
  await expect(writer.commit(plan)).rejects.toMatchObject({code:'stale_source'});expect((f.f.db.cursors[0] as any).proven_prefix).toBe(old)
 },5000)
 it('aborts without a cursor mutation and consumes interrupted authority',async()=>{
  const plan=await prefix.prepareCommit(await prefix.prepare(scope)),before=f.before();f.f.abort()
  await expect(prefix.commit(plan)).rejects.toThrow();expect(f.before()).toEqual(before);f.f.abort(false)
  await expect(prefix.commit(plan)).rejects.toMatchObject({code:'invalid_token'});expect(await prefix.commit(await prefix.prepareCommit(await prefix.prepare(scope)))).toBe('advanced')
 },5000)
 it('rejects a competing stale plan after another cursor owner commits',async()=>{
  const a=await prefix.prepareCommit(await prefix.prepare(scope)),b=await prefix.prepareCommit(await prefix.prepare(scope))
  await prefix.commit(a);const after=f.before();await expect(prefix.commit(b)).rejects.toMatchObject({code:'stale_source'});expect(f.before()).toEqual(after)
 },5000)
 it('consumes a certificate before awaiting cursor-plan preparation',async()=>{
  const certificate=await prefix.prepare(scope),outcomes=await Promise.allSettled([prefix.prepareCommit(certificate),prefix.prepareCommit(certificate)])
  expect(outcomes.filter(r=>r.status==='fulfilled')).toHaveLength(1)
  expect(outcomes.find(r=>r.status==='rejected')).toMatchObject({reason:{code:'invalid_token'}})
 },5000)
 for(const kind of ['key','auth','epoch','profile','device'] as const)it(`binds cursor authority to the actual ${kind} lifecycle`,async()=>{
  let active=true;const writer=createMetadataPrefix(f,f.transaction,()=>active),plan=await writer.prepareCommit(await writer.prepare(scope)),before=f.before()
  if(kind==='key')f.f.lock();else if(kind==='auth')await f.f.auth.logout();else if(kind==='epoch')await f.f.auth.login('fixture','fixture');else if(kind==='profile')active=false
  else{await expect(writer.prepare({...scope,deviceId:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'})).rejects.toThrow();return}
  await expect(writer.commit(plan)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 for(const kind of ['old-prefix-proof','AEAD','binding','source','membership','gap','duplicate','received-proven'] as const)it(`re-authenticates ${kind}, including the old proven prefix`,async()=>{
  if(kind==='old-prefix-proof')(f.f.db.inbox.find((r:any)=>r.state==='content_note_proven') as any).content_note_proof.outcome_digest='0'.repeat(64)
  if(kind==='AEAD'){const row=f.f.db.inbox[1] as any,wire=JSON.parse(row.wire_item);wire.object.ciphertext='AA';row.wire_item=JSON.stringify(wire)}
  if(kind==='binding')(f.f.db.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  if(kind==='source')(f.f.db.localProjects![0] as any).source_revision++
  if(kind==='membership')f.f.db.localNotes!.pop()
  if(kind==='gap')f.f.db.inbox.splice(1,1)
  if(kind==='duplicate')f.f.db.inbox.push(structuredClone(f.f.db.inbox[1]!))
  if(kind==='received-proven'){await f.receive('pending');(f.f.db.cursors[0] as any).proven_prefix=(f.f.db.cursors[0] as any).pull_cursor}
  const before=f.before();await expect(prefix.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('replays only the exact current original encrypted page and never changes the cursor',async()=>{
  const page=JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[JSON.parse(d.row.wire_item)],next_cursor:d.reference.server_sequence,has_more:false}),before=f.before()
  expect(await prefix.replay(scope,d.reference.server_sequence-1,page)).toEqual({committed_cursor:d.reference.server_sequence,new_events:0,replayed_events:1,has_more:false});expect(f.before()).toEqual(before)
  const invalid=JSON.parse(page);invalid.items[0].object.ciphertext='AA';await expect(prefix.replay(scope,d.reference.server_sequence-1,JSON.stringify(invalid))).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
})
