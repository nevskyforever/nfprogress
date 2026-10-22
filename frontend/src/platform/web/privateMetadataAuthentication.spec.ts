// @vitest-environment node
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {ordinaryV10Fixture} from './v10OrdinaryApply.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import {metadataRow} from './metadataPrefix.testFixture'
import {authenticatePrivateMetadataSource} from './mixedSourceValidation'
import {resolutionInventoryStores,scheduleResolutionInventory,type ResolutionInventorySnapshot} from './resolutionPlanner'
import type {MetadataHandoffInspection} from './historicalMetadataDependency'
import {metadataProofFor} from './importedMetadataApply'
import {noteProofDigest} from './legacyNoteApply'
import {BrowserHistoricalMetadataDependency} from './historicalMetadataDependency'
import {openBrowserCanonicalObject} from './canonicalReaders'
import {decodeBase64Url,encodeBase64Url} from '@/api/base64url'
import {frameContentNote,type ContentNoteEvent} from '@/cloud/contentNoteCodec'
import {encryptObjectBytes} from '@/crypto'
import {stageRow} from './stageApply.testFixture'

type Fixture=Awaited<ReturnType<typeof ordinaryV10Fixture>>
const inventory=(f:Fixture)=>f.transaction<ResolutionInventorySnapshot>(scope,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,scope,()=>true,result,abort))
const check=async(f:Fixture,mode:MetadataHandoffInspection)=>authenticatePrivateMetadataSource(scope,await inventory(f),amk,()=>true,mode)
afterEach(()=>vi.restoreAllMocks())
for(const protocol of [2,3] as const)for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)describe(`private authentication F${protocol}/${strategy}`,()=>{
 let f:Fixture
 beforeEach(async()=>{f=await ordinaryV10Fixture(strategy,protocol,protocol===3)},5000)
 it('authenticates active history and a real pending update without changing an outcome',async()=>{
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:f.m.event.header.event_id,compressed:true}),before=f.before()
  await check(f,{kind:'pending',sequence:m.reference.server_sequence});expect(f.before()).toEqual(before)
  const wire=JSON.parse(m.row.wire_item),proof=metadataProofFor(scope,m.reference,m.event,await noteProofDigest({protocol_version:3,event:m.reference,object:wire.object}),3)
  await check(f,{kind:'prediction',sequence:m.reference.server_sequence,proof});expect(f.before()).toEqual(before)
  expect(m.row.state).toBe('received')
 },5000)
 it('authenticates a predicted delete separately from the genuine durable delete',async()=>{
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:f.m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}})
  const before=f.before();await check(f,{kind:'pending',sequence:m.reference.server_sequence})
  const wire=JSON.parse(m.row.wire_item),proof=metadataProofFor(scope,m.reference,m.event,await noteProofDigest({protocol_version:3,event:m.reference,object:wire.object}),3)
  await check(f,{kind:'prediction',sequence:m.reference.server_sequence,proof});expect(f.before()).toEqual(before)
  await f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  await check(f,{kind:'durable'})
 },5000)
})
describe('private authentication fail closed',()=>{
 let f:Fixture,m:Awaited<ReturnType<typeof metadataRow>>
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:f.m.event.header.event_id,compressed:true})},5000)
 for(const fault of ['gap','duplicate','wrong-sequence','proven-pending','suffix','ancestor','proof','source','bootstrap','own','stage','outbox','wrong-prediction','candidate-AEAD','candidate-bootstrap','unrelated-note'] as const)it(`rejects ${fault} with byte-identical storage`,async()=>{
  let sequence=m.reference.server_sequence
  if(fault==='gap')f.f.db.inbox.shift()
  else if(fault==='duplicate')f.f.db.inbox.push(structuredClone(f.f.db.inbox[0]))
  else if(fault==='wrong-sequence')sequence--
  else if(fault==='proven-pending')(f.f.db.cursors[0] as any).proven_prefix=sequence
  else if(fault==='suffix')await metadataRow(f.f,sequence+1,{revision:3,parent:m.reference.event_id})
  else if(fault==='ancestor')(f.f.db.ownerHeads![0] as any).history=[]
  else if(fault==='proof')(f.f.db.inbox.find((r:any)=>r.state==='content_note_proven') as any).content_note_proof.outcome_digest='0'.repeat(64)
  else if(fault==='source')(f.f.db.localProjects![0] as any).source_revision++
  else if(fault==='bootstrap')(f.f.db.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  else if(fault==='own'){const w=JSON.parse(m.row.wire_item);w.event.device_id=scope.deviceId;m.row.wire_item=JSON.stringify(w)}
  else if(fault==='stage')await stageRow({...f.f,metadataEvent:f.m.event} as never,sequence+1)
  else if(fault==='outbox')f.f.db.outbox.push({account_id:scope.accountId})
  else if(fault==='unrelated-note')await f.receive('private-unrelated',null,1,false,{protocol:2,project:'q'})
  else if(fault==='candidate-AEAD'){const wire=JSON.parse(m.row.wire_item);wire.object.ciphertext='AAAA';m.row.wire_item=JSON.stringify(wire)}
  else if(fault==='candidate-bootstrap'){
   f.f.db.inbox.pop();(f.f.db.cursors[0] as any).pull_cursor--
   m=await metadataRow(f.f,sequence,{revision:2,parent:f.m.event.header.event_id,change:e=>{e.header.bootstrap_id=crypto.randomUUID()}})
  }
  const before=f.before()
  await expect(check(f,fault==='wrong-prediction'?{kind:'prediction',sequence,proof:{} as never}:{kind:'pending',sequence})).rejects.toThrow()
  expect(f.before()).toEqual(before)
 },5000)
 it('does not use public diagnostics or allocate nonces/HTTP',async()=>{
  vi.spyOn(BrowserHistoricalMetadataDependency.prototype,'bind').mockImplementation(()=>{throw Error('NO_PUBLIC_READER')})
  const nonce=vi.spyOn(crypto,'getRandomValues').mockImplementation(()=>{throw Error('NO_NONCE')}),http=vi.spyOn(globalThis,'fetch').mockRejectedValue(Error('NO_HTTP')),before=f.before()
  await check(f,{kind:'pending',sequence:m.reference.server_sequence});expect(f.before()).toEqual(before);expect(nonce).not.toHaveBeenCalled();expect(http).not.toHaveBeenCalled()
 },5000)
 it('rejects pending Content earlier than Metadata rather than skipping it',async()=>{
  // Real sender adds a new later Content row. A pending Metadata is still the earliest.
  await f.receive('later-content');await check(f,{kind:'pending',sequence:m.reference.server_sequence})
  const row=f.f.db.inbox.find((r:any)=>r.state==='content_note_proven') as any
  // Negative corruption is never used as positive evidence.
  row.state='received';delete row.content_note_proof
  const before=f.before();await expect(check(f,{kind:'pending',sequence:m.reference.server_sequence})).rejects.toThrow();expect(f.before()).toEqual(before)
 },5000)
})

describe('genuine mixed O/H evidence before private authentication',()=>{
 let f:Fixture
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{
  const o=await f.receive('private-independent',null,1,false,{protocol:3,compressed:true});await f.owner.apply(scope,o.sequence)
  const h=await f.receive('content-note',f.children[0]!.event_id,5,false,{protocol:3,compressed:false});await f.h.apply(scope,h.sequence)
  const retained=await f.receive('retained-note',f.children[1]!.event_id,5,false,{protocol:3,compressed:true});await f.h.apply(scope,retained.sequence)
 },5000)
 it('independently authenticates exact mixed source with pending deletion',async()=>{
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:2,parent:f.m.event.header.event_id,change:e=>{e.header.operation='delete';e.metadata=null;e.deleted_at=e.header.updated_at}}),before=f.before()
  await check(f,{kind:'pending',sequence:m.reference.server_sequence});expect(f.before()).toEqual(before)
 },5000)
})

describe('genuine late Metadata dependency counterexample',()=>{
 let f:Fixture
 beforeEach(async()=>{f=await ordinaryV10Fixture()},5000)
 beforeEach(async()=>{
  const e=await f.receive('late-dependency',null,1,false,{protocol:3}),m=await metadataRow(f.f,e.sequence+1,{revision:2,parent:f.m.event.header.event_id})
  const row=f.f.db.inbox.find((r:any)=>r.event_id===e.event_id) as any,wire=JSON.parse(row.wire_item)
  const nonce=decodeBase64Url(wire.object.nonce),ciphertext=decodeBase64Url(wire.object.ciphertext)
  const content=await openBrowserCanonicalObject(amk,{accountId:scope.canonicalUserId,projectId:'p',entityId:'late-dependency',entityType:'note',eventId:e.event_id},{...wire.object,nonce,ciphertext}) as ContentNoteEvent
  nonce.fill(0);ciphertext.fill(0);content.dependencies.metadata_event_id=m.reference.event_id
  const frame=frameContentNote(content),object=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'late-dependency',entityType:'note'},frame)
  try{wire.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(object.nonce),ciphertext:encodeBase64Url(object.ciphertext)};row.wire_item=JSON.stringify(wire)}finally{frame.fill(0);object.nonce.fill(0);object.ciphertext.fill(0)}
  // Genuine old live owner allows the now-present reference; .17 must independently prove M<E.
  await f.f.metadata.apply(scope,m.reference,f.f.auth,f.f.bindings as never,f.f.keys as never)
  await f.owner.apply(scope,e.sequence)
 },5000)
 it('rejects genuine applied E with q(M)>q(E) without rewriting its immutable proof',async()=>{
  const m=await metadataRow(f.f,(f.f.db.cursors[0] as any).pull_cursor+1,{revision:3,parent:(f.f.db.ownerHeads![0] as any).tip_event_ids[0]}),before=f.before()
  await expect(check(f,{kind:'pending',sequence:m.reference.server_sequence})).rejects.toThrow('outside_interval');expect(f.before()).toEqual(before)
 },5000)
})
