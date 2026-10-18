// @vitest-environment node
import {it,expect,vi} from 'vitest'
import {contentWriterSetup,sourceToken,fresh,update,scope,at} from './contentNoteIntents.testFixture'
import {BrowserLocalAuthority} from './localAuthority'
import {BrowserContentNoteIntents} from './contentNoteIntents'
import {BrowserPersistenceError} from './persistence'
import type {BrowserSyncTransaction} from './syncDurability'
import {contentRow} from './noteTransport.testFixture'
import {contentAuthorityFixture} from './contentAuthority.testFixture'
it.each([1,2,3,4])('write boundary %s failure rolls back I2/cursor/project/Note together',async boundary=>{
 const f=await contentWriterSetup();let count=0
 const tx:BrowserSyncTransaction=(s,stores,mode,schedule)=>f.transaction(s,stores,mode,(original,result,abort)=>{
  const proxy=new Proxy(original,{get(target,key){
   if(key!=='objectStore')return Reflect.get(target,key)
   return(name:string)=>new Proxy(target.objectStore(name),{get(store,method){
    if(method==='put'||method==='add')return(...args:unknown[])=>{
     const request=(store[method] as Function).apply(store,args)
     if(mode==='readwrite'&&++count===boundary)abort(new BrowserPersistenceError('storage_failed'))
     return request
    }
    const value=Reflect.get(store,method);return typeof value==='function'?value.bind(store):value
   }})
  }})
  schedule(proxy,result,abort)
 })
 const source=new BrowserLocalAuthority(tx),cw=new BrowserContentNoteIntents(tx,source,()=>true).bind(f.auth,f.bindings as never,f.keys as never),old=structuredClone(f.db)
 await expect(cw.local.createNote(scope,(await cw.local.readSnapshot(scope,'p')).token,fresh())).rejects.toThrow();expect(f.db).toEqual(old);expect(count).toBeGreaterThanOrEqual(boundary)
})
it.each(['source','membership','head','inbox','binding','metadata','cursor','outbox','intent','lock','logout','session','close'])('changed %s after prepare rejects the whole commit',async kind=>{
 const f=await contentWriterSetup(true);if(kind==='intent')await update(f)
 const prepare=f.cw.prepareMutation.bind(f.cw);let after:unknown
 vi.spyOn(f.cw,'prepareMutation').mockImplementation(async(...args)=>{
  const plan=await prepare(...args)
  if(kind==='source')(f.db.localNotes![0] as any).source_revision++
  if(kind==='membership')(f.db.localProjects![0] as any).source_revision++
  if(kind==='head')(f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='head') as any).head_revision++
  if(kind==='inbox')(f.db.inbox[1] as any).state='received'
  if(kind==='binding')(f.db.projectBindings[0] as any).bootstrap_id=crypto.randomUUID()
  if(kind==='metadata')(f.db.ownerHeads![0] as any).head_revision++
  if(kind==='cursor')(f.db.cursors[0] as any).next_local_ordinal++
  if(kind==='outbox')f.db.outbox.push({account_id:scope.accountId,unexpected:true})
  if(kind==='intent')(f.db.legacyNoteIntents![0] as any).mutation_generation++
  if(kind==='lock')f.lock();if(kind==='logout')await f.auth.logout();if(kind==='session')f.invalidate();if(kind==='close')f.close()
  after=structuredClone(f.db);return plan
 })
 await expect(update(f)).rejects.toThrow();expect(f.db).toEqual(after)
})
it.each(['snapshot_digest','intent_envelope','generation','bootstrap','dependency','operation','ordinal','event'])('tampered prior I2 %s cannot coalesce',async kind=>{
 const f=await contentWriterSetup(true);await update(f);const i=f.db.legacyNoteIntents![0] as any
 if(kind==='snapshot_digest')i.snapshot_digest='0'.repeat(64)
 if(kind==='intent_envelope')i.intent_envelope.ciphertext=(i.intent_envelope.ciphertext[0]==='A'?'B':'A')+i.intent_envelope.ciphertext.slice(1)
 if(kind==='generation')i.mutation_generation++
 if(kind==='bootstrap'){i.bootstrap_id=crypto.randomUUID();i.dependencies.bootstrap_id=i.bootstrap_id}
 if(kind==='dependency')i.dependencies.metadata_event_id=crypto.randomUUID()
 if(kind==='operation'){i.operation='delete';i.deleted_at=at}
 if(kind==='ordinal')i.local_ordinal++
 if(kind==='event')i.event_id=crypto.randomUUID()
 const old=structuredClone(f.db);await expect(update(f)).rejects.toThrow();expect(f.db).toEqual(old)
})
it.each(['missing-metadata','forged-dependency','bad-AEAD','wrong-source','wrong-membership','upload-existing','duplicate-ordinal'])('%s cannot mint first Content ownership',async kind=>{
 const f=await contentWriterSetup(true)
 if(kind==='missing-metadata')f.db.ownerHeads=[]
 if(kind==='forged-dependency'){const h=f.db.ownerHeads![0] as any;h.history[0].event_id=crypto.randomUUID();h.tip_event_ids=[h.history[0].event_id]}
 if(kind==='bad-AEAD'){const row=f.db.inbox[0] as any,w=JSON.parse(row.wire_item);w.object.ciphertext=(w.object.ciphertext[0]==='A'?'B':'A')+w.object.ciphertext.slice(1);row.wire_item=JSON.stringify(w)}
 if(kind==='wrong-source')await f.local.updateNote(scope,await sourceToken(f),'content-note',{content:'PRIVATE_UNBOUND_EDIT'},at)
 if(kind==='wrong-membership')(f.db.localNotes![0] as any).source_revision++
 if(kind==='upload-existing'){const b=f.db.projectBindings[0] as any;b.mode='upload_existing';b.phase='completing';b.initial_max_server_sequence=0}
 if(kind==='duplicate-ordinal'){await f.writer.local.createNote(scope,await sourceToken(f),fresh('legacy'));(f.db.cursors[0] as any).next_local_ordinal=1}
 const old=structuredClone(f.db);await expect(update(f)).rejects.toThrow();expect(f.db).toEqual(old)
})
it('peer input appearing after prepare is retained and invalidates the prepared source/I2 plan',async()=>{
 const f=await contentWriterSetup(true),prepare=f.cw.prepareMutation.bind(f.cw);let after:unknown
 vi.spyOn(f.cw,'prepareMutation').mockImplementation(async(...args)=>{const plan=await prepare(...args);await contentRow(f,3,{mutation:'update',parent:crypto.randomUUID()});after=structuredClone(f.db);return plan})
 await expect(update(f)).rejects.toThrow();expect(f.db).toEqual(after);expect(f.db.inbox).toHaveLength(3)
})
it('C3 sealed ownership cannot be coalesced or diverted through source-only/Legacy writes',async()=>{
 const f=await contentAuthorityFixture(false,'sealed'),cw=new BrowserContentNoteIntents(f.transaction,f.localOwner,()=>true).bind(f.auth,f.bindings as never,f.keys as never),old=structuredClone(f.db)
 await expect(cw.local.updateNote(scope,await sourceToken(f),'content-note',{content:'BAD'},at)).rejects.toThrow();await expect(f.local.updateNote(scope,await sourceToken(f),'content-note',{content:'BAD'},at)).rejects.toThrow();expect(f.db).toEqual(old)
})
it('I2 mutation performs no HTTP and leaves history/inbox/outbox/receipts/prefix unchanged',async()=>{
 const f=await contentWriterSetup(true),old=structuredClone(f.db),network=vi.spyOn(globalThis,'fetch');await update(f)
 expect(network).not.toHaveBeenCalled();for(const name of ['legacyNoteHistory','inbox','outbox','receipts','ownerHeads','projectBindings'])expect(f.db[name]).toEqual(old[name]);expect((f.db.cursors[0] as any).proven_prefix).toBe((old.cursors[0] as any).proven_prefix);vi.restoreAllMocks()
})
it('recomputed Metadata checksum under an already proven prefix cannot replace current-key AEAD authentication',async()=>{
 const f=await contentWriterSetup(true);await f.proven.advance(scope)
 const row=f.db.inbox[0] as any,wire=JSON.parse(row.wire_item);wire.object.ciphertext=(wire.object.ciphertext[0]==='A'?'B':'A')+wire.object.ciphertext.slice(1);row.wire_item=JSON.stringify(wire)
 const {noteProofDigest}=await import('./legacyNoteApply'),digest=await noteProofDigest({protocol_version:row.protocol_version,event:wire.event,object:wire.object});row.applied_proof.wire_digest=digest
 const head=f.db.ownerHeads![0] as any;head.history.find((p:any)=>p.event_id===row.event_id).wire_digest=digest
 const old=structuredClone(f.db);await expect(update(f)).rejects.toThrow();expect(f.db).toEqual(old)
})
