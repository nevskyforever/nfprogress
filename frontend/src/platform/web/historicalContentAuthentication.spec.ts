// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {BrowserHistoricalContentAuthentication} from './historicalContentAuthentication'
import {historicalMetadataAfterOrdinary} from './historicalMetadataDependency.testFixture'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {canonical} from '@/cloud/projectMetadataCodec'
import {openHistoricalJson} from './resolutionHistorical'

import {metadataRow} from './metadataPrefix.testFixture'
import {BrowserHistoricalMetadataDependency} from './historicalMetadataDependency'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Recovery} from './v10Recovery'
import * as readers from './canonicalReaders'
import * as prerequisites from './noteTransportPrerequisite'
import type {BrowserSyncTransaction} from './syncDurability'

afterEach(()=>vi.restoreAllMocks())
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`terminal Metadata ${protocol}/ID${+compressed}/${strategy}`,()=>{
 let baseline:Awaited<ReturnType<typeof ordinaryV10Fixture>>,f:Awaited<ReturnType<typeof historicalMetadataAfterOrdinary>>,reader:ReturnType<BrowserHistoricalContentAuthentication['bind']>
 beforeEach(async()=>{baseline=await ordinaryV10Fixture(strategy,protocol,compressed)},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(baseline,strategy);reader=new BrowserHistoricalContentAuthentication(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)},5000)
 it('authenticates original F, independent Content and H roles without live authority',async()=>{
  const before=f.before()
  for(const id of [f.r.event_id,f.ordinary.event_id,f.original.event_id,...(f.retained?[f.retained.event_id]:[])]){
   const result=await reader.inspect(scope,id)
   expect(result).toMatchObject({historicalAuthenticated:true,fullHistoryAuthenticated:true,currentSourceVerified:true,reason:null,readOnly:true,sourceAuthorized:false,firstApplyAllowed:false,commitAuthorized:false,ackAuthorized:false,ready:false})
  }
  expect(await reader.inspect(scope,f.ordinary.event_id)).toEqual(await reader.inspect(scope,f.ordinary.event_id))
  expect(Object.keys(reader)).toEqual(['inspect']);expect(f.before()).toEqual(before)
 },5000)
})

describe('historical authentication barriers',()=>{
 let baseline:Awaited<ReturnType<typeof ordinaryV10Fixture>>,f:Awaited<ReturnType<typeof historicalMetadataAfterOrdinary>>
 let active:boolean
 const create=(tx:BrowserSyncTransaction=f.transaction)=>new BrowserHistoricalContentAuthentication(tx,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 beforeEach(async()=>{active=true;baseline=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(baseline)},5000)
 for(const part of ['gap','duplicate','missing-M','metadata-digest','metadata-parent','metadata-bootstrap','metadata-wire','note-wire','note-proof','F-evidence','F-proof','unknown-generation','foreign-account','foreign-binding','local-intent','source-AEAD','Head2','source-revision'] as const)it(`rejects ${part} without mutation`,async()=>{
  const d=f.f.db,m=d.ownerHeads!.find((r:any)=>r.owner_kind==='project_metadata') as any,row=d.inbox.find((r:any)=>r.event_id===f.ordinary.event_id) as any
  if(part==='gap')d.inbox.splice(0,1)
  else if(part==='duplicate')d.inbox.push(structuredClone(d.inbox[0]))
  else if(part==='missing-M')d.ownerHeads=[]
  else if(part==='metadata-digest')m.history[0].wire_digest='0'.repeat(64)
  else if(part==='metadata-parent')m.history.at(-1).parent_event_ids=[crypto.randomUUID()]
  else if(part==='metadata-bootstrap')m.bootstrap_id=crypto.randomUUID()
  else if(part==='metadata-wire'||part==='note-wire'){const r=part==='metadata-wire'?d.inbox[0] as any:row,w=JSON.parse(r.wire_item);w.object.ciphertext='AAAA';r.wire_item=JSON.stringify(w)}
  else if(part==='note-proof')row.content_note_proof.dependency_digest='0'.repeat(64)
  else if(part==='F-evidence')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).evidence_envelope.ciphertext='AAAA'
  else if(part==='F-proof')(d.inbox.find((r:any)=>r.event_id===f.r.event_id) as any).resolution_proof.output_digests.original='0'.repeat(64)
  else if(part==='unknown-generation')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).record_version=999
  else if(part==='foreign-account')row.account_id=crypto.randomUUID()
  else if(part==='foreign-binding')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  else if(part==='local-intent')d.legacyNoteIntents!.push({account_id:scope.accountId})
  else if(part==='source-AEAD')(d.localNotes![0] as any).envelope.ciphertext='AAAA'
  else if(part==='source-revision')(d.localProjects![0] as any).source_revision++
  else (d.legacyNoteHistory!.find((r:any)=>r.record_kind==='head'&&r.record_version===2) as any).head_revision++
  const before=f.before();expect(await create().inspect(scope,f.ordinary.event_id)).toMatchObject({historicalAuthenticated:false,reason:'invalid_evidence',sourceAuthorized:false,ready:false});expect(f.before()).toEqual(before)
 },5000)
 for(const kind of ['note','project_metadata'] as const)it(`rejects valid-AEAD current ${kind} drift independently of Metadata admissibility`,async()=>{
  const raw=(kind==='note'?f.f.db.localNotes![0]:f.f.db.localProjects![0]) as any,id=kind==='note'?raw.note_id:raw.project_id
  const bytes=await openHistoricalJson(scope,raw.project_id,id,kind,raw.envelope,amk,()=>true)
  let encoded:Uint8Array|undefined
  try{
   const value=JSON.parse(new TextDecoder().decode(bytes))
   if(kind==='note')value.source.note.content='NEGATIVE_SOURCE_DRIFT'
   else {value.source_revision++;raw.source_revision++}
   encoded=new TextEncoder().encode(canonical(value))
   const object=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:raw.project_id,entityId:id,entityType:kind},encoded)
   try{raw.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(object.nonce),ciphertext:encodeBase64Url(object.ciphertext)}}finally{object.nonce.fill(0);object.ciphertext.fill(0)}
  }finally{bytes.fill(0);encoded?.fill(0)}
  const before=f.before()
  expect((await f.reader.inspect(scope,f.ordinary.event_id)).historicalMetadataAdmissible).toBe(true)
  expect((await create().inspect(scope,f.ordinary.event_id)).historicalAuthenticated).toBe(false);expect(f.before()).toEqual(before)
 },5000)
 it('reads internally, allocating no nonce, writes, HTTP or live certificate',async()=>{
  const tx:BrowserSyncTransaction=(s,n,mode,run)=>{expect(mode).toBe('readonly');return f.transaction(s,n,mode,run)}
  vi.spyOn(BrowserHistoricalMetadataDependency.prototype,'bind').mockImplementation(()=>{throw Error('NO_PUBLIC_DIAGNOSTIC')})
  const random=vi.spyOn(crypto,'getRandomValues').mockImplementation(()=>{throw Error('NO_NONCE')}),http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_HTTP')),certificate=vi.spyOn(prerequisites,'prepareNotePrerequisite').mockRejectedValue(Error('NO_LIVE_CERTIFICATE')),before=f.before()
  const r=await create(tx).inspect(scope,f.ordinary.event_id)
  expect(r.historicalAuthenticated).toBe(true);expect(Object.isFrozen(r)).toBe(true);expect(random).not.toHaveBeenCalled();expect(http).not.toHaveBeenCalled();expect(certificate).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
 },5000)
 it('never authorizes O/H/Q, live prerequisites or original Q/K dispatch',async()=>{
  const result=await create().inspect(scope,f.ordinary.event_id),g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),before=f.before()
  expect(result.historicalAuthenticated).toBe(true)
  const http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_UNAUTHORIZED_HTTP'))
  await expect(f.f.proven.prepareAck(scope,result as never)).rejects.toThrow();await expect(f.f.proven.ackOnce(result as never)).rejects.toThrow()
  await expect(prerequisites.prepareNoteTransportCommit(result as never,f.ordinary.plaintext,{} as never)).rejects.toThrow();expect(http).not.toHaveBeenCalled()
  await expect(f.owner.commit(result as never)).rejects.toThrow();await expect(f.h.commit(result as never)).rejects.toThrow();await expect(g.commit(result as never)).rejects.toThrow()
  await expect(g.prepare(scope)).rejects.toThrow();await expect(k.run(scope)).rejects.toThrow();await expect(f.owner.apply(scope,f.ordinary.sequence)).rejects.toThrow();await expect(f.h.apply(scope,f.original.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 for(const operation of ['delete','update','competing'] as const)it(`rejects real subsequent Metadata ${operation}`,async()=>{
  const a=await metadataRow(f.f,f.deletion.reference.server_sequence+1,{revision:4,parent:operation==='competing'?f.update.event.header.event_id:f.deletion.event.header.event_id,change:e=>{if(operation==='delete'){e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}}})
  if(operation!=='competing')await f.f.metadata.apply(scope,a.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  const before=f.before();expect((await create().inspect(scope,f.ordinary.event_id)).historicalAuthenticated).toBe(false);expect(f.before()).toEqual(before)
 },5000)
 for(const kind of ['key','account','device','profile','epoch','logout'] as const)it(`rejects ${kind} revocation`,async()=>{
  const reader=create(),before=f.before();let s=scope
  if(kind==='key')f.f.lock();else if(kind==='profile')active=false;else if(kind==='epoch')await f.f.auth.login('fixture','fixture');else if(kind==='logout')await f.f.auth.logout();else s={...scope,...(kind==='account'?{accountId:crypto.randomUUID()}:{deviceId:crypto.randomUUID()})}
  await expect(reader.inspect(s,f.ordinary.event_id)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('rejects lifecycle revocation during original Metadata AEAD',async()=>{
  const original=readers.openBrowserCanonicalObject;let fired=false
  vi.spyOn(readers,'openBrowserCanonicalObject').mockImplementation(async(...args)=>{const value=await original(...args);if(!fired){fired=true;f.f.lock()}return value})
  const before=f.before();await expect(create().inspect(scope,f.ordinary.event_id)).rejects.toMatchObject({code:'closed'});expect(f.before()).toEqual(before)
 },5000)
 it('rejects a genuine competing Metadata owner at the final full-inventory reload',async()=>{
  let n=0
  const tx:BrowserSyncTransaction=async(s,stores,mode,run)=>{if(++n===2){const a=await metadataRow(f.f,f.deletion.reference.server_sequence+1,{revision:4,parent:f.deletion.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}});await f.f.metadata.apply(scope,a.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)}return f.transaction(s,stores,mode,run)}
  await expect(create(tx).inspect(scope,f.ordinary.event_id)).rejects.toMatchObject({code:'stale_source'})
 },5000)
 it('rejects a competing full-account cursor snapshot without repairing it',async()=>{
  let n=0
  const tx:BrowserSyncTransaction=(s,stores,mode,run)=>{if(++n===2)(f.f.db.cursors[0] as any).proven_prefix++;return f.transaction(s,stores,mode,run)}
  await expect(create(tx).inspect(scope,f.ordinary.event_id)).rejects.toMatchObject({code:'stale_source'})
 },5000)
})
for(const cohort of ['pending-before','pending-after','fork','Stage'] as const)describe(cohort,()=>{
 let baseline:Awaited<ReturnType<typeof ordinaryV10Fixture>>,f:Awaited<ReturnType<typeof historicalMetadataAfterOrdinary>>
 beforeEach(async()=>{baseline=await ordinaryV10Fixture('keep_both',3,false,cohort==='Stage')},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(baseline,'keep_both',{pending:cohort==='pending-before',fork:cohort==='fork'})},5000)
 it('retains actual evidence and refuses any new first apply or unsupported cohort',async()=>{
  const reader=new BrowserHistoricalContentAuthentication(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  const pending=cohort==='pending-after'?await f.receive('published-after-delete'):f.pending,before=f.before()
  const r=await reader.inspect(scope,pending?.event_id??f.ordinary.event_id)
  expect(r).toMatchObject({historicalAuthenticated:false,firstApplyAllowed:false,commitAuthorized:false,ready:false})
  if(pending){expect(r.reason).toBe('not_applied');expect(r.firstPendingSequence).toBe(pending.sequence);await expect(f.owner.apply(scope,pending.sequence)).rejects.toThrow()}
  expect(f.before()).toEqual(before)
 },5000)
})
describe('accepted F/H-only historical source ordering',()=>{
 let f:Awaited<ReturnType<typeof ordinaryV10Fixture>>
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{
  const a=await f.receive('content-note',f.children[0]!.event_id,5),b=await f.receive('retained-note',f.children[1]!.event_id,5)
  await f.h.apply(scope,b.sequence);await f.h.apply(scope,a.sequence)
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:f.m.event.header.event_id})
  await f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  const d=await metadataRow(f.f,m.reference.server_sequence+1,{revision:3,parent:m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}})
  await f.f.metadata.apply(scope,d.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
 },5000)
 it('keeps the genuine cross-role commit order outside the mixed cohort',async()=>{
  const before=f.before(),reader=new BrowserHistoricalContentAuthentication(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
  expect(await reader.inspect(scope,f.r.event_id)).toMatchObject({historicalAuthenticated:true,sourceCohort:'historical'});expect(f.before()).toEqual(before)
 },5000)
})
