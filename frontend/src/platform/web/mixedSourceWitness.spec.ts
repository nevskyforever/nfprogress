// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {recoveryFixture} from './v10Recovery.testFixture'
import {ordinaryBoundaryFixture} from './v10OrdinaryBoundary.testFixture'
import {BrowserMixedSourceWitness} from './mixedSourceWitness'
import {BrowserResolutionContinuation} from './resolutionContinuation'
import {scope,amk,note} from './bootstrap.testFixture'
import {candidateDigest} from './noteHistory'
import {authenticateContinuationHistory,openHistoricalJson} from './resolutionHistorical'
import {scheduleResolutionInventory,type ResolutionInventorySnapshot,resolutionInventoryStores} from './resolutionPlanner'
import {canonical} from '@/cloud/projectMetadataCodec'
import {encryptObjectBytes} from '@/crypto'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {frameMapEvent} from '@/cloud/mapCodec'
import {readerCases} from './canonicalReaders.testFixture'
import {openBrowserCanonicalObject} from './canonicalReaders'
import {encodeBase64Url} from '@/api/base64url'
import type {BrowserSyncTransaction} from './syncDurability'
afterEach(()=>vi.restoreAllMocks())
async function setup(strategy:Parameters<typeof recoveryFixture>[0]='keep_both',protocol:2|3=3,compressed=false,baseline=true){
 const f=await recoveryFixture(strategy,protocol,compressed,false,true,baseline)
 await f.runtime.run(scope,{maxEvents:32})
 let active=true
 const create=(tx:BrowserSyncTransaction=f.transaction)=>new BrowserMixedSourceWitness(tx,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 return{...f,create,witness:create(),revoke:()=>{active=false}}
}
for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)it(`genuine K/F/H baseline and complete witness protocol${protocol}/ID${compressed?1:0}/${strategy}`,async()=>{
 const f=await setup(strategy,protocol,compressed),before=f.before(),call=f.f.calls.length
 expect(Object.keys(f.witness)).toEqual(['inspect'])
 const result=await f.witness.inspect(scope)
 expect(result).toEqual({readOnly:true,commitAuthorized:false,ackAuthorized:false,ready:false,projects:1,baselineNotes:strategy==='keep_both'?4:3,hTransitions:strategy==='keep_both'?2:1,ordinaryTransitions:0,pendingEvents:0})
 expect(Object.isFrozen(result)).toBe(true);expect(f.before()).toEqual(before)
 expect(f.f.calls.slice(call).every(c=>c.mode==='readonly')).toBe(true)
 expect(await f.create().inspect(scope)).toEqual(result) // Fresh runtime, no cached authority.
})
it('genuine output-only F/H histories remain eligible with an empty independent baseline',async()=>{
 const f=await setup('keep_both',3,true,false)
 expect(await f.witness.inspect(scope)).toMatchObject({baselineNotes:2,hTransitions:2})
})
it('genuine H cross-role out-of-order commits remain historical, but outside the ordered mixed cohort',async()=>{
 const f=await recoveryFixture('keep_both',3,false,false,true,false)
 await f.runtime.run(scope,{maxEvents:5}) // Real F; leave both children received.
 const h=new BrowserResolutionContinuation(f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await h.apply(scope,f.children[1]!.sequence);await h.apply(scope,f.children[0]!.sequence)
 expect(await h.history(scope)).toMatchObject({readOnly:true,resolutions:1})
 const before=f.before(),n=new BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await expect(n.inspect(scope)).rejects.toMatchObject({code:'revision_order'});expect(f.before()).toEqual(before)
})
it('a genuine H-preserved new fork is an explicit barrier, never a source transition',async()=>{
 const f=await setup(),plaintext=structuredClone(f.children[0]!.payload);plaintext.header.event_id=crypto.randomUUID()
 const peer='44444444-4444-4444-8444-444444444444',frame=frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:f.f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:plaintext})
 const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame),sequence=f.sequence+1,h=plaintext.header
 try{await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:{event_id:h.event_id,device_id:peer,server_sequence:sequence,project_id:'p',entity_id:'content-note',entity_type:'note',operation:'event',revision:h.revision,updated_at:h.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 const continuation=new BrowserResolutionContinuation(f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 expect(await continuation.apply(scope,sequence)).toBe('conflict_preserved')
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'unresolved_fork'});expect(f.before()).toEqual(before)
})
it('a caller DTO cannot replace the genuine registered-device proof',async()=>{
 const f=await setup(),before=f.before(),forged=new BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,{} as never)
 await expect(forged.inspect(scope)).rejects.toMatchObject({code:'closed'});expect(f.before()).toEqual(before)
})
it('a genuine local-only member BEFORE F has no reconstructible baseline; no synthetic capture',async()=>{
 const f=await recoveryFixture('keep_both',3,false)
 const n=note('local-only');n.revision=0
 await f.f.local.createNote(scope,(await f.f.local.readSnapshot(scope,'p')).token,n)
 await expect(f.runtime.run(scope,{maxEvents:32})).rejects.toMatchObject({code:'unsupported_local_source'}) // G already blocks this unproven member.
 expect(f.f.db.legacyNoteHistory!.some((r:any)=>r.record_kind==='resolution')).toBe(true)
 const witness=new BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),before=f.before()
 await expect(witness.inspect(scope)).rejects.toMatchObject({code:'missing_baseline'});expect(f.before()).toEqual(before)
})
it('digest-only negative retains original Legacy proof/wire but cannot stand for the missing encrypted projection',async()=>{
 const f=await setup('keep_both',2),c=f.f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='candidate'&&r.note_id==='baseline-live'&&r.header.revision===2) as any
 const proofs=structuredClone(f.f.db.inbox)
 // NEGATIVE ONLY: simulate missing historical projection. No applied proof is made.
 c.projection=null;c.record_digest=await candidateDigest(c)
 const v=await f.transaction<ResolutionInventorySnapshot>(scope,resolutionInventoryStores,'readonly',(tx,result,abort)=>scheduleResolutionInventory(tx,scope,()=>true,result,abort))
 expect((await authenticateContinuationHistory(scope,v,amk,()=>true)).resolutions.size).toBe(1)
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'missing_baseline'})
 expect(f.f.db.inbox).toEqual(proofs);expect(f.before()).toEqual(before)
})
for(const member of [false,true])it(`retains L valid-AEAD ${member?'membership':'revision'} drift rejection, historical wire/proofs intact`,async()=>{
 const f=await ordinaryBoundaryFixture('keep_both',3,true,false,false,true),witness=new BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 expect(await witness.inspect(scope)).toMatchObject({baselineNotes:4})
 await f.sourceProbe(member);const before=f.before()
 expect(await f.history(false)).toMatchObject({resolutions:1})
 await expect(witness.inspect(scope)).rejects.toMatchObject({code:'source_mismatch'})
 await expect(f.h.history(scope)).rejects.toThrow();await expect(f.g.prepare(scope)).rejects.toThrow();await expect(f.runtime.run(scope)).rejects.toThrow()
 expect(f.before()).toEqual(before)
})
for(const protocol of [2,3] as const)it(`pending protocol${protocol} wire is authenticated without any applied proof or source write`,async()=>{
 const f=await ordinaryBoundaryFixture('keep_both',3,true,false,false,true),incoming=await f.incomingNote(protocol,protocol===3),witness=new BrowserMixedSourceWitness(f.transaction,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device),before=f.before()
 expect(await witness.inspect(scope)).toMatchObject({pendingEvents:1,ordinaryTransitions:0,commitAuthorized:false});expect(f.before()).toEqual(before)
 const row=f.f.db.inbox.find((r:any)=>r.event_id===incoming.event.event_id) as any,wire=JSON.parse(row.wire_item)
 wire.object.ciphertext=(wire.object.ciphertext[0]==='A'?'B':'A')+wire.object.ciphertext.slice(1);row.wire_item=JSON.stringify(wire)
 const changed=f.before();await expect(witness.inspect(scope)).rejects.toThrow();expect(f.before()).toEqual(changed)
})
it('a genuine encrypted received next Resolution is an unsupported generation, not an idle witness success',async()=>{
 const f=await setup(),payload=structuredClone(f.resolution);payload.header.event_id=crypto.randomUUID()
 const peer='44444444-4444-4444-8444-444444444444',frame=frameContentNote({version:1,account_id:scope.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:f.f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:payload}),sequence=f.sequence+1
 const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame)
 try{await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:{event_id:payload.header.event_id,device_id:peer,server_sequence:sequence,project_id:'p',entity_id:'content-note',entity_type:'note',operation:'event',revision:payload.header.revision,updated_at:payload.header.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'unsupported_generation'});expect(f.before()).toEqual(before)
})
it('a canonically readable encrypted pending Map stays an explicit unsupported-family barrier',async()=>{
 const f=await setup(),event=readerCases().find(c=>c.id===9)!.event
 Object.assign(event.header,{account_id:scope.canonicalUserId,device_id:'44444444-4444-4444-8444-444444444444',project_id:'p',event_id:crypto.randomUUID(),bootstrap_id:f.f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id})
 const h=event.header,frame=await frameMapEvent(event),sequence=f.sequence+1,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:h.entity_id,entityType:'map'},frame)
 try{
  await openBrowserCanonicalObject(amk,{accountId:scope.canonicalUserId,projectId:'p',entityId:h.entity_id,entityType:'map',eventId:h.event_id},o)
  await f.f.sync.commitInboundPage(scope,f.sequence,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:{event_id:h.event_id,device_id:h.device_id,server_sequence:sequence,project_id:'p',entity_id:h.entity_id,entity_type:'map',operation:'event',revision:h.revision,updated_at:h.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}],next_cursor:sequence,has_more:false}))
 }finally{frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'unsupported_pending_family'});expect(f.before()).toEqual(before)
})
it('current Note re-encryption with identical canonical plaintext still breaks exact projection identity',async()=>{
 const f=await setup(),row=f.f.db.localNotes!.find((n:any)=>n.note_id==='baseline-live') as any
 const bytes=await openHistoricalJson(scope,'p',row.note_id,'note',row.envelope,amk,()=>true)
 try{const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:row.note_id,entityType:'note'},bytes);try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}}finally{bytes.fill(0)}
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'source_mismatch'});expect(f.before()).toEqual(before)
})
it('invalid authenticated current-source JSON never escapes as a plaintext-bearing parser error',async()=>{
 const f=await setup(),row=f.f.db.localNotes![0] as any,marker='DISPOSABLE_SOURCE_MUST_NOT_ESCAPE',bytes=new TextEncoder().encode('{'+marker)
 const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:row.project_id,entityId:row.note_id,entityType:'note'},bytes)
 try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{bytes.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 const before=f.before(),error=await f.witness.inspect(scope).then(()=>null,e=>e)
 expect(error).toMatchObject({code:'corrupt_record'});expect(error.message).not.toContain(marker);expect(f.before()).toEqual(before)
})
for(const kind of ['F-evidence','F-proof','baseline-proof','H-proof','missing-candidate','missing-row','duplicate-row','unknown-version','bootstrap','role','member','source','unrelated-source'] as const)it(`complete inventory rejects ${kind} without writes`,async()=>{
 const f=await setup(),d=f.f.db
 if(kind==='F-evidence')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='resolution') as any).evidence_envelope.ciphertext='AA'
 if(kind==='F-proof')(d.inbox.find((r:any)=>r.record_version===10) as any).resolution_proof.outcome_digest='0'.repeat(64)
 if(kind==='baseline-proof')(d.inbox.find((r:any)=>JSON.parse(r.wire_item).event.entity_id==='baseline-live') as any).content_note_proof.local_note_digest='0'.repeat(64)
 if(kind==='H-proof')(d.inbox.at(-1) as any).content_note_proof.outcome_digest='0'.repeat(64)
 if(kind==='missing-candidate')d.legacyNoteHistory=d.legacyNoteHistory!.filter((r:any)=>r.event_id!==f.children[0]!.event_id)
 if(kind==='missing-row')d.inbox=d.inbox.filter((r:any)=>r.event_id!==f.children[0]!.event_id)
 if(kind==='duplicate-row')d.inbox.push(structuredClone(d.inbox[0]))
 if(kind==='unknown-version')(d.legacyNoteHistory![0] as any).record_version=99
 if(kind==='bootstrap')(d.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
 if(kind==='role')(d.legacyNoteHistory!.find((r:any)=>r.record_kind==='head'&&r.note_id==='content-note') as any).node_ref={kind:'resolution_result',resolution_event_id:f.r.event_id,result_role:'retained',resolution_digest:'0'.repeat(64)}
 if(kind==='member')d.localNotes=d.localNotes!.filter((n:any)=>n.note_id!=='baseline-deleted')
 if(kind==='source')(d.localNotes![0] as any).source_revision++
 if(kind==='unrelated-source')(d.localProjects!.find((p:any)=>p.project_id==='q') as any).envelope.ciphertext='AA'
 const before=f.before();await expect(f.witness.inspect(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const kind of ['project','note','cursor','dependency','history','unrelated-project'] as const)it(`fresh full-inventory comparison rejects concurrent ${kind} drift`,async()=>{
 const f=await setup();let loads=0
 const tx:BrowserSyncTransaction=(...args)=>{
  if(++loads===2){
   const d=f.f.db
   if(kind==='project')(d.localProjects![0] as any).source_revision++
   if(kind==='note')(d.localNotes![0] as any).source_revision++
   if(kind==='cursor')(d.cursors[0] as any).proven_prefix--
   if(kind==='dependency')(d.ownerHeads![0] as any).tip_event_ids=[crypto.randomUUID()]
   if(kind==='history')(d.legacyNoteHistory![0] as any).record_digest='0'.repeat(64)
   if(kind==='unrelated-project')(d.localProjects!.find((p:any)=>p.project_id==='q') as any).source_revision++
  }
  return f.transaction(...args)
 }
 await expect(f.create(tx).inspect(scope)).rejects.toMatchObject({code:'stale_source'})
 expect(loads).toBe(2)
})
for(const kind of ['key','logout','account','profile','foreign-device-scope'] as const)it(`lifecycle ${kind} invalidation never returns a usable result`,async()=>{
 const f=await setup();let loads=0
 const tx:BrowserSyncTransaction=(...args)=>{
  if(++loads===2){if(kind==='key')f.f.lock();if(kind==='profile')f.revoke();if(kind==='foreign-device-scope')args[0]={...args[0],deviceId:crypto.randomUUID()}}
  return f.transaction(...args)
 }
 if(kind==='logout')await f.f.auth.logout()
 if(kind==='account')await f.f.auth.login('fixture','fixture')
 const before=f.before();await expect(f.create(tx).inspect(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('canonical project-field drift is rejected despite genuine new AEAD',async()=>{
 const f=await setup(),row=f.f.db.localProjects![0] as any,bytes=await openHistoricalJson(scope,'p','p','project_metadata',row.envelope,amk,()=>true)
 let payload:any;try{payload=JSON.parse(new TextDecoder().decode(bytes))}finally{bytes.fill(0)}
 payload.project.name='NEGATIVE_UNPROVEN_PROJECT_CHANGE'
 const raw=new TextEncoder().encode(canonical(payload)),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'p',entityType:'project_metadata'},raw)
 try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
 await expect(f.witness.inspect(scope)).rejects.toMatchObject({code:'source_mismatch'})
})
