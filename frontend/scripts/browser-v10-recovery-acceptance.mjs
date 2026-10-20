import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
// K starts from pending encrypted events. Actual ordinary/F/H/G owners create evidence;
// so replay never expands the accepted current-interval cursor contract.
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const errors=[],network=[];let context,page,scope,decisions,registrations=0,faults=0,recovered=0,restarts=0,budgetPasses=0,replays=0
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
for(const protocol of [2,3])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
 console.log(`K native ${protocol}/${strategy}`)
 const testCase={protocol,strategy},directory=await mkdtemp(join(tmpdir(),'c21-v10-recovery-'))
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
  globalThis.recovery=c21.v10RecoveryFixture(session,meta,device);globalThis.transport=c21.v10TransportFixture(session,meta,device);globalThis.readiness=c21.noteReaderReadinessFixture(session,meta,device);globalThis.planner=c21.resolutionPlannerFixture(session,meta,device);globalThis.applier=planner.atomicApply();globalThis.continuation=c21.resolutionContinuationFixture(session,meta,device);globalThis.prefix=c21.resolutionPrefixFixture(session,meta,device)
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
  await session.sync.commitInboundPage(s,0,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event:reference,object}],next_cursor:sequence,has_more:false}))
  const dependencies={bootstrap_id:binding.bootstrap_id,metadata_event_id:mh.event_id,stage_event_ids:[]},parents={}
  const fresh=(id,body)=>({id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE_PLANNER_NOTE',content:body,checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}})
  {
   const id=`note-${protocol}`,values=[];let root
   for(let i=0;i<3;i++){
    const h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:'upsert',revision:i?2:1,updated_at:stamp,deleted_at:null},note=fresh(id,`AUTHENTIC_BRANCH_${i}`.repeat(30)),plain=c21.createNoteSyncPlaintext(h,i?root:null,note).plaintext
    const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:plain},frame=protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:wrapper},i===2)
    const r=await receive(protocol,h,frame,id);if(i===0)root=h.event_id
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
  const orphan=strategy==='choose_version'?null:await child(d.note,crypto.randomUUID())
  // Real, encrypted received Resolution with no accepted apply authority.
  const id=d.note,ps=parents[protocol],ids=ps.map(p=>p.event_id),header={event_id:crypto.randomUUID(),parent_event_id:ids[0],additional_parent_event_ids:[ids[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp}
  const resolution={version:2,header,mutation:'resolution',resolution:{conflict_group_id:crypto.randomUUID(),conflict_generation:1,resolved_event_ids:ids,strategy:'choose_version',selected_event_id:ids[0]},result:{operation:'upsert',note:ps[0].note}}
  const receivedResolution=await receive(protocol,header,protocol===2?c21.encodeNoteSyncResolutionV2(resolution):c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:resolution}},true),id)
  const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:pending,next_cursor:sequence,has_more:true})
  await session.sync.commitInboundPage(s,since,rawPage)
  return{...d,since,rawPage,children,orphan,receivedResolution,count:pending.length,next:sequence}
 },testCase)
  const original=await snapshot(),bookmark=network.length
  assert.deepEqual(original.legacyNoteHistory,[]);assert.deepEqual(original.ownerHeads,[])
  assert.equal(await page.evaluate(async d=>{try{await planner.prepare(s,d.sequence);return null}catch(e){return e.code}},decisions),'missing_parent');assert.deepEqual(await snapshot(),original)
  const first=await page.evaluate(d=>recovery.run(s,{maxEvents:3,replay:{since:d.since,rawPage:d.rawPage}}),decisions)
  assert.deepEqual(first.applied.map(r=>r.sequence),[1,2,3]);assert.equal(first.blocker.kind,'budget_exhausted');assert.equal(first.ready,false);budgetPasses++
  const partial=await snapshot();assert.equal(partial.cursors[0].proven_prefix,0);assert.equal(network.length,bookmark)
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),partial)
  if(strategy==='keep_both'){
   // Abort the F transaction after its inbox10 put. Earlier independent ordinary
   // commits survive; F's source/history/proof changes MUST all roll back.
   assert.equal(await page.evaluate(async d=>{
    const put=IDBObjectStore.prototype.put;let hit=false
    IDBObjectStore.prototype.put=function(...args){const q=put.apply(this,args);if(this.name==='inbox'&&args[0].record_version===10){hit=true;q.addEventListener('success',()=>this.transaction.abort(),{once:true})}return q}
    try{await recovery.run(s,{maxEvents:32});return false}catch{return hit}finally{IDBObjectStore.prototype.put=put}
   },decisions),true)
   const failed=await snapshot();assert.equal(failed.inbox.find(r=>r.event_id===decisions.event_id).state,'received');assert.equal(failed.legacyNoteHistory.some(r=>r.record_kind==='resolution'),false)
   assert.deepEqual(failed.localProjects,partial.localProjects);assert.deepEqual(failed.localNotes,partial.localNotes);faults++
   await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),failed)
  }
  const fpass=await page.evaluate(maxEvents=>recovery.run(s,{maxEvents}),strategy==='keep_both'?1:2)
  assert.ok(fpass.applied.some(r=>r.route==='resolution'));assert.equal(fpass.blocker.kind,'budget_exhausted');budgetPasses++
  const afterF=await snapshot(),r=afterF.legacyNoteHistory.find(r=>r.record_kind==='resolution'),resolution=afterF.inbox.find(r=>r.event_id===decisions.event_id)
  assert.equal(resolution.record_version,10);assert.equal(afterF.cursors[0].proven_prefix,decisions.sequence);assert.equal(afterF.cursors[0].ack_cursor,0)
  if(strategy==='keep_both'){
   assert.equal(await page.evaluate(async d=>{
    const put=IDBObjectStore.prototype.put;let hit=false
    IDBObjectStore.prototype.put=function(...args){const q=put.apply(this,args);if(this.name==='inbox'&&args[0].server_sequence===d.children[0].sequence){hit=true;q.addEventListener('success',()=>void session.close(),{once:true})}return q}
    try{await recovery.run(s,{maxEvents:32});return false}catch{return hit}finally{IDBObjectStore.prototype.put=put}
   },decisions),true)
   assert.deepEqual(await snapshot(),afterF);faults++
   await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),afterF)
  }
  const traffic=network.length,complete=await page.evaluate(d=>recovery.run(s,{maxEvents:32,replay:{since:d.since,rawPage:d.rawPage}}),decisions)
  assert.equal(network.length,traffic);assert.equal(complete.ready,false);assert.equal(complete.declarationAllowed,false);assert.equal(complete.ackAuthorized,false);assert.equal(complete.readiness.ready,false)
  assert.equal(complete.blocker.kind,strategy==='choose_version'?'unsupported_generation':strategy==='manual_merge'?'unresolved_fork':'dependency_unavailable')
  assert.equal(complete.blocker.sequence,strategy==='manual_merge'?decisions.children.at(-1).sequence:(decisions.orphan??decisions.receivedResolution).sequence)
  const after=await snapshot();assert.deepEqual(after.inbox.find(r=>r.event_id===decisions.event_id),resolution)
  assert.deepEqual(after.legacyNoteHistory.filter(r=>['resolution','group_transition'].includes(r.record_kind)),afterF.legacyNoteHistory.filter(r=>['resolution','group_transition'].includes(r.record_kind)))
  assert.equal(after.cursors[0].proven_prefix,(decisions.orphan??decisions.receivedResolution).sequence-1-(strategy==='manual_merge'?1:0));assert.equal(after.cursors[0].ack_cursor,0)
  for(const row of after.inbox)assert.equal(row.wire_item,original.inbox.find(r=>r.event_id===row.event_id).wire_item)
  for(const name of ['identities','accountBindings','outbox','receipts','projectBindings','legacyNoteIntents'])assert.deepEqual(after[name],original[name])
  if(decisions.orphan)assert.equal(after.inbox.find(r=>r.event_id===decisions.orphan.event_id).state,'received');assert.equal(after.inbox.find(r=>r.event_id===decisions.receivedResolution.event_id).state,'received')
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),after)
  const stableTraffic=network.length,stable=await page.evaluate(async d=>{
   const tx=IDBDatabase.prototype.transaction,random=crypto.getRandomValues;let writes=0,nonces=0
   IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('STABLE_RECOVERY_WRITE')}return tx.call(this,stores,mode,...args)}
   crypto.getRandomValues=()=>{nonces++;throw Error('STABLE_RECOVERY_NONCE')}
   try{return{value:await recovery.run(s,{maxEvents:32,replay:{since:d.since,rawPage:d.rawPage}}),writes,nonces}}
   finally{IDBDatabase.prototype.transaction=tx;crypto.getRandomValues=random}
  },decisions)
  assert.deepEqual(stable.value.applied,[]);assert.equal(stable.value.blocker.kind,complete.blocker.kind);assert.equal(stable.writes,0);assert.equal(stable.nonces,0);assert.equal(network.length,stableTraffic);assert.deepEqual(await snapshot(),after);replays+=2
  const competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
  assert.equal(await competing.evaluate(async s=>{try{await c21.openBrowserPersistence(s.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close()
  assert.equal(await page.evaluate(async strategy=>{
   if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')
   try{await recovery.run(s);return false}catch{return true}
  },strategy),true);assert.deepEqual(await snapshot(),after)
  recovered++
 }finally{await context?.close();await rm(directory,{recursive:true,force:true})}
}
assert.deepEqual(errors,[])
assert.equal(network.filter(n=>n.includes('note-reader-capabilities')||n.includes('/ack')||n.includes('/push')).length,0)
console.log(JSON.stringify({result:'PASS',v10Recovery:true,profiles:recovered,protocols:[2,3],strategies:4,budgetPasses,restarts,ownerRollbackFaults:faults,replays,revocations:8,competingTabs:8,registrations,pageErrors:errors.length,unauthorizedWrites:0,ContentPush:0,ResolutionAck:0,NoteCapabilityPut:0,ready:false}))
