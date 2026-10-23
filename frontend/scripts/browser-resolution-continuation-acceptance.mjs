import assert from 'node:assert/strict'
import {mkdtemp,rm,cp,readFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
import {pathToFileURL} from 'node:url'
// G reuses this exact genuine F -> transport -> H producer/restart acceptance.
// The standalone H entry still executes every existing assertion unchanged.
export async function runResolutionContinuationAcceptance(onHistorical){
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const legacy3=process.argv.includes('--legacy3'),oldBundle=process.env.C21_OLD_T_BUNDLE
if(legacy3){assert.equal(onHistorical,undefined);assert.ok(oldBundle);assert.equal((await readFile(join(oldBundle,'baseline.sha'),'utf8')).trim(),'a5c83fadd04be6db7b45e6e5eb5854b922a38e76')}
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const errors=[],network=[];let context,page,scope,decisions,registrations=0,faults=0,applied=0,continuations=0,continuationFaults=0,historicalReopens=0,oldReaders=0,uncertain=0,preparedProcessStops=0,hCAS=0,forkFaults=0
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
for(const protocol of [2,3])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
 const testCase={protocol:legacy3?2:protocol,childProtocol:protocol,strategy,legacy3},directory=await mkdtemp(join(tmpdir(),'c21-resolution-apply-'))
 let activeDirectory=directory,old=false,copy
 const launch=async()=>{
  context=await chromium.launchPersistentContext(activeDirectory,{headless:true})
  if(old)await context.route(`${origin}/**`,async route=>{const path=new URL(route.request().url()).pathname;if(path.startsWith('/api/'))return route.fallback();assert.ok(path==='/scripts/browser-persistence-harness.html'||path==='/browser-persistence-acceptance.js'||path.startsWith('/chunks/')||path.startsWith('/assets/'));await route.fulfill({body:await readFile(join(oldBundle,path)),contentType:path.endsWith('.html')?'text/html':'text/javascript'})})
  context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)))
  context.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))network.push(r.method()+':'+new URL(r.url()).pathname)})
  await context.route('**/api/v1/sync/devices/*',async route=>{assert.equal(route.request().method(),'PUT');registrations++;await route.fulfill({json:{protocol_version:1,device_id:new URL(route.request().url()).pathname.split('/').at(-1),last_ack_cursor:0}})})
  page=await context.newPage();await page.goto(`${origin}/scripts/browser-persistence-harness.html`)
 }
  async function installContinuationReceiver(){await page.evaluate(async()=>{
   globalThis.receiveContinuation=async(d,options={})=>{
    const id=options.id??d.note,project='planner-project',stamp='2026-10-20T00:00:00.000000Z',peer='44444444-4444-4444-8444-444444444444',cursor=(await nativeRows('cursors'))[0],binding=(await nativeRows('projectBindings'))[0],mh=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata')
    const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),snapshot=await local.readSnapshot(s,project)
    let source;await local.withDecryptedSnapshot(s,snapshot.token,async opened=>{source=opened.notes.find(n=>n.note.id===id)})
    const deleted=options.deleted??(d.strategy==='delete'),parent=options.parent??d.event_id,revision=options.revision??4
    const ordinary=source.state==='live'?{...source.note}:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'AUTHENTIC_SUCCESSOR',content:'AUTHENTIC_SUCCESSOR',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
    delete ordinary.revision;ordinary.content='ACTUAL_PROTECTED_PEER_CHILD '+crypto.randomUUID();ordinary.updated_at=stamp
    const note=deleted?{id,project_id:project,stage_id:ordinary.stage_id,source_type:ordinary.source_type,source_map_id:ordinary.source_map_id,source_node_id:ordinary.source_node_id,content_format:ordinary.content_format,deleted_at:stamp}:ordinary
    const header={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null},plain=c21.createNoteSyncPlaintext(header,parent,note).plaintext
    const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:binding.bootstrap_id,metadata_event_id:mh.tip_event_ids[0],stage_event_ids:[]},event:plain}
    const frame=d.protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:wrapper},true),event={...header,operation:d.protocol===2?header.operation:'event',deleted_at:d.protocol===2?header.deleted_at:null,device_id:peer,server_sequence:cursor.pull_cursor+1}
    const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const encrypted=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(encrypted.nonce),ciphertext:c21.encodeBase64Url(encrypted.ciphertext)}}finally{encrypted.nonce.fill(0);encrypted.ciphertext.fill(0)}})
    try{await session.sync.commitInboundPage(s,cursor.pull_cursor,JSON.stringify({protocol_version:d.protocol,encrypted_sync_version:d.protocol,items:[{event,object}],next_cursor:event.server_sequence,has_more:false}))}finally{frame.fill(0)}
    return{sequence:event.server_sequence,event_id:event.event_id,id,deleted,content:ordinary.content}
   }
  })}
 const bind=async()=>{await page.evaluate(async scope=>{
  globalThis.s=scope;globalThis.session=await c21.openBrowserPersistence(s.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,s)
  const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(s)
  globalThis.verifiedHDevice=device;globalThis.planner=c21.resolutionPlannerFixture(session,meta,device);globalThis.applier=planner.atomicApply();globalThis.continuation=c21.resolutionContinuationFixture(session,meta,device);globalThis.prefix=c21.resolutionPrefixFixture(session,meta,device)
 },scope);await installContinuationReceiver()}
 try{
  await launch()
  scope=await page.evaluate(async()=>{const user=crypto.randomUUID(),p=await c21.openBrowserPersistence(user),i=await p.read(user);await p.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
  await bind()
  decisions=await page.evaluate(async testCase=>{
  const {protocol,childProtocol,strategy,legacy3}=testCase
  const stamp='2026-10-19T00:00:00.000000Z',project='planner-project',peer='44444444-4444-4444-8444-444444444444',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
  await local.initializeProject(s,{project:{id:project,name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  const binding=await session.projects.importRemote(s,{project_id:project,bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
  const metadata={version:1,header:{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation:'create',revision:1,generation:1,parent_event_ids:[],updated_at:stamp},metadata:{name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
  let sequence=0
  const receive=async(protocol,event,frame,id)=>{
   const ref={event_id:event.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:id,entity_type:'note',operation:protocol===2?event.operation:'event',revision:event.revision,updated_at:event.updated_at,deleted_at:null}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   const receivedProtocol=legacy3&&event.operation==='resolution'?3:protocol
   try{await session.sync.commitInboundPage(s,sequence-1,JSON.stringify({protocol_version:receivedProtocol,encrypted_sync_version:receivedProtocol,items:[{event:ref,object}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0)}
   return{sequence,event_id:ref.event_id}
  }
  // Real imported Metadata apply establishes the actual project dependency.
  const mh=metadata.header,frame=c21.frameProjectMetadata(metadata),reference={event_id:mh.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:project,entity_type:'project_metadata',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null}
  const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:project,entityType:'project_metadata'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}});frame.fill(0)
  await session.sync.commitInboundPage(s,0,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:reference,object}],next_cursor:sequence,has_more:false}));await session.metadata.apply(s,reference,meta.auth,meta.bindings,meta.keys)
  const dependencies={bootstrap_id:binding.bootstrap_id,metadata_event_id:mh.event_id,stage_event_ids:[]},parents={}
  const fresh=(id,body)=>({id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE_PLANNER_NOTE',content:body,checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}})
  {
   const id=`note-${protocol}`,values=[];let root
   for(let i=0;i<3;i++){
    const h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:'upsert',revision:i?2:1,updated_at:stamp,deleted_at:null},note=fresh(id,`AUTHENTIC_BRANCH_${i}`.repeat(30)),plain=c21.createNoteSyncPlaintext(h,i?root:null,note).plaintext
    const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:plain},frame=protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:wrapper},i===2)
    const r=await receive(protocol,h,frame,id);if(i===0)root=h.event_id
    if(protocol===2)await session.notes.bind(meta.auth,meta.bindings,meta.keys).apply(s,r.sequence);else await session.contentNotes.bind(meta.auth,meta.bindings,meta.keys).apply(s,r.sequence)
    if(i)values.push({event_id:h.event_id,note})
   }
   parents[protocol]=values.sort((a,b)=>a.event_id.localeCompare(b.event_id))
  }
  const result=[]
  {
   const id=`note-${protocol}`,ps=parents[protocol],ids=ps.map(p=>p.event_id),selected=ps[0],other=ps[1],header={event_id:crypto.randomUUID(),parent_event_id:ids[0],additional_parent_event_ids:[ids[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp}
   const decision={conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:ids,strategy,...(['choose_version','keep_both'].includes(strategy)?{selected_event_id:selected.event_id}:{}),...(strategy==='keep_both'?{retained_event_id:other.event_id,retained_note:{...other.note,id:`clone-${protocol}`,created_at:stamp,updated_at:stamp}}:{})}
   const output=strategy==='delete'?{operation:'delete',note:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}}:{operation:'upsert',note:strategy==='manual_merge'?{...selected.note,content:'AUTHENTIC_SENDER_MERGE'}:selected.note}
   const resolution={version:2,header,mutation:'resolution',resolution:decision,result:output},wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:resolution},frame=protocol===2?c21.encodeNoteSyncResolutionV2(resolution):c21.readerFrame({id:8,version:1,event:wrapper},strategy!=='choose_version')
   const r=await receive(protocol,header,frame,id);result.push({...r,protocol:childProtocol,strategy,note:id,retained_note:decision.retained_note?.id??null})
  }
  return result[0]
 },testCase)
  const before=await snapshot(),http=network.length
  // Native transaction/request failure injection uses only this disposable profile.
  if(!legacy3&&strategy==='keep_both'){
   for(let fault=0;fault<12;fault++){
    const failed=await page.evaluate(async({sequence,fault})=>{
     const p=await planner.prepare(s,sequence),token=await applier.prepare(p.token)
     const add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put;let n=0
     for(const method of ['add','put'])IDBObjectStore.prototype[method]=function(...args){
      const position=n++,r=(method==='add'?add:put).apply(this,args)
      if(position===Math.min(fault,7)){
       if(fault<8)throw new DOMException('DISPOSABLE_WRITE_FAILURE','QuotaExceededError')
       // Native abort after a successful last write, before completion.
       if(fault===8)r.addEventListener('success',()=>r.transaction.abort(),{once:true})
       else r.addEventListener('success',()=>{if(fault===9)void meta.keys.lock();else if(fault===10)void meta.auth.logout();else void session.close()},{once:true})
      }
      return r
     }
     try{await applier.commit(token);return false}catch{return true}
     finally{Object.assign(IDBObjectStore.prototype,{add,put})}
    },{sequence:decisions.sequence,fault})
    assert.equal(failed,true,`native fault ${protocol}/${fault}`);assert.deepEqual(await snapshot(),before);faults++
    if(fault>=9){await page.evaluate(async()=>{await meta.keys.dispose();await session.close()});await bind()}
   }
  }
  const competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
  assert.equal(await competing.evaluate(async scope=>{try{await c21.openBrowserPersistence(scope.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close()
  if(protocol===3&&strategy==='choose_version'){
   await page.evaluate(async d=>{const p=await planner.prepare(s,d.sequence);globalThis.staleIdentityToken=await applier.prepare(p.token)},decisions)
   const originalIdentity=before.identities[0],changedIdentity={...originalIdentity,device_id:crypto.randomUUID()}
   const identityWrite=row=>page.evaluate(async row=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
    try{await c21.runBrowserTransaction(db,['identities'],'readwrite',(tx,result)=>{tx.objectStore('identities').put(row);result(undefined)})}finally{db.close()}
   },row)
   await identityWrite(changedIdentity);const changed=await snapshot()
   assert.equal(await page.evaluate(async()=>{try{await applier.commit(staleIdentityToken);return false}catch{return true}}),true)
   assert.deepEqual(await snapshot(),changed);await identityWrite(originalIdentity);assert.deepEqual(await snapshot(),before)
  }
  const result=await page.evaluate(async d=>{
   const p=await planner.prepare(s,d.sequence),token=await applier.prepare(p.token)
   return applier.commit(token)
  },decisions)
  assert.equal(result.status,'applied');applied++
  const after=await snapshot(),r=after.legacyNoteHistory.find(r=>r.record_kind==='resolution'),row=after.inbox.find(r=>r.event_id===decisions.event_id)
  assert.equal(r.record_version,4);assert.equal(row.record_version,10);assert.equal(row.wire_item,before.inbox.find(r=>r.event_id===decisions.event_id).wire_item)
  assert.equal(after.localProjects[0].source_revision,before.localProjects[0].source_revision+1)
  assert.equal(after.localNotes.length,before.localNotes.length+(strategy==='keep_both'?1:0))
  for(const store of ['cursors','outbox','receipts','legacyNoteIntents'])assert.deepEqual(after[store],before[store])
  for(const kind of ['candidate','group','local_version'])assert.deepEqual(after.legacyNoteHistory.filter(r=>r.record_kind===kind),before.legacyNoteHistory.filter(r=>r.record_kind===kind))
  // Full OS-backed browser/profile restart, then fresh normal-user auth/key/device.
  await context.close();await launch();await bind();assert.deepEqual(await snapshot(),after)
  const bookmark=network.length
  const replay=await page.evaluate(async d=>{
   const transaction=IDBDatabase.prototype.transaction,add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put,del=IDBObjectStore.prototype.delete,clear=IDBObjectStore.prototype.clear
   let writes=0;IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('REPLAY_WRITE')}return transaction.call(this,stores,mode,...args)}
   for(const method of ['add','put','delete','clear'])IDBObjectStore.prototype[method]=()=>{writes++;throw Error('REPLAY_WRITE')}
   try{const a=await applier.reconcile(s,d.sequence),b=await applier.reconcile(s,d.sequence);return {a,b,writes}}
   finally{IDBDatabase.prototype.transaction=transaction;Object.assign(IDBObjectStore.prototype,{add,put,delete:del,clear})}
  },decisions)
  assert.equal(replay.a.status,'already_applied');assert.equal(replay.b.status,'already_applied');assert.equal(replay.writes,0)
  assert.deepEqual(await snapshot(),after);assert.equal(network.length,bookmark)


  const child=await page.evaluate(d=>receiveContinuation(d),decisions),received=await snapshot()
  const injectHFaults=async(sequence,conflict=false)=>{
   const stable=await snapshot(),limit=conflict?3:4
   for(let fault=0;fault<limit+5;fault++){
   const rejected=await page.evaluate(async({sequence,fault,limit})=>{
    const token=await continuation.prepare(s,sequence),add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put;let n=0
    for(const method of ['add','put'])IDBObjectStore.prototype[method]=function(...args){const position=n++,request=(method==='add'?add:put).apply(this,args)
     if(position===Math.min(fault,limit)){
      if(fault<=limit)throw new DOMException('NATIVE_CONTINUATION_FAULT','QuotaExceededError')
      request.addEventListener('success',()=>{if(fault===limit+1)request.transaction.abort();else if(fault===limit+2)void meta.keys.lock();else if(fault===limit+3)void meta.auth.logout();else void session.close()},{once:true})
     }
     return request
    }
    try{await continuation.commit(token);return false}catch{return true}finally{Object.assign(IDBObjectStore.prototype,{add,put})}
   },{sequence,fault,limit})
   assert.equal(rejected,true);assert.deepEqual(await snapshot(),stable);if(conflict)forkFaults++;else continuationFaults++
   if(fault>=limit+2){await page.evaluate(async()=>{await meta.keys.dispose();await session.close()});await bind()}
   }
  }
  if(strategy==='keep_both')await injectHFaults(child.sequence)
  if(legacy3&&strategy==='choose_version'){
   await page.evaluate(async sequence=>{globalThis.staleH=await continuation.prepare(s,sequence)},child.sequence)
   const original=received.localProjects[0],changed={...original,source_revision:original.source_revision+1}
   const writeProject=row=>page.evaluate(async row=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)});try{await c21.runBrowserTransaction(db,['localProjects'],'readwrite',(tx,result)=>{tx.objectStore('localProjects').put(row);result(undefined)})}finally{db.close()}},row)
   await writeProject(changed);const drift=await snapshot()
   assert.equal(await page.evaluate(async()=>{try{await continuation.commit(staleH);return false}catch{return true}}),true);assert.deepEqual(await snapshot(),drift)
   await writeProject(original);assert.deepEqual(await snapshot(),received);hCAS++
  }
  if(legacy3&&strategy==='keep_both'){
   await page.evaluate(async sequence=>{globalThis.lostHPreparation=await continuation.prepare(s,sequence)},child.sequence)
   await context.close();await launch();await bind();preparedProcessStops++;assert.deepEqual(await snapshot(),received)
   assert.equal(await page.evaluate(async sequence=>{const owner=c21.resolutionContinuationFixture(session,meta,verifiedHDevice,true),token=await owner.prepare(s,sequence);try{await owner.commit(token);throw Error('MISSING_LOST_H_SIGNAL')}catch(e){if(e.message!=='DISPOSABLE_H_LOST_COMPLETION')throw e}return continuation.reconcile(s,sequence)},child.sequence),'already_applied');uncertain++
  }else assert.equal(await page.evaluate(c=>continuation.apply(s,c.sequence),child),'applied')
  continuations++
  const descendants=[child];let continued=child
  if(strategy==='keep_both'){
   const retained=await page.evaluate(d=>receiveContinuation(d,{id:d.retained_note}),decisions)
   assert.equal(await page.evaluate(c=>continuation.apply(s,c.sequence),retained),'applied');continuations++;descendants.push(retained);continued=retained
  }
  if(strategy==='manual_merge'){
   const fork=await page.evaluate(d=>receiveContinuation(d),decisions)
   if(legacy3)await injectHFaults(fork.sequence,true)
   assert.equal(await page.evaluate(c=>continuation.apply(s,c.sequence),fork),'conflict_preserved');continuations++;descendants.push({...fork,conflict:true})
  }else{
   const grandchild=await page.evaluate(({d,child})=>receiveContinuation(d,{id:child.id,parent:child.event_id,revision:5,deleted:true}),{d:decisions,child:continued})
   assert.equal(await page.evaluate(c=>continuation.apply(s,c.sequence),grandchild),'applied');continuations++;descendants.push(grandchild)
  }
  const progressed=await snapshot()
  for(const kind of ['resolution','group_transition'])assert.deepEqual(progressed.legacyNoteHistory.filter(h=>h.record_kind===kind),after.legacyNoteHistory.filter(h=>h.record_kind===kind))
  assert.deepEqual(progressed.inbox.find(r=>r.event_id===decisions.event_id),after.inbox.find(r=>r.event_id===decisions.event_id))
  for(const store of ['outbox','receipts','legacyNoteIntents'])assert.deepEqual(progressed[store],after[store])
  for(const field of ['proven_prefix','ack_cursor','next_local_ordinal'])assert.equal(progressed.cursors[0][field],after.cursors[0][field])
  // Another complete disk restart after actual protected continuation, not fixtures.
  await context.close();await launch();await bind();historicalReopens++
  const historic=await page.evaluate(async descendants=>{
   const tx=IDBDatabase.prototype.transaction,add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put,del=IDBObjectStore.prototype.delete,clear=IDBObjectStore.prototype.clear;let writes=0
   IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('H_REPLAY_WRITE')}return tx.call(this,stores,mode,...args)}
   for(const method of ['add','put','delete','clear'])IDBObjectStore.prototype[method]=()=>{writes++;throw Error('H_REPLAY_WRITE')}
   try{const history=await continuation.history(s),replays=[];for(const d of descendants)replays.push(await continuation.apply(s,d.sequence));return{history,replays,writes}}
   finally{IDBDatabase.prototype.transaction=tx;Object.assign(IDBObjectStore.prototype,{add,put,delete:del,clear})}
  },descendants)
  assert.equal(historic.history.resolutions,1);assert.equal(historic.history.closedGroups,1);assert.equal(historic.writes,0);assert.deepEqual(historic.replays,descendants.map(()=>'already_applied'));assert.deepEqual(await snapshot(),progressed)
  const source=await page.evaluate(async descendants=>{
   const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),snapshot=await local.readSnapshot(s,'planner-project')
   return local.withDecryptedSnapshot(s,snapshot.token,async value=>({ids:value.notes.map(n=>n.note.id).sort(),states:descendants.map(d=>{const note=value.notes.find(n=>n.note.id===d.id);return{id:d.id,state:note.state,revision:note.state==='live'?note.note.revision:note.revision,content:note.state==='live'?note.note.content:null}})}))
  },descendants)
  assert.equal(new Set(source.ids).size,source.ids.length);for(const n of source.states)assert.equal(n.revision,0)
  const expected=new Map();for(const d of descendants)if(!d.conflict)expected.set(d.id,d)
  for(const [id,d] of expected){const n=source.states.find(n=>n.id===id);assert.equal(n.state,d.deleted?'tombstone':'live');if(!d.deleted)assert.equal(n.content,d.content)}
  assert.equal(await page.evaluate(async sequence=>{try{await applier.reconcile(s,sequence);return false}catch{return true}},decisions.sequence),true)
  assert.equal(await page.evaluate(async()=>{try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(s);return false}catch{return true}}),true)
  assert.deepEqual(await snapshot(),progressed)
  if(legacy3){
   await context.close();copy=await mkdtemp(join(tmpdir(),'c21-old-t-H-copy-'));await cp(directory,copy,{recursive:true});activeDirectory=copy;old=true
   await launch();await bind();assert.deepEqual(await snapshot(),progressed)
   const oldBookmark=network.length
   const rejected=await page.evaluate(async descendants=>{
    const device=verifiedHDevice,g=c21.resolutionPrefixFixture(session,meta,device),q=c21.mixedResolutionPrefixFixture(session,meta,device),k=c21.v10RecoveryFixture(session,meta,device),mixed=c21.mixedV10RecoveryFixture(session,meta,device),o=c21.v10OrdinaryOwnerFixture(session,meta,device),privateMeta=c21.privateMetadataFixture(session,meta,device)
    const sequence=descendants[0].sequence,actions=[()=>continuation.history(s),()=>continuation.reconcile(s,sequence),()=>continuation.apply(s,sequence),()=>g.prepare(s),()=>q.prepare(s),()=>k.run(s),()=>mixed.run(s),()=>o.apply(s,sequence),()=>privateMeta.prepare(s,sequence),()=>c21.postFMetadataFixture(session,meta,device).prefix.prepare(s),()=>session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(s)]
    const outcomes=[];for(const action of actions){try{await action();outcomes.push(null)}catch(e){if(e instanceof TypeError||e instanceof ReferenceError)throw e;outcomes.push(e.code??e.message)}}return outcomes
   },descendants)
   assert.ok(rejected.every(Boolean),JSON.stringify(rejected));assert.deepEqual(await snapshot(),progressed);assert.equal(network.length,oldBookmark);oldReaders++
   await context.close();old=false;await launch();await bind();historicalReopens++
   assert.equal((await page.evaluate(()=>continuation.history(s))).resolutions,1)
   for(const d of descendants)assert.equal(await page.evaluate(sequence=>continuation.reconcile(s,sequence),d.sequence),'already_applied')
   assert.deepEqual(await snapshot(),progressed)
   const barrierBookmark=network.length
   const blocked=await page.evaluate(async()=>{try{await prefix.prepare(s);return false}catch{return true}})
   assert.equal(blocked,true);assert.deepEqual(await snapshot(),progressed);assert.equal(network.length,barrierBookmark)
  }
  if(onHistorical)await onHistorical({get page(){return page},snapshot,scope,decisions,descendants,progressed,bind,restart:async()=>{await context.close();await launch();await bind()}})
  // No push/ACK occurred before restart either (registration is external setup).
  assert.equal(network.length,registrations)
 }finally{await context?.close();await rm(directory,{recursive:true,force:true});if(copy)await rm(copy,{recursive:true,force:true})}
}
assert.deepEqual(errors,[])
console.log(JSON.stringify({result:'PASS',legacy3,oldReaders,uncertain,preparedProcessStops,hCAS,forkFaults,continuations,continuationFaults,historicalReopens,protocols:[2,3],strategies:4,applied,nativeFaultRollbacks:faults,diskRestarts:8,replays:16,replayWrites:0,realParentProducers:true,newOutbox:0,push:0,newACK:0,pageErrors:0,registrationFixtureCalls:registrations}))
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await runResolutionContinuationAcceptance()
