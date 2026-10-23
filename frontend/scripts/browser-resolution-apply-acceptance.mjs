import assert from 'node:assert/strict'
import {mkdtemp,rm,cp,readFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const legacyV3=process.argv.includes('--legacy-v3'),oldBundle=process.env.C21_OLD_V10_BUNDLE
if(legacyV3){
 assert.ok(oldBundle,'C21_OLD_V10_BUNDLE must point to pinned 2320549 baseline bundle')
 assert.equal((await readFile(join(oldBundle,'baseline.sha'),'utf8')).trim(),'2320549e1c2e4ef3cc87bd91ee109c8e9bb7ebc6')
}
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const errors=[],network=[];let context,page,scope,decisions,registrations=0,faults=0,applied=0,restarts=0,oldReaders=0,joins=0,uncertain=0,preCommitProcessStops=0
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
for(const protocol of legacyV3?[2]:[2,3])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
 const testCase={protocol,strategy,legacyV3},directory=await mkdtemp(join(tmpdir(),'c21-resolution-apply-'))
 let activeDirectory=directory,old=false,copy
 const launch=async()=>{
  context=await chromium.launchPersistentContext(activeDirectory,{headless:true})
  if(old)await context.route(`${origin}/**`,async route=>{
   const path=new URL(route.request().url()).pathname
   if(path.startsWith('/api/'))return route.fallback()
   assert.ok(path==='/scripts/browser-persistence-harness.html'||path==='/browser-persistence-acceptance.js'||path.startsWith('/chunks/')||path.startsWith('/assets/'))
   await route.fulfill({body:await readFile(join(oldBundle,path)),contentType:path.endsWith('.html')?'text/html':'text/javascript'})
  })
  context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)))
  context.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))network.push(r.method()+':'+new URL(r.url()).pathname)})
  await context.route('**/api/v1/sync/devices/*',async route=>{assert.equal(route.request().method(),'PUT');registrations++;await route.fulfill({json:{protocol_version:1,device_id:new URL(route.request().url()).pathname.split('/').at(-1),last_ack_cursor:0}})})
  page=await context.newPage();await page.goto(`${origin}/scripts/browser-persistence-harness.html`)
 }
 const bind=()=>page.evaluate(async scope=>{
  globalThis.s=scope;globalThis.session=await c21.openBrowserPersistence(s.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,s)
  const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(s)
  globalThis.replayDevice=device;globalThis.planner=c21.resolutionPlannerFixture(session,meta,device);globalThis.applier=planner.atomicApply()
 },scope)
 try{
  await launch()
  scope=await page.evaluate(async()=>{const user=crypto.randomUUID(),p=await c21.openBrowserPersistence(user),i=await p.read(user);await p.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
  await bind()
  decisions=await page.evaluate(async testCase=>{
  const {protocol,strategy,legacyV3}=testCase
  const stamp='2026-10-19T00:00:00.000000Z',project='planner-project',peer='44444444-4444-4444-8444-444444444444',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
  await local.initializeProject(s,{project:{id:project,name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  const binding=await session.projects.importRemote(s,{project_id:project,bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
  const metadata={version:1,header:{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation:'create',revision:1,generation:1,parent_event_ids:[],updated_at:stamp},metadata:{name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
  let sequence=0
  const receive=async(protocol,event,frame,id)=>{
   const ref={event_id:event.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:id,entity_type:'note',operation:protocol===2?event.operation:'event',revision:event.revision,updated_at:event.updated_at,deleted_at:null}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   const receivedProtocol=legacyV3&&event.operation==='resolution'?3:protocol
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
   const r=await receive(protocol,header,frame,id);result.push({...r,protocol,strategy,note:id})
  }
  return result[0]
 },testCase)
  const before=await snapshot()
  // Native transaction/request failure injection uses only this disposable profile.
  if(strategy==='keep_both'){
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
  if((protocol===3||legacyV3)&&strategy==='choose_version'){
   await page.evaluate(async d=>{const p=await planner.prepare(s,d.sequence);globalThis.staleIdentityToken=await applier.prepare(p.token)},decisions)
   const originalIdentity=before.identities[0],changedIdentity={...originalIdentity,device_id:crypto.randomUUID()}
   const identityWrite=row=>page.evaluate(async row=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
    try{await c21.runBrowserTransaction(db,['identities'],'readwrite',(tx,result)=>{tx.objectStore('identities').put(row);result(undefined)})}finally{db.close()}
   },row)
   await identityWrite(changedIdentity);const changed=await snapshot()
   assert.equal(await page.evaluate(async()=>{try{await applier.commit(staleIdentityToken);return false}catch{return true}}),true)
   assert.deepEqual(await snapshot(),changed);await identityWrite(originalIdentity);assert.deepEqual(await snapshot(),before)
  }
  if(legacyV3&&strategy==='keep_both'){
   // Lose the private prepared token with the entire process before commit.
   await page.evaluate(async d=>{const p=await planner.prepare(s,d.sequence);globalThis.lostPreparation=await applier.prepare(p.token)},decisions)
   await context.close();await launch();await bind();restarts++;preCommitProcessStops++
   assert.deepEqual(await snapshot(),before)
  }
  const result=await page.evaluate(async({d,loseCompletion})=>{
   if(loseCompletion){
    const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(s)
    const owner=c21.resolutionPlannerFixture(session,meta,device,true),apply=owner.atomicApply(),p=await owner.prepare(s,d.sequence)
    try{await apply.commit(await apply.prepare(p.token));throw Error('MISSING_LOST_SIGNAL')}catch(e){if(e.message!=='DISPOSABLE_LOST_COMPLETION')throw e}
    return{status:(await applier.reconcile(s,d.sequence)).status,uncertain:true}
   }
   const p=await planner.prepare(s,d.sequence),token=await applier.prepare(p.token)
   return applier.commit(token)
  },{d:decisions,loseCompletion:legacyV3&&strategy==='keep_both'})
  if(result.uncertain){assert.equal(result.status,'already_applied');uncertain++}else assert.equal(result.status,'applied')
  applied++
  const after=await snapshot(),r=after.legacyNoteHistory.find(r=>r.record_kind==='resolution'),row=after.inbox.find(r=>r.event_id===decisions.event_id)
  assert.equal(r.record_version,4);assert.equal(row.record_version,10);assert.equal(row.wire_item,before.inbox.find(r=>r.event_id===decisions.event_id).wire_item)
  assert.equal(after.localProjects[0].source_revision,before.localProjects[0].source_revision+1)
  assert.equal(after.localNotes.length,before.localNotes.length+(strategy==='keep_both'?1:0))
  for(const store of ['cursors','outbox','receipts','legacyNoteIntents'])assert.deepEqual(after[store],before[store])
  for(const kind of ['candidate','group','local_version'])assert.deepEqual(after.legacyNoteHistory.filter(r=>r.record_kind===kind),before.legacyNoteHistory.filter(r=>r.record_kind===kind))
  // Full OS-backed browser/profile restart, then fresh normal-user auth/key/device.
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),after)
  const bookmark=network.length
  const replay=await page.evaluate(async d=>{
   const verifiedDevice=replayDevice
   const transaction=IDBDatabase.prototype.transaction,add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put,del=IDBObjectStore.prototype.delete,clear=IDBObjectStore.prototype.clear
   let writes=0;IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('REPLAY_WRITE')}return transaction.call(this,stores,mode,...args)}
   for(const method of ['add','put','delete','clear'])IDBObjectStore.prototype[method]=()=>{writes++;throw Error('REPLAY_WRITE')}
   try{
    const a=await applier.reconcile(s,d.sequence),b=await applier.reconcile(s,d.sequence),j=c21.v10TransportFixture(session,meta,verifiedDevice)
    const row=(await nativeRows('inbox')).find(r=>r.server_sequence===d.sequence),item=JSON.parse(row.wire_item),page=protocol=>JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[item],next_cursor:d.sequence,has_more:false})
    const replay=await j.replayInboundPage(s,d.sequence-1,page(row.protocol_version))
    const joined=row.protocol_version===2?await j.joinRetainedF2(s,d.sequence-1,page(3),row.event_id):null
    try{if(row.protocol_version===2)await j.replayInboundPage(s,d.sequence-1,page(3));else await j.joinRetainedF2(s,d.sequence-1,page(3),row.event_id);throw Error('MISSING_CROSS_PROTOCOL_REJECTION')}catch(e){if(e.code!=='conflicting_record')throw e}
    return {a,b,writes,replay,joined}
   }
   finally{IDBDatabase.prototype.transaction=transaction;Object.assign(IDBObjectStore.prototype,{add,put,delete:del,clear})}
  },decisions)
  assert.equal(replay.a.status,'already_applied');assert.equal(replay.b.status,'already_applied');assert.equal(replay.writes,0)
  assert.equal(replay.replay.replayed_events,1);if(replay.joined){assert.equal(replay.joined.matched,true);joins++}
  assert.deepEqual(await snapshot(),after);assert.equal(network.length,bookmark)
  // No push/ACK occurred before restart either (registration is external setup).
  assert.equal(network.length,registrations)
  if(legacyV3){
   await context.close()
   copy=await mkdtemp(join(tmpdir(),'c21-old-v10-copy-'));await cp(directory,copy,{recursive:true});activeDirectory=copy;old=true
   await launch();await bind();assert.deepEqual(await snapshot(),after)
   const oldBookmark=network.length
   const rejected=await page.evaluate(async d=>{
    const device=replayDevice,j=c21.v10TransportFixture(session,meta,device),h=c21.resolutionContinuationFixture(session,meta,device),g=c21.resolutionPrefixFixture(session,meta,device),q=c21.mixedResolutionPrefixFixture(session,meta,device),k=c21.v10RecoveryFixture(session,meta,device),mixed=c21.mixedV10RecoveryFixture(session,meta,device),o=c21.v10OrdinaryOwnerFixture(session,meta,device)
    if(typeof j.joinRetainedF2!=='undefined')throw Error('Expected pinned old v10 implementation')
    const actions=[()=>applier.reconcile(s,d.sequence),()=>planner.prepare(s,d.sequence),()=>j.listReceived(s),()=>h.history(s),()=>g.prepare(s),()=>q.prepare(s),()=>k.run(s),()=>mixed.run(s),()=>o.apply(s,d.sequence),()=>session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(s),async()=>{const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),snapshot=await local.readSnapshot(s,'planner-project');return local.updateNote(s,snapshot.token,d.note,{title:'MUST_REJECT_OLD_READER'},'2026-10-20T00:00:00.000000Z')},async()=>{const row=(await nativeRows('inbox')).find(r=>r.server_sequence===d.sequence);return j.replayInboundPage(s,d.sequence-1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[JSON.parse(row.wire_item)],next_cursor:d.sequence,has_more:false}))}]
    const outcomes=[];for(const action of actions){try{await action();outcomes.push(null)}catch(e){if(e instanceof TypeError||e instanceof ReferenceError)throw e;outcomes.push(e.code??e.message)}}return outcomes
   },decisions)
   assert.ok(rejected.every(Boolean),JSON.stringify(rejected));assert.deepEqual(await snapshot(),after);assert.equal(network.length,oldBookmark);oldReaders++
   await context.close();old=false;await launch();await bind();restarts++
   assert.equal((await page.evaluate(d=>applier.reconcile(s,d.sequence),decisions)).status,'already_applied');assert.deepEqual(await snapshot(),after)
  }
 }finally{await context?.close();await rm(directory,{recursive:true,force:true});if(copy)await rm(copy,{recursive:true,force:true})}
}
assert.deepEqual(errors,[])
console.log(JSON.stringify({result:'PASS',protocols:legacyV3?[3]:[2,3],rawLegacy3:legacyV3,strategies:4,applied,nativeFaultRollbacks:faults,diskRestarts:restarts,oldReaders,joins,uncertain,preCommitProcessStops,replays:applied*2,replayWrites:0,realParentProducers:true,newOutbox:0,push:0,newACK:0,pageErrors:0,registrationFixtureCalls:registrations}))
