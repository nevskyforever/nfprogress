// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {plannerFixture,receiveLegacyResolutionOn3} from './resolutionPlanner.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'
import {BrowserV10Transport} from './v10Transport'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {BrowserResolutionPrefix} from './resolutionPrefix'
import {BrowserV10Recovery} from './v10Recovery'
import {BrowserV10OrdinaryApply} from './v10OrdinaryApply'
import {BrowserMixedSourceWitness} from './mixedSourceWitness'
import {bindPrivateMetadataPrefix} from './privateMetadataPrefix'
import {authenticateResolutionHistory,authenticateTerminalMetadataResolutions,authenticateMetadataHandoffResolutions} from './resolutionAuthentication'
import {validateResolution4,validateResolutionProof1,validateResolutionInbox10} from './resolutionRecords'
import {noteProofDigest} from './legacyNoteApply'
import {fixtureDigest,sealResolutionFixture} from './resolution.testFixture'
import {decryptObjectBytes,encryptObjectBytes} from '@/crypto'
import {decodeBase64Url,encodeBase64Url} from '@/api/base64url'
import {decodeNoteSyncResolutionV2,encodeNoteSyncResolutionV2} from '@/cloud/noteSyncResolutionV2Codec'
import {unframeContentNote} from '@/cloud/contentNoteCodec'

afterEach(()=>vi.restoreAllMocks())
const strategies=['choose_version','manual_merge','delete','keep_both'] as const
const inventory=(f:Awaited<ReturnType<typeof plannerFixture>>)=>{const d=f.f.db;return{history:d.legacyNoteHistory!,rows:d.inbox,bindings:d.projectBindings,owners:d.ownerHeads!,out:d.outbox,receipts:d.receipts,projects:d.localProjects!,localNotes:d.localNotes!,intents:d.legacyNoteIntents!,checkpoints:d.cursors,cursor:d.cursors[0] as any}}
async function setup(strategy:typeof strategies[number]='keep_both',raw3=true){
 const f=await plannerFixture(strategy,2,false,true)
 const rawPage=raw3?await receiveLegacyResolutionOn3(f):JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[JSON.parse(f.received.wire_item)],next_cursor:f.sequence,has_more:false})
 const transport=new BrowserV10Transport(f.f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const applier=f.runtime.atomicApply(),apply=async()=>{const p=await f.runtime.prepare(scope,f.sequence);return applier.commit(await applier.prepare(p.token))}
 return{f,transport,applier,apply,rawPage}
}
async function rehashApplied(f:Awaited<ReturnType<typeof plannerFixture>>){
 const d=f.f.db,r=d.legacyNoteHistory!.find((a:any)=>a.record_kind==='resolution') as any,t=d.legacyNoteHistory!.find((a:any)=>a.record_kind==='group_transition') as any
 r.record_digest=await fixtureDigest(r);t.resolution_digest=r.record_digest;t.record_digest=await fixtureDigest(t)
 for(const h of d.legacyNoteHistory! as any[])if(h.record_kind==='head')h.node_ref.resolution_digest=r.record_digest
 Object.assign(f.received.resolution_proof,{dependency_digest:r.dependency_digest,resolution_digest:r.record_digest,transition_digest:t.record_digest})
 f.received.resolution_proof.outcome_digest=await fixtureDigest(f.received.resolution_proof,'outcome_digest')
}
for(const strategy of strategies)it(`raw3 ${strategy}: real receive/owner/evidence and exact read-only replay`,async()=>{
 const {f,transport,applier,apply,rawPage}=await setup(strategy),before=f.before()
 expect(f.received).toMatchObject({protocol_version:3,state:'received'})
 const wire=JSON.parse(f.received.wire_item),bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},{...wire.object,nonce:decodeBase64Url(wire.object.nonce),ciphertext:decodeBase64Url(wire.object.ciphertext)})
 try{expect(decodeNoteSyncResolutionV2(bytes)).toEqual(f.resolution);expect(()=>unframeContentNote(bytes)).toThrow()}finally{bytes.fill(0)}
 expect(await apply()).toEqual({status:'applied'})
 const v=inventory(f),r=v.history.find((r:any)=>r.record_kind==='resolution') as any,row=f.received
 expect(validateResolution4(r,scope)).toMatchObject({protocol_version:3,transport_kind:'legacy_resolution_v2'})
 expect(validateResolutionProof1(row.resolution_proof,scope)).toMatchObject({protocol_version:3,reference:{operation:'resolution'}})
 expect(validateResolutionInbox10(row,scope)).toEqual(row)
 expect(r.wire_digest).toBe(await noteProofDigest({protocol_version:3,item:wire}))
 expect(r.wire_digest).not.toBe(await noteProofDigest({protocol_version:2,item:wire}))
 const e=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},{...r.evidence_envelope,nonce:decodeBase64Url(r.evidence_envelope.nonce),ciphertext:decodeBase64Url(r.evidence_envelope.ciphertext)})
 try{expect(JSON.parse(new TextDecoder().decode(e)).authenticated_payload.wrapper_payload_digest).toBeNull()}finally{e.fill(0)}
 expect((await authenticateResolutionHistory(scope,v,amk,()=>true)).resolutions).toBe(1)
 expect(v.history.filter((r:any)=>r.record_kind==='head')).toHaveLength(strategy==='keep_both'?2:1)
 for(const name of ['outbox','receipts','cursors','projectBindings','ownerHeads','legacyNoteIntents'] as const)expect(f.f.db[name]).toEqual(before[name])
 const after=f.before();expect(await applier.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
 // Native J interval replay for all four strategies is exercised in Chromium.
 await expect(transport.joinRetainedF2(scope,f.sequence-1,rawPage,row.event_id)).rejects.toThrow()
 expect(f.before()).toEqual(after)
})
for(const strategy of strategies)it(`F2 ${strategy}: exact3 refetch joins genuine unchanged retained authority`,async()=>{
 const {f,transport,apply,rawPage}=await setup(strategy,false);await apply();const before=f.before(),calls=f.f.calls.length
 expect(await transport.joinRetainedF2(scope,f.sequence-1,rawPage,f.received.event_id)).toMatchObject({matched:true,retainedProtocol:2,receivedProtocol:3,commitAuthorized:false,ackAuthorized:false})
 expect(f.before()).toEqual(before);expect(f.f.calls.slice(calls).every((c:{mode:string})=>c.mode==='readonly')).toBe(true)
})
for(const mutation of ['ciphertext','nonce','aad','crypto','operation','event','device','project','sequence','revision','timestamp','deleted_at'] as const)it(`raw3 original ${mutation} rejects before owner writes`,async()=>{
 const {f}=await setup(),w=JSON.parse(f.received.wire_item)
 if(mutation==='ciphertext'||mutation==='nonce')w.object[mutation]=(w.object[mutation][0]==='A'?'B':'A')+w.object[mutation].slice(1)
 if(mutation==='aad')w.object.aad_version=2
 if(mutation==='crypto')w.object.crypto_version=2
 if(mutation==='operation')w.event.operation='event'
 if(mutation==='event')w.event.event_id=crypto.randomUUID()
 if(mutation==='device')w.event.device_id=scope.deviceId
 if(mutation==='project')w.event.project_id='foreign'
 if(mutation==='sequence')w.event.server_sequence++
 if(mutation==='revision')w.event.revision++
 if(mutation==='timestamp')w.event.updated_at='2026-10-14T00:00:00.000000Z'
 if(mutation==='deleted_at')w.event.deleted_at=w.event.updated_at
 f.received.wire_item=JSON.stringify(w);const before=f.before()
 await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const mutation of ['stage','map','format','missing_parent','publication','bootstrap','clone'] as const)it(`raw3 ${mutation} source/parent constraints remain strict`,async()=>{
 const {f}=await setup(),d=f.f.db
 if(['stage','map','format'].includes(mutation)){
  const n=f.resolution.resolution.strategy==='keep_both'?f.resolution.resolution.retained_note:null
  if(!n)throw Error('keep_both fixture')
  if(mutation==='stage')n.stage_id='unsupported-stage'
  if(mutation==='map'){n.source_type='mindmap';n.source_map_id='m';n.source_node_id='node'}
  if(mutation==='format')n.content_format='plain'
  await f.reseal(true)
 }
 if(mutation==='missing_parent')d.legacyNoteHistory=d.legacyNoteHistory!.filter((r:any)=>r.event_id!==f.parents[0]!.event_id)
 if(mutation==='publication')d.inbox=d.inbox.filter((r:any)=>r.event_id!==f.parents[0]!.event_id)
 if(mutation==='bootstrap')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
 if(mutation==='clone')d.localNotes!.push({...d.localNotes![0] as any,note_id:'retained-note'})
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const mutation of ['missing','proof','parent','gap','source','bootstrap','ciphertext','descriptor','sequence'] as const)it(`F2 join rejects ${mutation} with zero mutation`,async()=>{
 const {f,transport,apply,rawPage}=await setup('keep_both',false);await apply();const page=JSON.parse(rawPage),d=f.f.db
 if(mutation==='missing')d.inbox.pop()
 if(mutation==='gap')d.inbox.shift()
 if(mutation==='proof')f.received.resolution_proof.outcome_digest='0'.repeat(64)
 if(mutation==='parent')d.inbox.splice(2,1)
 if(mutation==='source')(d.localNotes![0] as any).source_revision++
 if(mutation==='bootstrap')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
 if(mutation==='ciphertext')page.items[0].object.ciphertext=(page.items[0].object.ciphertext[0]==='A'?'B':'A')+page.items[0].object.ciphertext.slice(1)
 if(mutation==='descriptor')page.items[0].event.revision++
 if(mutation==='sequence'){page.items[0].event.server_sequence++;page.next_cursor++}
 const before=f.before();await expect(transport.joinRetainedF2(scope,f.sequence-1,JSON.stringify(page),f.resolution.header.event_id)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const mutation of ['proof_protocol','record_codec','evidence','duplicate_event','duplicate_sequence','additional_resolution'] as const)it(`raw3 durable ${mutation} cannot authenticate`,async()=>{
 const {f,apply,applier}=await setup();await apply();const d=f.f.db,r=d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any
 if(mutation==='proof_protocol'){f.received.protocol_version=2;f.received.resolution_proof.protocol_version=2;f.received.resolution_proof.outcome_digest=await fixtureDigest(f.received.resolution_proof,'outcome_digest')}
 if(mutation==='record_codec')r.transport_kind='content_note_resolution_v2'
 if(mutation==='evidence'){
  // Rehash all public references consistently, leaving the authentic encrypted
  // identity untouched. Only authenticated evidence can reject this forgery.
  r.dependency_digest='0'.repeat(64);await rehashApplied(f)
 }
 if(mutation==='duplicate_event')d.inbox.push({...f.received,server_sequence:f.sequence+1})
 if(mutation==='duplicate_sequence')d.inbox.push({...f.received,event_id:crypto.randomUUID()})
 if(mutation==='additional_resolution')d.legacyNoteHistory!.push({...r,event_id:crypto.randomUUID()})
 const before=f.before();await expect(applier.reconcile(scope,f.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const mutation of ['source','binding','metadata','cursor','history','inbox','key','logout','profile','epoch','device'] as const)it(`raw3 commit rejects changed ${mutation}`,async()=>{
 const {f,applier}=await setup(),plan=await f.runtime.prepare(scope,f.sequence),token=await applier.prepare(plan.token),d=f.f.db
 if(mutation==='source')(d.localProjects![0] as any).source_revision++
 if(mutation==='binding')(d.projectBindings[0] as any).remote_high_water++
 if(mutation==='metadata')(d.ownerHeads![0] as any).head_revision++
 if(mutation==='cursor')(d.cursors[0] as any).pull_cursor++
 if(mutation==='history')(d.legacyNoteHistory![0] as any).record_id='changed'
 if(mutation==='inbox')f.received.wire_item+=' '
 if(mutation==='key')f.f.lock()
 if(mutation==='logout')await f.f.auth.logout()
 if(mutation==='profile')f.close()
 if(mutation==='epoch')await f.f.auth.login('fixture','fixture')
 if(mutation==='device')vi.spyOn(f.f.auth,'isCurrent').mockReturnValue(false)
 const before=f.before();await expect(applier.commit(token)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('Y admits independent read-only Q while raw3 stays blocked in K/O and mixed/private authority',async()=>{
 const {f,apply}=await setup();await apply();const d=f.f,before=f.before(),args=[d.auth,d.bindings as never,d.keys as never,f.device] as const
 const h=new BrowserResolutionContinuation(d.transaction,d.localOwner,()=>true).bind(...args)
 const g=new BrowserResolutionPrefix(d.transaction,()=>true),k=new BrowserV10Recovery(d.transaction,d.localOwner,()=>true)
 const o=new BrowserV10OrdinaryApply(d.transaction,d.localOwner,()=>true).bind(...args)
 expect(await h.history(scope)).toMatchObject({readOnly:true,resolutions:1})
 const gp=g.bind(...args);expect(await gp.calculate(await gp.prepare(scope))).toMatchObject({readOnly:true,ackAuthorized:false,counts:{resolution:1}})
 const q=g.bindMixedSources(...args);expect(await q.calculate(await q.prepare(scope))).toMatchObject({readOnly:true,ackAuthorized:false,counts:{resolution:1}})
 for(const action of [()=>k.bind(...args).run(scope),()=>k.bindPostFMetadata(...args).run(scope),()=>o.apply(scope,f.sequence),()=>new BrowserMixedSourceWitness(d.transaction,()=>true).bind(...args).inspect(scope),()=>bindPrivateMetadataPrefix(d.transaction,()=>true,...args).prepare(scope)])await expect(action()).rejects.toThrow()
 await expect(authenticateTerminalMetadataResolutions(scope,inventory(f),amk,()=>true)).rejects.toThrow()
 await expect(authenticateMetadataHandoffResolutions(scope,inventory(f),amk,()=>true,{kind:'durable'})).rejects.toThrow()
 expect(f.before()).toEqual(before)
})
for(const strategy of strategies)it(`raw3 ${strategy} preserves genuine mixed Legacy/Content parent dependencies`,async()=>{
 const f=await plannerFixture(strategy,2,false,false,{mixed:true}),old=f.received,w=JSON.parse(old.wire_item)
 const bytes=encodeNoteSyncResolutionV2(f.resolution),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes)
 try{w.event.operation='resolution';w.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.event_id!==old.event_id);(f.f.db.cursors[0] as any).pull_cursor=f.sequence-1
 await f.f.sync.commitInboundPage(scope,f.sequence-1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[w],next_cursor:f.sequence,has_more:false}))
 expect(new Set(f.parents.map(p=>p.record_version))).toEqual(new Set([1,2]))
 const p=await f.runtime.prepare(scope,f.sequence),apply=f.runtime.atomicApply();await apply.commit(await apply.prepare(p.token))
 expect((await authenticateResolutionHistory(scope,inventory(f),amk,()=>true)).resolutions).toBe(1)
 expect(await apply.reconcile(scope,f.sequence)).toEqual({status:'already_applied'})
})
for(const mutation of ['accountId','canonicalUserId','deviceId','key','logout','profile','expired'] as const)it(`F2 join reauthenticates ${mutation}`,async()=>{
 const {f,transport,apply,rawPage}=await setup('choose_version',false);await apply();let s={...scope}
 if(['accountId','canonicalUserId','deviceId'].includes(mutation))s={...s,[mutation]:crypto.randomUUID()}
 if(mutation==='key')f.f.lock()
 if(mutation==='logout')await f.f.auth.logout()
 if(mutation==='profile')f.close()
 if(mutation==='expired')vi.spyOn(f.f.auth,'isCurrent').mockReturnValue(false)
 const before=f.before();await expect(transport.joinRetainedF2(s,f.sequence-1,rawPage,f.received.event_id)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('fresh receive cannot substitute for missing retained F2 application',async()=>{
 const {f,transport,rawPage}=await setup('choose_version',false),before=f.before()
 await expect(transport.joinRetainedF2(scope,f.sequence-1,rawPage,f.received.event_id)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('F2 join detects concurrent inventory change after AEAD before returning',async()=>{
 const {f,apply,rawPage}=await setup('choose_version',false);await apply();let reads=0
 const tx:BrowserSyncTransaction=(s,stores,mode,callback)=>{
  if(++reads===2)(f.f.db.cursors[0] as any).proven_prefix++
  return f.f.transaction(s,stores,mode,callback)
 }
 const j=new BrowserV10Transport(tx,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 const before=f.before();await expect(j.joinRetainedF2(scope,f.sequence-1,rawPage,f.received.event_id)).rejects.toMatchObject({code:'stale_source'})
 ;(before.cursors[0] as any).proven_prefix++;expect(f.before()).toEqual(before)
})
it('pending raw3 keep_both reserves its clone before another F owner applies',async()=>{
 const {f}=await setup(),pending=structuredClone(f.resolution),w=JSON.parse(f.received.wire_item)
 pending.header.event_id=crypto.randomUUID();pending.header.entity_id='other-note';pending.result.note.id='other-note'
 const bytes=encodeNoteSyncResolutionV2(pending),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'other-note',entityType:'note'},bytes)
 try{Object.assign(w.event,{event_id:pending.header.event_id,entity_id:'other-note',server_sequence:f.sequence+1});w.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[w],next_cursor:f.sequence+1,has_more:false}))
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toMatchObject({code:'clone_collision'});expect(f.before()).toEqual(before)
})
it('authenticated raw3 evidence rejects a non-null Content wrapper even after public rehash',async()=>{
 const {f,apply,applier}=await setup();await apply();const r=f.f.db.legacyNoteHistory!.find((a:any)=>a.record_kind==='resolution') as any
 const bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},{...r.evidence_envelope,nonce:decodeBase64Url(r.evidence_envelope.nonce),ciphertext:decodeBase64Url(r.evidence_envelope.ciphertext)})
 let e:any;try{e=JSON.parse(new TextDecoder().decode(bytes))}finally{bytes.fill(0)}
 e.authenticated_payload.wrapper_payload_digest='0'.repeat(64);r.evidence_envelope=await sealResolutionFixture(e);await rehashApplied(f)
 const before=f.before();await expect(applier.reconcile(scope,f.sequence)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('a genuine further raw3 receive cannot authorize an additional Resolution generation',async()=>{
 const {f,apply}=await setup();await apply();const next=structuredClone(f.resolution),w=JSON.parse(f.received.wire_item)
 next.header.event_id=crypto.randomUUID();const bytes=encodeNoteSyncResolutionV2(next),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},bytes)
 try{Object.assign(w.event,{event_id:next.header.event_id,server_sequence:f.sequence+1});w.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[w],next_cursor:f.sequence+1,has_more:false}))
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence+1)).rejects.toThrow();expect(f.before()).toEqual(before)
})
