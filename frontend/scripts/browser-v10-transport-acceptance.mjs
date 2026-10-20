import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
// J uses real F/H/G producers. Pending encrypted children are retained WITH R,
// so replay never expands the accepted current-interval cursor contract.
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const errors=[],network=[];let context,page,scope,decisions,registrations=0,faults=0,applied=0,continuations=0,replays=0,scans=0,restarts=0
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
for(const protocol of [2,3])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
 console.log(`J native ${protocol}/${strategy}`)
 const testCase={protocol,strategy},directory=await mkdtemp(join(tmpdir(),'c21-v10-transport-'))
 const launch=async()=>{
  context=await chromium.launchPersistentContext(directory,{headless:true})
  context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)))
  context.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))network.push(r.method()+':'+new URL(r.url()).pathname)})
  await context.route('**/api/v1/sync/devices/*',async route=>{assert.equal(route.request().method(),'PUT');registrations++;await route.fulfill({json:{protocol_version:1,device_id:new URL(route.request().url()).pathname.split('/').at(-1),last_ack_cursor:0}})})
  page=await context.newPage();await page.goto(`${origin}/scripts/browser-persistence-harness.html`)
 }
 const bind=()=>page.evaluate(async scope=>{
  globalThis.s=scope;globalThis.session=await c21.openBrowserPersistence(s.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,s)
  const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(s)
  globalThis.transport=c21.v10TransportFixture(session,meta,device);globalThis.readiness=c21.noteReaderReadinessFixture(session,meta,device);globalThis.planner=c21.resolutionPlannerFixture(session,meta,device);globalThis.applier=planner.atomicApply();globalThis.continuation=c21.resolutionContinuationFixture(session,meta,device);globalThis.prefix=c21.resolutionPrefixFixture(session,meta,device)
 },scope)
 try{
  await launch()
  scope=await page.evaluate(async()=>{const user=crypto.randomUUID(),p=await c21.openBrowserPersistence(user),i=await p.read(user);await p.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
  await bind()
  decisions=await page.evaluate(async testCase=>{
  const {protocol,strategy}=testCase
  const stamp='2026-10-19T00:00:00.000000Z',project='planner-project',peer='44444444-4444-4444-8444-444444444444',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
  await local.initializeProject(s,{project:{id:project,name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  const binding=await session.projects.importRemote(s,{project_id:project,bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
  const metadata={version:1,header:{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation:'create',revision:1,generation:1,parent_event_ids:[],updated_at:stamp},metadata:{name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
  let sequence=0,batch=false;const pending=[]
  const receive=async(protocol,event,frame,id)=>{
   const ref={event_id:event.event_id,device_id:peer,server_sequence:++sequence,project_id:project,entity_id:id,entity_type:'note',operation:protocol===2?event.operation:'event',revision:event.revision,updated_at:event.updated_at,deleted_at:protocol===2?(event.deleted_at??null):null}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   try{if(batch)pending.push({event:ref,object});else await session.sync.commitInboundPage(s,sequence-1,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event:ref,object}],next_cursor:sequence,has_more:false}))}finally{frame.fill(0)}
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
  const result=[];const since=sequence;batch=true
  {
   const id=`note-${protocol}`,ps=parents[protocol],ids=ps.map(p=>p.event_id),selected=ps[0],other=ps[1],header={event_id:crypto.randomUUID(),parent_event_id:ids[0],additional_parent_event_ids:[ids[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp}
   const decision={conflict_group_id:crypto.randomUUID(),conflict_generation:77,resolved_event_ids:ids,strategy,...(['choose_version','keep_both'].includes(strategy)?{selected_event_id:selected.event_id}:{}),...(strategy==='keep_both'?{retained_event_id:other.event_id,retained_note:{...other.note,id:`clone-${protocol}`,created_at:stamp,updated_at:stamp}}:{})}
   const output=strategy==='delete'?{operation:'delete',note:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}}:{operation:'upsert',note:strategy==='manual_merge'?{...selected.note,content:'AUTHENTIC_SENDER_MERGE'}:selected.note}
   const resolution={version:2,header,mutation:'resolution',resolution:decision,result:output},wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:resolution},frame=protocol===2?c21.encodeNoteSyncResolutionV2(resolution):c21.readerFrame({id:8,version:1,event:wrapper},strategy!=='choose_version')
   const r=await receive(protocol,header,frame,id);result.push({...r,protocol,strategy,note:id})
  }
  const d=result[0],children=[]
  const child=async(id=d.note,parent=d.event_id)=>{
   const deleted=strategy==='delete',note=deleted?{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}:fresh(id,'AUTHENTIC_BATCH_CHILD'.repeat(30))
   const header={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision:4,updated_at:stamp,deleted_at:deleted?stamp:null},plain=c21.createNoteSyncPlaintext(header,parent,note).plaintext
   const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:plain}
   return receive(protocol,header,protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:wrapper},strategy!=='choose_version'),id)
  }
  children.push(await child())
  if(strategy==='keep_both')children.push(await child(`clone-${protocol}`))
  if(strategy==='manual_merge')children.push(await child()) // genuine unresolved fork
  const orphan=await child(d.note,crypto.randomUUID())
  // Real, encrypted received Resolution with no accepted apply authority.
  const id=d.note,ps=parents[protocol],ids=ps.map(p=>p.event_id),header={event_id:crypto.randomUUID(),parent_event_id:ids[0],additional_parent_event_ids:[ids[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp}
  const resolution={version:2,header,mutation:'resolution',resolution:{conflict_group_id:crypto.randomUUID(),conflict_generation:1,resolved_event_ids:ids,strategy:'choose_version',selected_event_id:ids[0]},result:{operation:'upsert',note:ps[0].note}}
  const receivedResolution=await receive(protocol,header,protocol===2?c21.encodeNoteSyncResolutionV2(resolution):c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:resolution}},true),id)
  const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:pending,next_cursor:sequence,has_more:true})
  await session.sync.commitInboundPage(s,since,rawPage)
  return{...d,since,rawPage,children,orphan,receivedResolution,count:pending.length,next:sequence}
 },testCase)
  const before=await snapshot()
  assert.equal(await page.evaluate(async d=>{const p=await planner.prepare(s,d.sequence);return (await applier.commit(await applier.prepare(p.token))).status},decisions),'applied');applied++
  for(const child of decisions.children){const status=await page.evaluate(c=>continuation.apply(s,c.sequence),child);assert.ok(['applied','conflict_preserved'].includes(status));continuations++}
  const g=await page.evaluate(async()=>{const token=await prefix.prepare(s),value=await prefix.calculate(token);await prefix.commit(await prefix.prepareCommit(token));return value})
  assert.equal(g.ackAuthorized,false)
  assert.equal(g.candidate_proven_prefix,decisions.orphan.sequence-1-(strategy==='manual_merge'?1:0))
  const proven=await snapshot(),resolution=proven.inbox.find(r=>r.event_id===decisions.event_id)
  assert.equal(resolution.record_version,10);assert.equal(resolution.wire_item,before.inbox.find(r=>r.event_id===decisions.event_id).wire_item)
  for(const child of decisions.children)assert.notEqual(proven.inbox.find(r=>r.event_id===child.event_id).state,'received')
  // Both original failures are reproduced over real native F/H/G evidence.
  const old=await page.evaluate(async d=>{
   const rejected=async action=>{try{await action();return null}catch(e){return e.code}}
   return{replay:await rejected(()=>session.sync.commitInboundPage(s,d.since,d.rawPage)),scan:await rejected(()=>session.sync.listReceived(s))}
  },decisions)
  assert.deepEqual(old,{replay:'corrupt_record',scan:'corrupt_record'});assert.deepEqual(await snapshot(),proven)
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),proven)
  const bookmark=network.length
  // Lock out ALL storage writes and nonce generation during J acceptance.
  const output=await page.evaluate(async d=>{
   const transaction=IDBDatabase.prototype.transaction,methods=Object.fromEntries(['add','put','delete','clear'].map(k=>[k,IDBObjectStore.prototype[k]])),random=crypto.getRandomValues
   let writes=0,nonces=0
   IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('J_WRITE')}return transaction.call(this,stores,mode,...args)}
   for(const k of Object.keys(methods))IDBObjectStore.prototype[k]=()=>{writes++;throw Error('J_WRITE')}
   crypto.getRandomValues=()=>{nonces++;throw Error('J_NONCE')}
   try{
    const a=await transport.replayInboundPage(s,d.since,d.rawPage),b=await transport.replayInboundPage(s,d.since,d.rawPage),received=await transport.listReceived(s),limited=await transport.listReceived(s,1,d.orphan.sequence-1),tail=await transport.listReceived(s,200,d.orphan.sequence),end=await transport.listReceived(s,1,d.next)
    return{a,b,received,limited,tail,end,writes,nonces}
   }finally{IDBDatabase.prototype.transaction=transaction;Object.assign(IDBObjectStore.prototype,methods);crypto.getRandomValues=random}
  },decisions)
  for(const r of [output.a,output.b])assert.deepEqual(r,{committed_cursor:decisions.next,new_events:0,replayed_events:decisions.count,has_more:true})
  assert.deepEqual(output.received.map(r=>r.event_id),[decisions.orphan.event_id,decisions.receivedResolution.event_id])
  assert.equal(output.limited[0].event_id,decisions.orphan.event_id);assert.equal(output.limited.length,1);assert.equal(output.tail[0].event_id,decisions.receivedResolution.event_id);assert.deepEqual(output.end,[])
  assert.equal(output.writes,0);assert.equal(output.nonces,0);assert.equal(network.length,bookmark);assert.deepEqual(await snapshot(),proven);replays+=2;scans+=4
  // Genuine received Resolution stays ciphertext, never creates an apply proof.
  assert.equal(output.received[1].state,'received');assert.equal(output.received[1].record_version,1)
  assert.equal(await page.evaluate(async()=>{try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(s);return false}catch{return true}}),true)
  assert.equal((await snapshot()).cursors[0].ack_cursor,0)
  const competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
  assert.equal(await competing.evaluate(async s=>{try{await c21.openBrowserPersistence(s.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close()
  for(const operation of ['replay','scan'])for(const fault of ['request','abort','key','logout','profile']){
   const rejected=await page.evaluate(async({d,fault,operation})=>{
    const prototype=operation==='scan'?IDBIndex.prototype:IDBObjectStore.prototype,get=prototype.get;let injected=false
    prototype.get=function(...args){const store=operation==='scan'?this.objectStore:this,r=get.apply(this,args)
     if(store.name==='inbox'&&!injected){injected=true
      if(fault==='request')throw new DOMException('J_REQUEST_FAILURE','UnknownError')
      r.addEventListener('success',()=>{if(fault==='abort')store.transaction.abort();else if(fault==='key')void meta.keys.lock();else if(fault==='logout')void meta.auth.logout();else void session.close()},{once:true})
     }return r
    }
    // replay uses primary/index gets after bounded inventory authentication.
    try{if(operation==='replay')await transport.replayInboundPage(s,d.since,d.rawPage);else await transport.listReceived(s);return false}catch{return injected}
    finally{prototype.get=get}
   },{d:decisions,fault,operation})
   assert.equal(rejected,true,`J native failure ${protocol}/${strategy}/${fault}`);assert.deepEqual(await snapshot(),proven);faults++
   if(['key','logout','profile'].includes(fault)){await page.evaluate(async()=>{await meta.keys.dispose();await session.close()});await bind()}
  }
  if(protocol===3&&strategy==='keep_both'){
   const replace=(store,row)=>page.evaluate(async({store,row})=>{
    const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
    try{await c21.runBrowserTransaction(db,[store],'readwrite',(tx,result)=>{tx.objectStore(store).put(row);result(undefined)})}finally{db.close()}
   },{store,row})
   const rejectsBoth=()=>page.evaluate(async d=>{let rejected=0;for(const action of [()=>transport.replayInboundPage(s,d.since,d.rawPage),()=>transport.listReceived(s)])try{await action()}catch{rejected++}return rejected},decisions)
   const identity=proven.identities[0];await replace('identities',{...identity,device_id:crypto.randomUUID()})
   const changed=await snapshot();assert.equal(await rejectsBoth(),2);assert.deepEqual(await snapshot(),changed);await replace('identities',identity)
   for(const fault of ['proof_digest','missing_field','unknown_version','unknown_state','foreign_device']){
    const corrupt=structuredClone(resolution)
    if(fault==='proof_digest')corrupt.resolution_proof.outcome_digest='0'.repeat(64)
    if(fault==='missing_field')delete corrupt.resolution_proof.output_digests
    if(fault==='unknown_version')corrupt.record_version=11
    if(fault==='unknown_state')corrupt.state='applied'
    if(fault==='foreign_device')corrupt.device_id=crypto.randomUUID()
    await replace('inbox',corrupt);const damaged=await snapshot();assert.equal(await rejectsBoth(),2);assert.deepEqual(await snapshot(),damaged);await replace('inbox',resolution)
   }
   assert.deepEqual(await snapshot(),proven)
  }
  // Native event index and immutable interval reject tampering without repairs.
  for(const mutation of ['nonce','descriptor','truncated','old_interval']){
   assert.equal(await page.evaluate(async({d,mutation})=>{
    const p=JSON.parse(d.rawPage)
    if(mutation==='nonce')p.items[0].object.nonce=(p.items[0].object.nonce[0]==='A'?'B':'A')+p.items[0].object.nonce.slice(1)
    if(mutation==='descriptor')p.items[0].event.event_id=crypto.randomUUID()
    if(mutation==='truncated')p.items.shift()
    if(mutation==='old_interval'){p.items.pop();p.next_cursor--}
    try{await transport.replayInboundPage(s,d.since,JSON.stringify(p));return false}catch{return true}
   },{d:decisions,mutation}),true);assert.deepEqual(await snapshot(),proven)
  }
 }finally{await context?.close();await rm(directory,{recursive:true,force:true})}
}
assert.deepEqual(errors,[])
assert.equal(network.filter(n=>n.includes('note-reader-capabilities')||n.includes('/ack')||n.includes('/push')).length,0)
console.log(JSON.stringify({v10Transport:true,profiles:8,F:applied,H:continuations,diskRestarts:restarts,replays,scans,nativeFailures:faults,registrations,pageErrors:errors.length,writes:0,newNonces:0,ContentPush:0,ResolutionAck:0,NoteCapabilityPut:0}))
