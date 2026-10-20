// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {continuationFixture} from './resolutionContinuation.testFixture'
import {BrowserResolutionPrefix,type VerifiedResolutionPrefix} from './resolutionPrefix'
import {scope,amk} from './bootstrap.testFixture'
import {noteProofDigest} from './legacyNoteApply'
import type {BrowserSyncTransaction} from './syncDurability'
import {syncApi} from '@/api/sync'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
afterEach(()=>vi.restoreAllMocks())
async function fixture(...args:Parameters<typeof continuationFixture>){
 const f=await continuationFixture(...args);let active=true
 const create=(transaction:BrowserSyncTransaction=f.f.transaction)=>new BrowserResolutionPrefix(transaction,()=>active).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 return{...f,g:create(),create,close:()=>{active=false;f.close()}}
}
async function result(f:Awaited<ReturnType<typeof fixture>>){return f.g.calculate(await f.g.prepare(scope))}
for(const legacy of [false,true])for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)it(`authentic F protocol${legacy?2:3} ${strategy}, H descendants and historical prefix`,async()=>{
 const f=await fixture(strategy,legacy),before=f.before(),initial=await result(f)
 expect(initial).toMatchObject({current_proven_prefix:0,candidate_proven_prefix:f.sequence,first_blocking_sequence:null,counts:{resolution:1,metadata:1}});expect(f.before()).toEqual(before)
 const first=await f.receive({deleted:strategy==='delete'});await f.runtime.apply(scope,first.sequence)
 let last=first
 if(strategy==='keep_both'){last=await f.receive({id:'retained-note'});await f.runtime.apply(scope,last.sequence)}
 const next=await f.receive({id:last.plaintext.note.id,parent:last.event_id,revision:5,deleted:true});await f.runtime.apply(scope,next.sequence)
 const after=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:next.sequence,counts:{resolution:1},ackAuthorized:false,readOnly:true});expect(f.before()).toEqual(after)
 await expect(f.applier.reconcile(scope,f.sequence)).rejects.toThrow()
 const certificate=await f.g.prepare(scope),commit=await f.g.prepareCommit(certificate)
 expect(await f.g.commit(commit)).toBe('advanced');expect(await f.g.commit(commit)).toBe('already_proven')
 const expected=structuredClone(after);(expected.cursors[0] as any).proven_prefix=next.sequence;expect(f.before()).toEqual(expected)
 await expect(f.g.calculate(certificate)).rejects.toThrow()
 expect(await result(f)).toMatchObject({current_proven_prefix:next.sequence,candidate_proven_prefix:next.sequence})
 expect(await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))).toBe('no_progress')
 await expect(f.f.proven.prepare(scope)).rejects.toThrow()
})
for(const compressed of [false,true])it(`Content Stage/plain ID${compressed?1:0} fresh dependency certificates`,async()=>{
 const f=await fixture('keep_both',false,{stage:true,format:'plain',compressed}),child=await f.receive({compressed});await f.runtime.apply(scope,child.sequence)
 expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,counts:{metadata:1,stage:1,content:4,resolution:1}})
})
for(const count of [3,64])it(`authentic all-${count}-parent DAG and closure qualify once`,async()=>{
 const f=await fixture('choose_version',count===64,undefined,false,count),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,counts:{resolution:1}})
},30000)
it('genuine published frozen Legacy history remains valid after F/H',async()=>{
 const f=await fixture('choose_version',false,undefined,true),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 expect(await f.runtime.history(scope)).toMatchObject({resolutions:1,closedGroups:1})
 expect(await result(f)).toMatchObject({candidate_proven_prefix:3,first_blocking_sequence:4,blocker:'missing_sequence'})
})
it('independent new conflict is authentic but caps its own incoming sequence',async()=>{
 const f=await fixture(),first=await f.receive();await f.runtime.apply(scope,first.sequence)
 const old=f.before().legacyNoteHistory!.filter((r:any)=>r.record_kind==='group'||r.record_kind==='group_transition')
 const fork=await f.receive();await f.runtime.apply(scope,fork.sequence)
 expect(await result(f)).toMatchObject({candidate_proven_prefix:first.sequence,first_blocking_sequence:fork.sequence,blocker:'unproven_family',counts:{resolution:1}})
 expect(f.f.db.legacyNoteHistory.filter((r:any)=>r.record_kind==='group')).toHaveLength(2);expect(f.f.db.legacyNoteHistory).toEqual(expect.arrayContaining(old))
 const before=f.before();await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))
 const after=structuredClone(before);(after.cursors[0] as any).proven_prefix=first.sequence;expect(f.before()).toEqual(after)
})
it('unsupported tombstone resurrection remains received and unqualified',async()=>{
 const f=await fixture('delete'),child=await f.receive({deleted:true});await f.runtime.apply(scope,child.sequence)
 const unsupported=await f.receive({parent:child.event_id,revision:5}),before=f.before();await expect(f.runtime.apply(scope,unsupported.sequence)).rejects.toThrow()
 expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,first_blocking_sequence:unsupported.sequence});expect(f.before()).toEqual(before)
})
for(const mutate of ['digest','AEAD','closure','duplicate_transition','original_anchor','retained_anchor','clone_genesis','descendant','source','project','bootstrap','old_proof','unknown','duplicate_event','duplicate_sequence','own_resolution','missing_publication','metadata','stage'] as const)it(`no certificate from ${mutate}`,async()=>{
 const f=await fixture('keep_both',false,mutate==='stage'?{stage:true}:undefined),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 const d=f.f.db,h=d.legacyNoteHistory,r=h.find((r:any)=>r.record_kind==='resolution'),t=h.find((r:any)=>r.record_kind==='group_transition')
 if(mutate==='digest')r.payload_digest='0'.repeat(64)
 if(mutate==='AEAD')r.evidence_envelope.ciphertext=(r.evidence_envelope.ciphertext[0]==='A'?'B':'A')+r.evidence_envelope.ciphertext.slice(1)
 if(mutate==='closure'){t.resolution_digest='0'.repeat(64);const {record_digest:_d,...body}=t;t.record_digest=await noteProofDigest(body)}
 if(mutate==='duplicate_transition')h.push(structuredClone(t))
 if(mutate==='original_anchor'||mutate==='retained_anchor')d.legacyNoteHistory=h.filter((a:any)=>!(a.record_kind==='head'&&a.note_id===(mutate==='original_anchor'?'content-note':'retained-note')))
 if(mutate==='clone_genesis'){const c=structuredClone(h.find((r:any)=>r.event_id===child.event_id));c.note_id='retained-note';c.record_id=c.event_id=crypto.randomUUID();c.header={...c.header,event_id:c.event_id,parent_event_id:null,revision:1};h.push(c)}
 if(mutate==='descendant')d.legacyNoteHistory=h.filter((r:any)=>r.event_id!==child.event_id)
 if(mutate==='source')d.localNotes[0].envelope.ciphertext='AA'
 if(mutate==='project')d.localProjects[0].source_revision++
 if(mutate==='bootstrap')d.projectBindings[0].bootstrap_id=crypto.randomUUID()
 if(mutate==='old_proof')(d.inbox.find((r:any)=>r.state==='content_note_proven') as any).content_note_proof.outcome_digest='0'.repeat(64)
 if(mutate==='unknown')h.push({...t,record_version:99})
 if(mutate==='duplicate_event')d.inbox.push({...d.inbox.at(-1),server_sequence:(d.cursors[0] as any).pull_cursor+1})
 if(mutate==='duplicate_sequence')d.inbox.push({...d.inbox.at(-1),event_id:crypto.randomUUID()})
 if(mutate==='own_resolution'){r.source_device_id=scope.deviceId;const wire=JSON.parse(r.wire_item);wire.event.device_id=scope.deviceId;r.wire_item=JSON.stringify(wire)}
 if(mutate==='missing_publication')d.inbox=d.inbox.filter((r:any)=>r.event_id!==f.parents[1]!.event_id)
 if(mutate==='metadata'||mutate==='stage')d.ownerHeads=d.ownerHeads!.filter((r:any)=>r.owner_kind!==(mutate==='stage'?'stage':'project_metadata'))
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const key of ['accountId','canonicalUserId','deviceId'] as const)it(`wrong ${key} never mints certificate`,async()=>{
 const f=await fixture(),before=f.before();await expect(f.g.prepare({...scope,[key]:crypto.randomUUID()})).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const kind of ['key','logout','profile','epoch'] as const)it(`certificate/commit lifecycle ${kind}`,async()=>{
 const f=await fixture(),certificate=await f.g.prepare(scope),commit=await f.g.prepareCommit(certificate)
 if(kind==='key')f.f.lock();else if(kind==='profile')f.close();else if(kind==='epoch')await f.f.auth.login('fixture','fixture');else await f.f.auth.logout()
 const before=f.before();await expect(f.g.calculate(certificate)).rejects.toThrow();await expect(f.g.prepareCommit(certificate)).rejects.toThrow();await expect(f.g.commit(commit)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const part of ['source','history','dependency','cursor','wire','binding','outbox'] as const)it(`full inventory CAS ${part}`,async()=>{
 const f=await fixture(),certificate=await f.g.prepare(scope),commit=await f.g.prepareCommit(certificate),d=f.f.db
 if(part==='source')d.localNotes[0].source_revision++
 if(part==='history')d.legacyNoteHistory.find((r:any)=>r.record_kind==='head').head_revision++
 if(part==='dependency')d.ownerHeads![0].head_revision++
 if(part==='cursor')(d.cursors[0] as any).next_local_ordinal++
 if(part==='wire')(d.inbox.at(-1) as any).wire_item+=' '
 if(part==='binding')d.projectBindings[0].remote_high_water++
 if(part==='outbox')d.outbox.push({account_id:scope.accountId,event_id:crypto.randomUUID()})
 const before=f.before();await expect(f.g.calculate(certificate)).rejects.toThrow();await expect(f.g.commit(commit)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('forged/cross-runtime capabilities and public diagnostics cannot authorize prefix',async()=>{
 const f=await fixture(),token=await f.g.prepare(scope),commit=await f.g.prepareCommit(token),other=f.create(),diagnostic=await f.runtime.history(scope),before=f.before()
 for(const fake of [{},diagnostic,await f.g.calculate(token)]){await expect(f.g.calculate(fake as VerifiedResolutionPrefix)).rejects.toThrow();await expect(f.g.commit(fake as never)).rejects.toThrow()}
 expect('certificate'in f.g).toBe(false)
 await expect(other.calculate(token)).rejects.toThrow();await expect(other.commit(commit)).rejects.toThrow();expect(f.before()).toEqual(before)
})
for(const kind of ['put','complete','key','logout','profile'] as const)it(`cursor-only atomic rollback ${kind}`,async()=>{
 const f=await fixture();let armed=false
 const transaction:BrowserSyncTransaction=(s,stores,mode,schedule)=>f.f.transaction(s,stores,mode,(tx:IDBTransaction,result:(r:any)=>void,abort:(e:unknown)=>void)=>{
  const proxy=new Proxy(tx,{get:(tx,key)=>key==='objectStore'?(name:string)=>{
   const store=tx.objectStore(name);return new Proxy(store,{get:(store,key)=>{
    const method=Reflect.get(store,key)
    if(key==='put'&&mode==='readwrite')return(...args:any[])=>{
     expect(name).toBe('cursors');const r=method.apply(store,args)
     if(armed){if(kind==='put')throw new DOMException('injected','QuotaExceededError');else if(kind==='key')f.f.lock();else if(kind==='logout')void f.f.auth.logout();else if(kind==='profile')f.close()}
     return r
    }
    return typeof method==='function'?method.bind(store):method
   }})
  }:Reflect.get(tx,key)})
  schedule(proxy,result,abort)
 })
 const g=f.create(transaction),commit=await g.prepareCommit(await g.prepare(scope)),before=f.before();armed=true;if(kind==='complete')f.f.abort()
 await expect(g.commit(commit)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('missing sequence after Resolution caps candidate; corruption inside prefix fails without reset',async()=>{
 const f=await fixture(),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 const gap=await f.receive({parent:child.event_id,revision:5});f.f.db.inbox.pop()
 expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,first_blocking_sequence:gap.sequence,blocker:'missing_sequence'})
 await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))
 ;(f.f.db.cursors[0] as any).proven_prefix=gap.sequence
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('missing Metadata sequence before Resolution cannot be skipped',async()=>{
 const f=await fixture('choose_version',true);f.f.db.inbox=f.f.db.inbox.filter((r:any)=>r.server_sequence!==1)
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:0,first_blocking_sequence:1,blocker:'missing_sequence'});expect(f.before()).toEqual(before)
})
it('received Resolution is a barrier, never applied authority from retention',async()=>{
 const f=await fixture(),row=structuredClone(f.f.db.inbox.find((r:any)=>r.record_version===10)) as any
 row.event_id=crypto.randomUUID();row.server_sequence++;row.record_version=1;row.state='received';delete row.resolution_proof
 const wire=JSON.parse(row.wire_item);wire.event.event_id=row.event_id;wire.event.server_sequence=row.server_sequence;row.wire_item=JSON.stringify(wire)
 f.f.db.inbox.push(row);(f.f.db.cursors[0] as any).pull_cursor=row.server_sequence
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:row.server_sequence});expect(f.before()).toEqual(before)
})
it('no G ACK/HTTP entry, old ACK cannot consume new tokens',async()=>{
 const f=await fixture(),acks=[vi.spyOn(syncApi,'ack'),vi.spyOn(encryptedSyncV2Api,'ack'),vi.spyOn(encryptedSyncV3Api,'ack')]
 const token=await f.g.prepare(scope);await f.g.commit(await f.g.prepareCommit(token))
 expect('prepareAck'in f.g).toBe(false);expect('ackOnce'in f.g).toBe(false)
 await expect(f.f.proven.ackOnce(token as never)).rejects.toThrow();for(const ack of acks)expect(ack).not.toHaveBeenCalled();expect((f.f.db.cursors[0] as any).ack_cursor).toBe(0)
})
it('wrong AMK cannot authenticate an exact outer inventory',async()=>{
 const f=await fixture(),copy=amk.slice();try{amk.fill(0);await expect(f.g.prepare(scope)).rejects.toThrow()}finally{amk.set(copy);copy.fill(0)}
})
for(const route of [{stage:true,order:true,mixedInventory:true},{stage:false,mixed:true}])it(`mixed actual family producers ${JSON.stringify(route)}`,async()=>{
 const f=await fixture('choose_version',false,route),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 expect(await result(f)).toMatchObject({candidate_proven_prefix:child.sequence,first_blocking_sequence:null,counts:{metadata:1,resolution:1,...(route.order?{stage:1,stage_order:1,legacy:1}:{legacy:1,content:3})}})
})
it('incomplete StageOrder proof is unqualified, never skipped',async()=>{
 const f=await fixture('choose_version',false,{stage:true,order:true})
 f.f.db.ownerHeads=f.f.db.ownerHeads!.filter((r:any)=>r.owner_kind!=='stage_order')
 const before=f.before(),r=await result(f)
 expect(r).toMatchObject({candidate_proven_prefix:5,first_blocking_sequence:6,blocker:'unproven_family'});expect(f.before()).toEqual(before)
})
it('received unsupported family blocks at its exact sequence',async()=>{
 const f=await fixture(),child=await f.receive(),row=f.f.db.inbox.at(-1) as any,wire=JSON.parse(row.wire_item)
 wire.event.entity_type='document';row.wire_item=JSON.stringify(wire)
 const before=f.before();expect(await result(f)).toMatchObject({candidate_proven_prefix:f.sequence,first_blocking_sequence:child.sequence});expect(f.before()).toEqual(before)
})
it('new H receipt/apply after local prefix keeps bounded durable invariants',async()=>{
 const f=await fixture();await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)))
 const child=await f.receive();expect(await result(f)).toMatchObject({current_proven_prefix:f.sequence,candidate_proven_prefix:f.sequence,first_blocking_sequence:child.sequence})
 await f.runtime.apply(scope,child.sequence);expect(await result(f)).toMatchObject({current_proven_prefix:f.sequence,candidate_proven_prefix:child.sequence})
 await f.g.commit(await f.g.prepareCommit(await f.g.prepare(scope)));expect((f.f.db.cursors[0] as any).proven_prefix).toBe(child.sequence)
})
it('validly encrypted unexplained source change cannot replace the protected source chain',async()=>{
 const {openHistoricalJson}=await import('./resolutionHistorical'),{encryptObjectBytes}=await import('@/crypto'),{encodeBase64Url}=await import('@/api/base64url'),{canonical}=await import('@/cloud/projectMetadataCodec')
 const f=await fixture(),child=await f.receive();await f.runtime.apply(scope,child.sequence)
 const row=f.f.db.localNotes.find((r:any)=>r.note_id==='content-note'),bytes=await openHistoricalJson(scope,'p',row.note_id,'note',row.envelope,amk,()=>true)
 let raw:Uint8Array|undefined
 try{const payload=JSON.parse(new TextDecoder().decode(bytes));payload.source.note.content='AUTHENTIC_ENCRYPTION_WITHOUT_PROTECTED_HISTORY';raw=new TextEncoder().encode(canonical(payload));const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:row.note_id,entityType:'note'},raw)
  try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}
 }finally{bytes.fill(0);raw?.fill(0)}
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('unqualified genuine C3/P2 fixture is never borrowed as a Resolution author or family grant',async()=>{
 const {contentAuthorityFixture}=await import('./contentAuthority.testFixture'),own=await contentAuthorityFixture(),f=await fixture()
 // Negative-only graft: exact genuine own AEAD specimen has no accepted author
 // relationship to this F/H inventory. No positive IDB proof is manufactured.
 f.f.db.inbox.push(own.row)
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('pending genuine I2 does not authorize new prefix',async()=>{
 const {contentAuthorityFixture}=await import('./contentAuthority.testFixture'),own=await contentAuthorityFixture(false,'intent'),f=await fixture()
 f.f.db.legacyNoteIntents.push(own.intent)
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
it('unexplained change to an additional project member cannot borrow the Resolution certificate',async()=>{
 const f=await fixture('choose_version',false,{stage:true,order:true,mixedInventory:true})
 const row=f.f.db.localNotes.find((r:any)=>r.note_id==='remote-note')
 const {openHistoricalJson}=await import('./resolutionHistorical'),{encryptObjectBytes}=await import('@/crypto'),{encodeBase64Url}=await import('@/api/base64url'),{canonical}=await import('@/cloud/projectMetadataCodec')
 const bytes=await openHistoricalJson(scope,'p',row.note_id,'note',row.envelope,amk,()=>true)
 let raw:Uint8Array|undefined
 try{const payload=JSON.parse(new TextDecoder().decode(bytes));payload.source.note.content='UNEXPLAINED_ADDITIONAL_MEMBER';raw=new TextEncoder().encode(canonical(payload));const o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:row.note_id,entityType:'note'},raw)
  try{row.envelope={crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}
 }finally{bytes.fill(0);raw?.fill(0)}
 expect(await f.runtime.history(scope)).toMatchObject({resolutions:1}) // H original/retained authority remains unchanged.
 const before=f.before();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(before)
})
