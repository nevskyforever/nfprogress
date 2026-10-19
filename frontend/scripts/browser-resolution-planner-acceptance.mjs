import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const directory=await mkdtemp(join(tmpdir(),'c21-resolution-planner-')),errors=[],network=[],registrations=[]
let context,page,scope,decisions
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const launch=async()=>{
 context=await chromium.launchPersistentContext(directory,{headless:true})
 context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)))
 context.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))network.push({method:r.method(),path:new URL(r.url()).pathname})})
 // Controlled registration transport only; the real auth/identity runtime mints
 // its own private device token. The planner never calls this endpoint.
 await context.route('**/api/v1/sync/devices/*',async route=>{const request=route.request();assert.equal(request.method(),'PUT');const id=new URL(request.url()).pathname.split('/').at(-1);registrations.push(id);await route.fulfill({json:{protocol_version:1,device_id:id,last_ack_cursor:0}})})
 page=await context.newPage();await page.goto(`${origin}/scripts/browser-persistence-harness.html`)
}
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
const bind=()=>page.evaluate(async scope=>{
 globalThis.s=scope;globalThis.session=await c21.openBrowserPersistence(s.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,s)
 const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(s)
 globalThis.planner=c21.resolutionPlannerFixture(session,meta,device)
},scope)
const planAll=()=>page.evaluate(async decisions=>{
 const transaction=IDBDatabase.prototype.transaction,add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put,del=IDBObjectStore.prototype.delete,clear=IDBObjectStore.prototype.clear
 let writes=0;IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('planner_readwrite')}return transaction.call(this,stores,mode,...args)}
 for(const name of ['add','put','delete','clear'])IDBObjectStore.prototype[name]=function(){writes++;throw Error('planner_write')}
 const statuses=[]
 try{for(const d of decisions){const p=await planner.prepare(s,d.sequence);globalThis.lastPlannerToken=p.token;if(Object.keys(p.token).length)throw Error('public_plan_details');const status=await planner.inspect(p.token);if(status.strategy!==d.strategy||status.parentCount!==2||status.commitAuthorized||status.ackAuthorized)throw Error('bad_plan');statuses.push(status)}if(writes)throw Error('planner_writes');return statuses}
 finally{IDBDatabase.prototype.transaction=transaction;Object.assign(IDBObjectStore.prototype,{add,put,delete:del,clear})}
},decisions)
const mutate=async(store,row,remove=false)=>page.evaluate(async({store,row,remove})=>{
 const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
 try{await c21.runBrowserTransaction(db,[store],'readwrite',(tx,result)=>{const s=tx.objectStore(store);if(remove)s.delete(row);else s.put(row);result(undefined)})}finally{db.close()}
},{store,row,remove})
try{
 await launch()
 scope=await page.evaluate(async()=>{const user=crypto.randomUUID(),p=await c21.openBrowserPersistence(user),i=await p.read(user);await p.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
 await bind()
 decisions=await page.evaluate(async()=>{
  const stamp='2026-10-19T00:00:00.000000Z',project='planner-project',peer='44444444-4444-4444-8444-444444444444',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
  await local.initializeProject(s,{project:{id:project,name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  const binding=await session.projects.importRemote(s,{project_id:project,bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
  const metadata={version:1,header:{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation:'create',revision:1,generation:1,parent_event_ids:[],updated_at:stamp},metadata:{name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
  let sequence=0
  const receive=async(protocol,event,frame,id)=>{
   const ref={event_id:event.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:id,entity_type:'note',operation:protocol===2?event.operation:'event',revision:event.revision,updated_at:event.updated_at,deleted_at:null}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   try{await session.sync.commitInboundPage(s,sequence-1,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event:ref,object}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0)}
   return{sequence,event_id:ref.event_id}
  }
  // Real imported Metadata apply establishes the actual project dependency.
  const mh=metadata.header,frame=c21.frameProjectMetadata(metadata),reference={event_id:mh.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:project,entity_type:'project_metadata',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null}
  const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:project,entityType:'project_metadata'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}});frame.fill(0)
  await session.sync.commitInboundPage(s,0,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:reference,object}],next_cursor:sequence,has_more:false}));await session.metadata.apply(s,reference,meta.auth,meta.bindings,meta.keys)
  const dependencies={bootstrap_id:binding.bootstrap_id,metadata_event_id:mh.event_id,stage_event_ids:[]},parents={}
  const fresh=(id,body)=>({id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE_PLANNER_NOTE',content:body,checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}})
  for(const protocol of [3,2]){
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
  for(const protocol of [3,2])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
   const id=`note-${protocol}`,ps=parents[protocol],ids=ps.map(p=>p.event_id),selected=ps[0],other=ps[1],header={event_id:crypto.randomUUID(),parent_event_id:ids[0],additional_parent_event_ids:[ids[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp}
   const decision={conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:ids,strategy,...(['choose_version','keep_both'].includes(strategy)?{selected_event_id:selected.event_id}:{}),...(strategy==='keep_both'?{retained_event_id:other.event_id,retained_note:{...other.note,id:`clone-${protocol}`,created_at:stamp,updated_at:stamp}}:{})}
   const output=strategy==='delete'?{operation:'delete',note:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}}:{operation:'upsert',note:strategy==='manual_merge'?{...selected.note,content:'AUTHENTIC_SENDER_MERGE'}:selected.note}
   const resolution={version:2,header,mutation:'resolution',resolution:decision,result:output},wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:resolution},frame=protocol===2?c21.encodeNoteSyncResolutionV2(resolution):c21.readerFrame({id:8,version:1,event:wrapper},strategy!=='choose_version')
   const r=await receive(protocol,header,frame,id);result.push({...r,protocol,strategy,note:id})
  }
  return result
 })
 const before=await snapshot(),bookmark=network.length,statuses=await planAll()
 assert.equal(statuses.length,8);assert.deepEqual(await snapshot(),before);assert.equal(network.length,bookmark)
 assert.equal(before.inbox.filter(r=>decisions.some(d=>d.event_id===r.event_id)).every(r=>r.state==='received'),true)
 const competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
 assert.equal(await competing.evaluate(async scope=>{try{await c21.openBrowserPersistence(scope.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close()
 // A genuine missing parent stays received, with no invented fallback witness.
 const candidate=before.legacyNoteHistory.find(r=>r.record_kind==='candidate'&&r.note_id==='note-3'&&r.header.revision===2)
 await mutate('legacyNoteHistory',[candidate.account_id,candidate.project_id,candidate.note_id,candidate.record_kind,candidate.record_id],true)
 const missing=await snapshot();assert.equal(await page.evaluate(async d=>{try{await planner.prepare(s,d.sequence);return false}catch(e){return e.code==='missing_parent'}},decisions[0]),true);assert.deepEqual(await snapshot(),missing);await mutate('legacyNoteHistory',candidate)
 await context.close();await launch();await bind();assert.deepEqual(await snapshot(),before)
 const afterNetwork=network.length;assert.deepEqual(await planAll(),statuses);assert.equal(network.length,afterNetwork);assert.deepEqual(await snapshot(),before)
 for(const kind of ['key','logout']){
  assert.equal(await page.evaluate(async kind=>{if(kind==='key')await meta.keys.lock();else await meta.auth.logout();try{await planner.inspect(lastPlannerToken);return false}catch{return true}},kind),true)
  const unchanged=await snapshot();assert.deepEqual(unchanged,before)
  await page.evaluate(async()=>{await meta.keys.dispose();await session.close()});await bind();await planAll()
 }
 // Accepted source-only HTML edit creates genuine newer encrypted Note/project
 // records. Fresh planning refuses to consume that unproven working branch.
 await page.evaluate(async()=>{const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),token=(await local.readSnapshot(s,'planner-project')).token;await local.updateNote(s,token,'note-3',{content:'NEWER_LOCAL_CONTENT'},'2026-10-19T00:00:00.000000Z')})
 const edited=await snapshot();assert.equal(await page.evaluate(async d=>{try{await planner.prepare(s,d.sequence);return false}catch{return true}},decisions[0]),true);assert.deepEqual(await snapshot(),edited)
 assert.deepEqual(edited.outbox,before.outbox);assert.deepEqual(edited.receipts,before.receipts);assert.deepEqual(edited.cursors,before.cursors);assert.deepEqual(edited.inbox,before.inbox)
 assert.equal(network.length,registrations.length);assert.deepEqual(errors,[])
 console.log(JSON.stringify({result:'PASS',protocols:[2,3],strategies:4,plans:8,realConflictProducers:true,diskRestart:true,readonlyWriteAttempts:0,newOutbox:0,ResolutionWrites:0,plannerHTTP:0,push:0,newACK:0,pageErrors:0,registrationFixtureCalls:registrations.length,missingParent:'blocked',newerSource:'blocked',keyLogout:'invalidated',secondTab:'writer_busy'}))
}finally{await context?.close();await rm(directory,{recursive:true,force:true})}
