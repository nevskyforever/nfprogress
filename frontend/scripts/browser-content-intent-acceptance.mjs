import assert from 'node:assert/strict'
import {chromium} from '@playwright/test'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
/** Real dormant producer, real normal-user key/identity runtime, native IDB/locks. */
export async function acceptContentAtomicIntents({origin,cases,mixedPage,mixedScope,captureV9Profile}){
 if(mixedPage){
  await mixedPage.evaluate(async scope=>{
   await meta.keys.dispose();await session.close();globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope)
   const before={};for(const name of ['localProjects','localNotes','legacyNoteIntents','legacyNoteHistory','outbox','receipts','inbox','cursors','ownerHeads','projectBindings'])before[name]=await nativeRows(name)
   if(!before.legacyNoteHistory.some(h=>h.record_kind==='group'&&h.note_id==='pending-legacy-content'))throw Error('mixed_fixture_missing')
   const writer=c21.contentIntentFixture(session,meta),token=(await writer.local.readSnapshot(scope,'stage-order-project')).token
   let rejected=false;try{await writer.local.updateNote(scope,token,'pending-legacy-content',{content:'PRIVATE_BLOCKED_CONTENT'},'2026-10-19T00:00:00.000000Z')}catch{rejected=true}
   if(!rejected)throw Error('mixed_writer_activated')
   for(const name of Object.keys(before))if(JSON.stringify(await nativeRows(name))!==JSON.stringify(before[name]))throw Error('mixed_changed_'+name)
  },mixedScope)
  cases.push('C21.2.07 native existing mixed group1 blocks explicit Content handover with every source/history/intent/transport byte unchanged')
 }
 const directory=await mkdtemp(join(tmpdir(),'c21-content-intent-')),errors=[],requests=[];let context,page,scope
 const launch=async()=>{context=await chromium.launchPersistentContext(directory,{headless:true});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))requests.push(r.url())});await page.goto(`${origin}/scripts/browser-persistence-harness.html`)}
 const bind=()=>page.evaluate(async scope=>{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope);globalThis.cw=c21.contentIntentFixture(session,meta);globalThis.local=cw.local;globalThis.s=scope;globalThis.stamp='2026-10-19T00:00:00.000000Z';globalThis.token=async()=>(await local.readSnapshot(s,'atomic-project')).token;globalThis.fresh=id=>({id,project_id:'atomic-project',stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'PRIVATE_CONTENT_ATOMIC_TITLE',content:'PRIVATE_CONTENT_ATOMIC_BODY',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{},revision:0})},scope)
 const snapshot=()=>page.evaluate(async()=>{const names=['identities','accountBindings','localProjects','localNotes','legacyNoteIntents','legacyNoteHistory','outbox','receipts','inbox','cursors','ownerHeads','projectBindings'],v={};for(const name of names)v[name]=await nativeRows(name);return v})
 const inspect=()=>page.evaluate(async()=>({intents:await cw.list(s,'atomic-project'),cursor:await session.sync.readCheckpoint(s),prefix:(await session.proven.bind(meta.auth,meta.bindings,meta.keys).calculate(s)).candidate_proven_prefix}))
 try{
  await launch()
  scope=await page.evaluate(async()=>{const user=crypto.randomUUID();globalThis.session=await c21.openBrowserPersistence(user);const i=await session.read(user);await session.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
  await bind()
  const competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
  assert.equal(await competing.evaluate(async scope=>{try{await c21.openBrowserPersistence(scope.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close()
  await page.evaluate(async()=>{
   await local.initializeProject(s,{project:{id:'atomic-project',name:'PRIVATE_CONTENT_ATOMIC_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
   const b=await session.projects.importRemote(s,{project_id:'atomic-project',bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0}),peer=crypto.randomUUID(),eventId=crypto.randomUUID()
   const event={version:1,header:{account_id:s.canonicalUserId,bootstrap_id:b.bootstrap_id,device_id:peer,entity_id:b.project_id,event_id:eventId,generation:1,operation:'create',parent_event_ids:[],project_id:b.project_id,revision:1,updated_at:stamp},metadata:{name:'PRIVATE_METADATA',goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
   const ref={event_id:eventId,device_id:peer,server_sequence:1,project_id:b.project_id,entity_id:b.project_id,entity_type:'project_metadata',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null},item=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const bytes=c21.frameProjectMetadata(event);let o;try{o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:b.project_id,entityId:b.project_id,entityType:'project_metadata'},bytes);return{event:ref,object:{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}}finally{bytes.fill(0);o?.nonce.fill(0);o?.ciphertext.fill(0)}})
   await session.sync.commitInboundPage(s,0,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[item],next_cursor:1,has_more:false}));await session.metadata.apply(s,ref,meta.auth,meta.bindings,meta.keys);await session.proven.bind(meta.auth,meta.bindings,meta.keys).advance(s)
  })
  for(const name of ['legacyNoteIntents','cursors','localProjects','localNotes']){
   const before=await snapshot()
   assert.equal(await page.evaluate(async name=>{const originals={add:IDBObjectStore.prototype.add,put:IDBObjectStore.prototype.put};for(const method of ['add','put'])IDBObjectStore.prototype[method]=function(...args){const r=originals[method].apply(this,args);if(this.name===name)r.addEventListener('success',()=>this.transaction.abort(),{once:true});return r};try{await local.createNote(s,await token(),fresh('abort-'+name));return false}catch{return true}finally{Object.assign(IDBObjectStore.prototype,originals)}},name),true)
   assert.deepEqual(await snapshot(),before)
  }
  cases.push('C21.2.07 native abort after I2/cursor/project/Note write rolls back all four effects; no ordinal gaps')
  await page.evaluate(async()=>local.createNote(s,await token(),fresh('content-a')))
  const first=await inspect();assert.equal(first.intents.length,1);assert.equal(first.intents[0].local_ordinal,1);assert.equal(first.intents[0].mutation_generation,1);assert.equal(first.intents[0].parent_event_id,null);assert.equal(first.intents[0].revision,1);assert.equal(first.prefix,1)
  const committed=await snapshot();assert.deepEqual(committed.localNotes[0],first.intents[0].snapshot);assert.equal(JSON.stringify(committed).includes('PRIVATE_CONTENT_ATOMIC'),false)
  await page.reload();await bind();assert.deepEqual(await snapshot(),committed);assert.deepEqual(await inspect(),first)
  await context.close();await launch();await bind();assert.deepEqual(await snapshot(),committed);assert.deepEqual(await inspect(),first)
  await page.evaluate(async()=>local.updateNote(s,await token(),'content-a',{content:'PRIVATE_CONTENT_ATOMIC_SECOND'},stamp))
  const coalesced=await inspect(),a=coalesced.intents[0],old=first.intents[0]
  assert.deepEqual([a.event_id,a.local_ordinal,a.parent_event_id,a.revision],[old.event_id,old.local_ordinal,old.parent_event_id,old.revision]);assert.equal(a.mutation_generation,2);assert.equal(coalesced.cursor.next_local_ordinal,2);assert.equal(a.snapshot.note_revision,1)
  const beforeRejected=await snapshot()
  for(const kind of ['legacy','source-only','delete','seal'])assert.equal(await page.evaluate(async kind=>{try{if(kind==='legacy')await session.noteIntents.bind(meta.auth,meta.bindings,meta.keys).local.updateNote(s,await token(),'content-a',{content:'BAD'},stamp);if(kind==='source-only')await session.localSource.bind(meta.auth,meta.bindings,meta.keys).updateNote(s,await token(),'content-a',{content:'BAD'},stamp);if(kind==='delete')await local.tombstoneNote(s,await token(),'content-a',stamp);if(kind==='seal')await session.noteIntents.bind(meta.auth,meta.bindings,meta.keys).seal(s,'atomic-project',(await cw.list(s,'atomic-project'))[0].event_id);return false}catch{return true}},kind),true)
  assert.deepEqual(await snapshot(),beforeRejected)
  for(const kind of ['key','logout']){
   const before=await snapshot()
   assert.equal(await page.evaluate(async kind=>{const prepare=cw.prepareMutation.bind(cw);cw.prepareMutation=async(...args)=>{const p=await prepare(...args);globalThis.invalidationFlight=kind==='key'?meta.keys.lock():meta.auth.logout();return p};try{await local.updateNote(s,await token(),'content-a',{content:'BAD'},stamp);return false}catch{return true}},kind),true)
   assert.deepEqual(await snapshot(),before);await page.evaluate(async()=>{await globalThis.invalidationFlight;await meta.keys.dispose();globalThis.meta=await c21.metadataFixture(session,s);globalThis.cw=c21.contentIntentFixture(session,meta);globalThis.local=cw.local})
  }
  await page.evaluate(async()=>{await session.noteIntents.bind(meta.auth,meta.bindings,meta.keys).local.createNote(s,await token(),fresh('legacy-b'));await local.createNote(s,await token(),fresh('content-c'))})
  const final=await snapshot(),state=await inspect();assert.deepEqual([...final.legacyNoteIntents].sort((a,b)=>a.local_ordinal-b.local_ordinal).map(i=>[i.note_id,i.record_version,i.local_ordinal]),[['content-a',2,1],['legacy-b',1,2],['content-c',2,3]]);assert.equal(state.cursor.next_local_ordinal,4);assert.equal(state.cursor.proven_prefix,1);assert.equal(state.cursor.ack_cursor,0)
  assert.deepEqual(final.outbox,[]);assert.deepEqual(final.receipts,[]);assert.deepEqual(final.legacyNoteHistory,[]);assert.equal(final.inbox.some(r=>r.record_version===9),false)
  // A genuine incoming peer head can hand over explicitly; its historical proof
  // still replays after the local I2 changes the canonical source.
  await page.evaluate(async()=>{
   const note=fresh('peer-head');delete note.revision
   const head=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'),b=(await nativeRows('projectBindings'))[0],id=crypto.randomUUID(),peer=crypto.randomUUID()
   const header={event_id:id,project_id:'atomic-project',entity_id:'peer-head',entity_type:'note',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null},plain=c21.createNoteSyncPlaintext(header,null,note).plaintext
   const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:head.tip_event_ids[0],stage_event_ids:[]},event:plain}
   const item=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const bytes=c21.readerFrame({id:8,version:1,event:wrapper},false);let o;try{o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:'atomic-project',entityId:'peer-head',entityType:'note'},bytes);return{event:{...header,operation:'event',device_id:peer,server_sequence:2},object:{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}}finally{bytes.fill(0);o?.nonce.fill(0);o?.ciphertext.fill(0)}})
   await session.sync.commitInboundPage(s,1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[item],next_cursor:2,has_more:false}));await session.contentNotes.bind(meta.auth,meta.bindings,meta.keys).apply(s,2)
   await local.updateNote(s,await token(),'peer-head',{content:'PRIVATE_CONTENT_ATOMIC_HANDOVER'},stamp)
   const intent=(await cw.list(s,'atomic-project')).find(i=>i.note_id==='peer-head')
   if(intent.parent_event_id!==id||intent.revision!==2||intent.local_ordinal!==4)throw Error('handover_identity')
  })
  const retained=await snapshot(),afterPeer=await inspect()
  assert.equal(await page.evaluate(()=>session.contentNotes.bind(meta.auth,meta.bindings,meta.keys).apply(s,2)),'already_applied');assert.deepEqual(await snapshot(),retained)
  assert.equal(afterPeer.cursor.proven_prefix,1);assert.equal(afterPeer.cursor.ack_cursor,0);assert.equal(afterPeer.prefix,2);assert.equal(retained.legacyNoteHistory.some(h=>h.record_kind==='candidate'&&h.record_version===3),false)
  await context.close();await launch();await bind();assert.deepEqual(await snapshot(),retained);assert.deepEqual(await inspect(),afterPeer)
  cases.push('C21.2.07 native genuine peer Content head explicitly hands over to I2; historical proof replays without source/intent/head writes, pending I2 adds no prefix/ACK qualification')
  captureV9Profile?.({phase:"intent",scope,snapshot:retained})
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[])
  cases.push('C21.2.07 genuine dormant producer creates encrypted canonical Note/membership + authenticated I2; renderer and disk restart preserve exact bytes and event/ordinal/parent')
  cases.push('C21.2.07 compatible edit after disk reopen coalesces same event/ordinal into generation2; source-only/Legacy fallback, pending delete and Legacy seal rejected atomically')
  cases.push('C21.2.07 auth/key invalidation after crypto prepare aborts without source/I2 changes; independent Content and Legacy Notes share dense ordinals across disk restart')
  cases.push('C21.2.07 native source+I2 only: no C3/outbox/R2/P2/inbox9, no new prefix/ACK qualification, HTTP0, page errors0; production composition remains dormant')
 }finally{if(context)await context.close();await rm(directory,{recursive:true,force:true})}
}
