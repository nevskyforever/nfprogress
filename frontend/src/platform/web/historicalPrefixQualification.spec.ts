// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {BrowserHistoricalPrefixQualification} from './historicalPrefixQualification'
import {historicalMetadataAfterOrdinary} from './historicalMetadataDependency.testFixture'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {BrowserHistoricalContentAuthentication} from './historicalContentAuthentication'
import {BrowserHistoricalMetadataDependency} from './historicalMetadataDependency'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Recovery} from './v10Recovery'
import * as readers from './canonicalReaders'
import type {BrowserSyncTransaction} from './syncDurability'

import * as prerequisites from './noteTransportPrerequisite'
import {stageRow} from './stageApply.testFixture'
import {orderRow} from './stageOrder.testFixture'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {inspectTerminalMetadataHistoricalPrefix} from './mixedSourceValidation'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import {openHistoricalJson} from './resolutionHistorical'
import {canonical} from '@/cloud/projectMetadataCodec'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'

afterEach(()=>vi.restoreAllMocks())
type Base=Awaited<ReturnType<typeof ordinaryV10Fixture>>
type Fixture=Awaited<ReturnType<typeof historicalMetadataAfterOrdinary>>
const bind=(f:Fixture|Base,transaction:BrowserSyncTransaction=f.transaction,current=()=>true)=>new BrowserHistoricalPrefixQualification(transaction,current).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`historical prefix ${protocol}/ID${+compressed}/${strategy}`,()=>{
 let base:Base,f:Fixture
 beforeEach(async()=>{base=await ordinaryV10Fixture(strategy,protocol,compressed)},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(base,strategy)},5000)
 it('qualifies each genuine sequence through the terminal delete without cursor writes',async()=>{
  const before=f.before(),cursor=before.cursors[0] as any,reader=bind(f),result=await reader.inspect(scope),retained=strategy==='keep_both'
  expect(result).toMatchObject({readOnly:true,current_proven_prefix:cursor.proven_prefix,candidate_historical_prefix:f.deletion.reference.server_sequence,pull_cursor:cursor.pull_cursor,first_blocking_sequence:null,blocker:null,cursorCommitAuthorized:false,sourceAuthorized:false,firstApplyAllowed:false,commitAuthorized:false,ackAuthorized:false,declarationAllowed:false,ready:false})
  expect(cursor.proven_prefix).toBeGreaterThan(0) // Genuine K advanced it before the later real O/H/Metadata owners.
  expect(result.counts).toEqual({metadata:3,resolution:1,legacy:protocol===2?8+Number(retained):0,content:protocol===2?2+Number(retained):10+2*Number(retained)})
  expect(Object.values(result.counts).reduce((a,b)=>a+b,0)).toBe(result.candidate_historical_prefix)
  expect(result.candidate_historical_prefix).toBe(retained?16:14)
  expect(await reader.inspect(scope)).toEqual(result);expect(Object.isFrozen(result)).toBe(true);expect(Object.isFrozen(result.counts)).toBe(true);expect(Object.keys(reader)).toEqual(['inspect']);expect(f.before()).toEqual(before)
 },5000)
})

describe('read-only prefix barriers',()=>{
 let base:Base,f:Fixture,active:boolean
 const create=(tx:BrowserSyncTransaction=f.transaction)=>bind(f,tx,()=>active)
 beforeEach(async()=>{active=true;base=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(base)},5000)
 for(const part of ['gap','duplicate-sequence','duplicate-event','metadata-proof','metadata-wire','missing-ancestor','note-proof','F-proof','F-evidence','Head2','source-revision','source-AEAD','generation','foreign-account','foreign-bootstrap','own','outbox'] as const)it(`rejects ${part} including already-proven evidence`,async()=>{
  const db=f.f.db,m=db.ownerHeads!.find((r:any)=>r.owner_kind==='project_metadata') as any
  if(part==='gap')db.inbox.splice(db.inbox.findIndex((r:any)=>r.event_id===f.update.event.header.event_id),1)
  else if(part==='duplicate-sequence')db.inbox.push(structuredClone(db.inbox[0]))
  else if(part==='duplicate-event'){const r=structuredClone(db.inbox[0]) as any;r.server_sequence=(db.cursors[0] as any).pull_cursor+1;db.inbox.push(r);(db.cursors[0] as any).pull_cursor++}
  else if(part==='metadata-proof')m.history[0].wire_digest='0'.repeat(64)
  else if(part==='metadata-wire'){const r=db.inbox[0] as any,w=JSON.parse(r.wire_item);w.object.ciphertext='AAAA';r.wire_item=JSON.stringify(w)}
  else if(part==='missing-ancestor')m.history.shift()
  else if(part==='note-proof'){const r=db.inbox.find((r:any)=>r.state==='content_note_proven') as any;r.content_note_proof.outcome_digest='0'.repeat(64)}
  else if(part==='F-proof')(db.inbox.find((r:any)=>r.event_id===f.r.event_id) as any).resolution_proof.dependency_digest='0'.repeat(64)
  else if(part==='F-evidence')(db.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).evidence_envelope.ciphertext='AAAA'
  else if(part==='Head2')(db.legacyNoteHistory!.find((r:any)=>r.record_kind==='head'&&r.record_version===2) as any).head_revision++
  else if(part==='source-revision')(db.localProjects![0] as any).source_revision++
  else if(part==='source-AEAD')(db.localNotes![0] as any).envelope.ciphertext='AAAA'
  else if(part==='generation')(db.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).record_version=999
  else if(part==='foreign-account')(db.inbox[0] as any).account_id=crypto.randomUUID()
  else if(part==='foreign-bootstrap')(db.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  else if(part==='own'){const r=db.inbox[0] as any,w=JSON.parse(r.wire_item);w.event.device_id=scope.deviceId;r.wire_item=JSON.stringify(w)}
  else db.outbox.push({account_id:scope.accountId})
  const before=f.before()
  await expect(create().inspect(scope)).rejects.toMatchObject({name:'HistoricalPrefixQualificationError',...(part==='gap'||part==='foreign-account'?{code:'missing_sequence',sequence:part==='gap'?f.update.reference.server_sequence:1}:part==='duplicate-sequence'?{code:'duplicate_sequence',sequence:1}:{code:'invalid_history'})})
  expect(f.before()).toEqual(before)
 },5000)
 it('uses internal authentication, with no writes, nonces, HTTP or public diagnostic',async()=>{
  vi.spyOn(BrowserResolutionPrefix.prototype,'bind').mockImplementation(()=>{throw Error('NO_Q_CERTIFICATE')})
  vi.spyOn(BrowserResolutionPrefix.prototype,'bindMixedSources').mockImplementation(()=>{throw Error('NO_Q_CERTIFICATE')})
  vi.spyOn(BrowserHistoricalMetadataDependency.prototype,'bind').mockImplementation(()=>{throw Error('NO_PUBLIC_13')})
  vi.spyOn(BrowserHistoricalContentAuthentication.prototype,'bind').mockImplementation(()=>{throw Error('NO_PUBLIC_14')})
  const tx:BrowserSyncTransaction=(s,n,mode,run)=>{expect(mode).toBe('readonly');return f.transaction(s,n,mode,run)}
  const random=vi.spyOn(crypto,'getRandomValues').mockImplementation(()=>{throw Error('NO_NONCE')}),http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_HTTP')),before=f.before()
  expect((await create(tx).inspect(scope)).candidate_historical_prefix).toBe(16);expect(random).not.toHaveBeenCalled();expect(http).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
 },5000)
 it('cannot be used by owner, Metadata, Q, transport or ACK APIs',async()=>{
  const result=await create().inspect(scope),g=new BrowserResolutionPrefix(f.transaction,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),k=new BrowserV10Recovery(f.transaction,f.f.localOwner,()=>true).bindMixedSources(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),before=f.before(),http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_HTTP'))
  await expect(f.owner.commit(result as never)).rejects.toThrow();await expect(f.h.commit(result as never)).rejects.toThrow()
  await expect(g.prepareCommit(result as never)).rejects.toThrow();await expect(g.commit(result as never)).rejects.toThrow()
  await expect(f.f.proven.prepareAck(scope,result as never)).rejects.toThrow();await expect(f.f.proven.ackOnce(result as never)).rejects.toThrow()
  await expect(f.f.metadata.apply(scope,result as never,f.f.auth,f.f.bindings as never,f.f.keys as never)).rejects.toThrow()
  await expect(prerequisites.prepareNoteTransportCommit(result as never,f.ordinary.plaintext,{} as never)).rejects.toThrow()
  await expect(g.prepare(scope)).rejects.toThrow();await expect(k.run(scope)).rejects.toThrow();expect(http).not.toHaveBeenCalled();expect(f.before()).toEqual(before)
 },5000)
 for(const kind of ['key','account','device','profile','epoch','logout'] as const)it(`rejects ${kind} revocation`,async()=>{
  const reader=create(),before=f.before();let s=scope
  if(kind==='key')f.f.lock();else if(kind==='profile')active=false;else if(kind==='epoch')await f.f.auth.login('fixture','fixture');else if(kind==='logout')await f.f.auth.logout();else s={...scope,...(kind==='account'?{accountId:crypto.randomUUID()}:{deviceId:crypto.randomUUID()})}
  await expect(reader.inspect(s)).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
 it('rejects revocation during Metadata crypto',async()=>{
  const original=readers.openBrowserCanonicalObject;let fired=false
  vi.spyOn(readers,'openBrowserCanonicalObject').mockImplementation(async(...args)=>{const r=await original(...args);if(!fired){fired=true;f.f.lock()}return r})
  const before=f.before();await expect(create().inspect(scope)).rejects.toMatchObject({code:'closed'});expect(f.before()).toEqual(before)
 },5000)
 for(const operation of ['delete','update','competing'] as const)it(`rejects actual Metadata ${operation}`,async()=>{
  const a=await metadataRow(f.f,17,{revision:4,parent:operation==='competing'?f.update.event.header.event_id:f.deletion.event.header.event_id,change:e=>{if(operation==='delete'){e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}}})
  if(operation!=='competing')await f.f.metadata.apply(scope,a.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  const before=f.before();await expect(create().inspect(scope)).rejects.toMatchObject({code:'invalid_history'});expect(f.before()).toEqual(before)
 },5000)
 it('rejects an actual owner change at the final complete snapshot read',async()=>{
  let n=0
  const tx:BrowserSyncTransaction=async(s,stores,mode,run)=>{if(++n===2){const a=await metadataRow(f.f,17,{revision:4,parent:f.deletion.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}});await f.f.metadata.apply(scope,a.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)}return f.transaction(s,stores,mode,run)}
  await expect(create(tx).inspect(scope)).rejects.toMatchObject({code:'stale_source'})
 },5000)
 it('rejects a stale cursor without trusting an old candidate',async()=>{
  let n=0
  const tx:BrowserSyncTransaction=(s,stores,mode,run)=>{if(++n===2)(f.f.db.cursors[0] as any).proven_prefix++;return f.transaction(s,stores,mode,run)}
  await expect(create(tx).inspect(scope)).rejects.toMatchObject({code:'stale_source'})
 },5000)
 it('rejects a failed readonly inventory load and safely reauthenticates afterward',async()=>{
  const before=f.before(),tx:BrowserSyncTransaction=()=>Promise.reject(Error('NEGATIVE_READ_ABORT'))
  await expect(create(tx).inspect(scope)).rejects.toThrow();expect(f.before()).toEqual(before);expect((await create().inspect(scope)).candidate_historical_prefix).toBe(16)
 },5000)
 it('rejects valid-AEAD source drift despite authentic historical Metadata',async()=>{
  const raw=f.f.db.localNotes!.find((r:any)=>!r.deleted) as any,bytes=await openHistoricalJson(scope,raw.project_id,raw.note_id,'note',raw.envelope,amk,()=>true)
  const p=JSON.parse(new TextDecoder().decode(bytes));bytes.fill(0);p.source.note.content='NEGATIVE_SOURCE_DRIFT'
  const encoded=new TextEncoder().encode(canonical(p)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:raw.project_id,entityId:raw.note_id,entityType:'note'},encoded)
  try{raw.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{encoded.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
  const before=f.before();expect((await f.reader.inspect(scope,f.ordinary.event_id)).historicalMetadataAdmissible).toBe(true);await expect(create().inspect(scope)).rejects.toMatchObject({code:'invalid_history'});expect(f.before()).toEqual(before)
 },5000)
 for(const family of ['stage','stage_order','unrelated-note'] as const)it(`does not hide later unsupported ${family}`,async()=>{
  await f.receive('earlier-pending')
  if(family==='unrelated-note')await f.receive('foreign-project',null,1,false,{protocol:2,project:'q'})
  else if(family==='stage')await stageRow({...f.f,metadataEvent:f.m.event} as never,18)
  else await orderRow({...f.f,metadataEvent:f.m.event,stageEvents:[]} as never,18)
  const before=f.before();await expect(create().inspect(scope)).rejects.toMatchObject({code:'unsupported_family',sequence:18});expect(f.before()).toEqual(before)
 },5000)
})
for(const cohort of ['pending-before','pending-after','fork','Stage'] as const)describe(cohort,()=>{
 let base:Base,f:Fixture
 beforeEach(async()=>{base=await ordinaryV10Fixture('keep_both',3,false,cohort==='Stage')},5000)
 beforeEach(async()=>{f=await historicalMetadataAfterOrdinary(base,'keep_both',{pending:cohort==='pending-before',fork:cohort==='fork'})},5000)
 it('blocks at the first pending sequence or rejects the unsupported full cohort',async()=>{
  const pending=cohort==='pending-after'?await f.receive('after-delete'):f.pending,before=f.before(),reader=bind(f)
  if(pending){
   const result=await reader.inspect(scope)
   expect(result).toMatchObject({candidate_historical_prefix:pending.sequence-1,first_blocking_sequence:pending.sequence,blocker:'received',counts:{metadata:cohort==='pending-before'?2:3}})
   expect(Object.values(result.counts).reduce((a,b)=>a+b,0)).toBe(result.candidate_historical_prefix)
   expect(await reader.inspect(scope)).toEqual(result)
  }else await expect(reader.inspect(scope)).rejects.toMatchObject({code:cohort==='Stage'?'unsupported_family':'invalid_history'})
  expect(f.before()).toEqual(before)
 },5000)
 if(cohort==='pending-before')it('cannot use a corrupt existing prefix to cross its unqualified pending event',async()=>{
  ;(f.f.db.cursors[0] as any).proven_prefix=f.pending!.sequence
  const before=f.before();await expect(bind(f).inspect(scope)).rejects.toMatchObject({code:'unqualified_proven_sequence',sequence:f.pending!.sequence});expect(f.before()).toEqual(before)
 },5000)
})
describe('F/H-only historical order',()=>{
 let base:Base
 beforeEach(async()=>{base=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{
  const a=await base.receive('content-note',base.children[0]!.event_id,5),b=await base.receive('retained-note',base.children[1]!.event_id,5)
  await base.h.apply(scope,b.sequence);await base.h.apply(scope,a.sequence)
  const m=await metadataRow(base.f,(base.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:base.m.event.header.event_id});await base.f.metadata.apply(scope,m.reference,base.f.auth,base.f.bindings as never,base.f.keys as never)
  const d=await metadataRow(base.f,m.reference.server_sequence+1,{revision:3,parent:m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}});await base.f.metadata.apply(scope,d.reference,base.f.auth,base.f.bindings as never,base.f.keys as never)
 },5000)
 it('qualifies both roles without imposing mixed source order',async()=>{
  const before=base.before(),result=await bind(base).inspect(scope)
  expect(result).toMatchObject({sourceCohort:'historical',candidate_historical_prefix:(before.cursors[0] as any).pull_cursor,first_blocking_sequence:null});expect(base.before()).toEqual(before)
 },5000)
})

it('requires one actual F even when a genuine ordinary-only history has a Metadata tombstone',async()=>{
 const f=await routeSetup();await contentRow(f);await new BrowserContentNoteApplyRuntime(f.notes).apply(scope,2)
 const m=await metadataRow(f,3,{revision:2,parent:f.m.event.header.event_id});await f.metadata.apply(scope,m.reference,f.auth,f.bindings as never,f.keys as never)
 const d=await metadataRow(f,4,{revision:3,parent:m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}});await f.metadata.apply(scope,d.reference,f.auth,f.bindings as never,f.keys as never)
 const before=structuredClone(f.db),v=await f.transaction<ResolutionInventorySnapshot>(scope,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,scope,()=>true,result,abort))
 await expect(inspectTerminalMetadataHistoricalPrefix(scope,v,amk,()=>true)).rejects.toMatchObject({code:'invalid_history'});expect(f.db).toEqual(before)
},5000)
