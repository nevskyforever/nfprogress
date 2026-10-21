import {runOrdinaryOwnerCase} from './browser-v10-ordinary-owner-cases.mjs'
import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
// L STOP audit: all positive evidence comes from unchanged K/F/H/G owners;
// so replay never expands the accepted current-interval cursor contract.
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
const recoveryMode=process.argv.includes('--mixed-recovery')
const prefixMode=process.argv.includes('--mixed-prefix')||recoveryMode
const continuationMode=process.argv.includes('--mixed-continuation')||prefixMode
const ordinaryMode=process.argv.includes('--ordinary-owner')||continuationMode
const hTotals={hApplied:0,hPreserved:0,hReplays:0,hRollback:0,hRaces:0,hRevoked:0,hBarriers:0,hRestarts:0,hTabs:0,oInterleaved:0}
const qTotals={qAdvanced:0,qRaces:0,qRollback:0,qRevoked:0,qRestarts:0,qTabs:0,qReplay:0,qOrdinary:0,qForkBarriers:0}
const kTotals={kApplied:0,kRestarts:0,kRollback:0,kPrefixRecovery:0,kRevoked:0,kTabs:0,kReplay:0,kBounded:0}
const witnessMode=process.argv.includes('--mixed-source-witness')||ordinaryMode
const ordinaryTotals={applied:0,replays:0,rollbacks:0,races:0,revocations:0,barriers:0,restarts:0,tabs:0}
assert.equal(new URL(origin).hostname,'127.0.0.1')
const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const errors=[],network=[];let context,page,scope,decisions,registrations=0,profiles=0,restarts=0,metadataOwners=0,metadataRollbacks=0,ordinaryRejects=0,structuralRejects=0,sourceRejects=0
const snapshot=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
const sessionClose=()=>page.evaluate(()=>session.close())
let witnessReads=0,witnessRaces=0,witnessRevocations=0,witnessTabs=0,witnessRejects=0
const checkWitness=async()=>{
 const before=await snapshot(),traffic=network.length
 const result=await page.evaluate(async()=>{
  const tx=IDBDatabase.prototype.transaction,random=crypto.getRandomValues;let writes=0,nonces=0
  IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('WITNESS_WRITE')}return tx.call(this,stores,mode,...args)}
  crypto.getRandomValues=()=>{nonces++;throw Error('WITNESS_NONCE')}
  try{return{value:await witness.inspect(s),writes,nonces,keys:Object.keys(witness)}}finally{IDBDatabase.prototype.transaction=tx;crypto.getRandomValues=random}
 })
 assert.deepEqual(result.keys,['inspect']);assert.equal(result.writes,0);assert.equal(result.nonces,0)
 assert.equal(result.value.readOnly,true);assert.equal(result.value.ready,false);assert.equal(result.value.commitAuthorized,false);assert.equal(result.value.ackAuthorized,false)
 assert.equal(result.value.ordinaryTransitions,0);assert.ok(result.value.baselineNotes>=3)
 assert.equal(network.length,traffic);assert.deepEqual(await snapshot(),before);witnessReads++
}
for(const protocol of [2,3])for(const strategy of ['choose_version','manual_merge','delete','keep_both']){
 console.log(`${ordinaryMode?'O owner':'L boundary'} native ${protocol}/${strategy}`)
 const testCase={protocol,strategy,witnessMode},directory=await mkdtemp(join(tmpdir(),'c21-v10-ordinary-boundary-'))
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
  globalThis.ordinaryOwner=c21.v10OrdinaryOwnerFixture(session,meta,device)
  globalThis.verifiedDevice=device;globalThis.witness=c21.mixedSourceWitnessFixture(session,meta,device)
  globalThis.mixedRecovery=c21.mixedV10RecoveryFixture(session,meta,device)
 },scope)
 try{
  await launch()
  scope=await page.evaluate(async()=>{const user=crypto.randomUUID(),p=await c21.openBrowserPersistence(user),i=await p.read(user);await p.close();return{canonicalUserId:user,accountId:i.local_account_id,deviceId:i.device_id}})
  await bind()
  decisions=await page.evaluate(async testCase=>{
  const {protocol,strategy,witnessMode}=testCase
  const stamp='2026-10-19T00:00:00.000000Z',project='planner-project',peer='44444444-4444-4444-8444-444444444444',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
  await local.initializeProject(s,{project:{id:project,name:'DISPOSABLE_PLANNER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  // Genuine other-project authority must exist BEFORE any v10 history.
  await local.initializeProject(s,{project:{id:'other-project',name:'DISPOSABLE_OTHER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]})
  await session.projects.importRemote(s,{project_id:'other-project',bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})
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
  if(witnessMode)for(const id of ['baseline-live','baseline-deleted']){
   let parent=null
   for(let revision=1;revision<=2;revision++){
    const deleted=id==='baseline-deleted'&&revision===2,h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null}
    const n=deleted?{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}:fresh(id,'AUTHENTIC_PRE_F_BASELINE'.repeat(30))
    const plain=c21.createNoteSyncPlaintext(h,parent,n).plaintext,frame=protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies,event:plain}},revision===2)
    await receive(protocol,h,frame,id);parent=h.event_id
   }
  }
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
  const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:pending,next_cursor:sequence,has_more:true})
  await session.sync.commitInboundPage(s,since,rawPage)
  return{...d,since,rawPage,children,count:pending.length,next:sequence}
 },testCase)
  const seed=await page.evaluate(d=>recovery.run(s,{maxEvents:32,replay:{since:d.since,rawPage:d.rawPage}}),decisions)
  assert.equal(seed.blocker,null);assert.equal(seed.ready,false)
  const positive=await snapshot();assert.equal(positive.inbox.find(r=>r.event_id===decisions.event_id).record_version,10)
  if(witnessMode)await checkWitness()
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),positive)
  if(ordinaryMode){
   const results=await runOrdinaryOwnerCase({getPage:()=>page,snapshot,protocol,strategy,continuationMode,prefixMode,recoveryMode,
    restart:async()=>{await context.close();await launch();await bind()},
    rebind:async()=>{await sessionClose();await bind()},
    compete:async()=>{const other=await context.newPage();await other.goto(`${origin}/scripts/browser-persistence-harness.html`);assert.equal(await other.evaluate(async s=>{try{await c21.openBrowserPersistence(s.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await other.close()}
   })
   for(const key of Object.keys(ordinaryTotals))ordinaryTotals[key]+=results[key]
   if(results.h)for(const key of Object.keys(hTotals))hTotals[key]+=results.h[key]
   if(results.h?.q)for(const key of Object.keys(qTotals))qTotals[key]+=results.h.q[key]
   if(results.h?.k)for(const key of Object.keys(kTotals))kTotals[key]+=results.h.k[key]
   restarts+=results.restarts;profiles++;continue
  }
  if(witnessMode){
   await checkWitness()
   // A REAL accepted H apply races the read-only verifier's final re-read.
   // All resulting wire/source/history/proof comes from unchanged H, not puts.
   assert.equal(await page.evaluate(async protocol=>{
    const racing=c21.mixedSourceWitnessFixture(session,meta,verifiedDevice,async()=>{
     const project='planner-project',id=`note-${protocol}`,head=(await nativeRows('legacyNoteHistory')).find(r=>r.record_kind==='head'&&r.note_id===id),parent=(await nativeRows('inbox')).find(r=>r.event_id===head.linear_head_event_id),old=JSON.parse(parent.wire_item).event,stamp='2026-10-20T00:00:00.000000Z'
     const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys);let source
     await local.withDecryptedSnapshot(s,(await local.readSnapshot(s,project)).token,async opened=>{source=structuredClone(opened.notes.find(n=>n.note.id===id))})
     const {revision:_local,...note}=source.note
     if(source.state==='tombstone')note.deleted_at=stamp;else note.updated_at=stamp
     const h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:source.state==='tombstone'?'delete':'upsert',revision:old.revision+1,updated_at:stamp,deleted_at:source.state==='tombstone'?note.deleted_at:null}
     const plain=c21.createNoteSyncPlaintext(h,head.linear_head_event_id,note).plaintext,b=(await nativeRows('projectBindings')).find(b=>b.project_id===project),mh=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project)
     const frame=protocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:old.device_id,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:mh.tip_event_ids[0],stage_event_ids:[]},event:plain}},true),cursor=(await nativeRows('cursors'))[0]
     const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
     const event={...h,device_id:old.device_id,server_sequence:cursor.pull_cursor+1,operation:protocol===2?h.operation:'event',deleted_at:protocol===2?h.deleted_at:null}
     try{await session.sync.commitInboundPage(s,cursor.pull_cursor,JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event,object}],next_cursor:event.server_sequence,has_more:false}))}finally{frame.fill(0)}
     if(await continuation.apply(s,event.server_sequence)!=='applied')throw Error('H_RACE_NOT_APPLIED')
    })
    try{await racing.inspect(s);return false}catch(e){return e.code==='stale_source'}
   },protocol),true);witnessRaces++
   await checkWitness()
   const stable=await snapshot(),competing=await context.newPage();await competing.goto(`${origin}/scripts/browser-persistence-harness.html`)
   assert.equal(await competing.evaluate(async s=>{try{await c21.openBrowserPersistence(s.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);await competing.close();witnessTabs++
   assert.equal(await page.evaluate(async strategy=>{
    const revoked=c21.mixedSourceWitnessFixture(session,meta,verifiedDevice,async()=>{
     if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')
    })
    try{await revoked.inspect(s);return false}catch{return true}
   },strategy),true);witnessRevocations++;assert.deepEqual(await snapshot(),stable)
   await sessionClose();await bind();await checkWitness()
  }
  const traffic=network.length
  const audit=await page.evaluate(async protocol=>{
   const stamp='2026-10-20T00:00:00.000000Z',peer='44444444-4444-4444-8444-444444444444',project='planner-project',local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
   const all=async()=>{
    const names=['inbox','outbox','receipts','projectBindings','ownerHeads','legacyNoteHistory','legacyNoteIntents','localProjects','localNotes','cursors'],a=await Promise.all(names.map(n=>nativeRows(n)))
    return{rows:a[0],out:a[1],receipts:a[2],bindings:a[3],owners:a[4],history:a[5],intents:a[6],projects:a[7],localNotes:a[8],checkpoints:a[9],cursor:a[9][0]}
   }
   const rejected=async action=>{try{await action();return null}catch(e){return e.code??e.name}}
   const retain=async(type,id,frame,projectId=project,operation='upsert',revision=1,eventId=crypto.randomUUID(),wireProtocol=3)=>{
    const cursor=(await nativeRows('cursors'))[0],event={event_id:eventId,device_id:peer,server_sequence:cursor.pull_cursor+1,project_id:projectId,entity_id:id,entity_type:type,operation,revision,updated_at:stamp,deleted_at:null}
    const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId,entityId:id,entityType:type},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
    await meta.keys.leaseForAccount(s.accountId).use(async amk=>{
     const nonce=c21.decodeBase64Url(object.nonce),ciphertext=c21.decodeBase64Url(object.ciphertext)
     try{
      if(wireProtocol===2){const{device_id:_d,server_sequence:_s,...descriptor}=event;await c21.openNoteSyncEvent(amk,s.canonicalUserId,descriptor,{crypto_version:1,aad_version:1,nonce,ciphertext})}
      else await c21.openBrowserCanonicalObject(amk,{accountId:s.canonicalUserId,projectId,entityId:id,entityType:type,eventId},{crypto_version:1,aad_version:1,nonce,ciphertext})
     }finally{nonce.fill(0);ciphertext.fill(0)}
    })
    const page=JSON.stringify({protocol_version:wireProtocol,encrypted_sync_version:wireProtocol,items:[{event,object}],next_cursor:event.server_sequence,has_more:false})
    try{await session.sync.commitInboundPage(s,cursor.pull_cursor,page)}finally{frame.fill(0)}
    return{sequence:event.server_sequence,event,page,since:cursor.pull_cursor}
   }
   const metadata=async(projectId)=>{
    const bindings=await nativeRows('projectBindings'),owners=await nativeRows('ownerHeads'),b=bindings.find(b=>b.project_id===projectId),head=owners.find(h=>h.owner_kind==='project_metadata'&&h.owner_id===projectId),revision=head?head.history.length+1:1,eventId=crypto.randomUUID()
    const payload=c21.readerCases().find(c=>c.id===1&&c.version===1).event
    Object.assign(payload.header,{account_id:s.canonicalUserId,bootstrap_id:b.bootstrap_id,device_id:peer,project_id:projectId,entity_id:projectId,event_id:eventId,operation:head?'update':'create',revision,generation:revision,parent_event_ids:head?head.tip_event_ids:[],updated_at:stamp})
    payload.metadata.name='ACTUAL_METADATA_OWNER_AFTER_RESOLUTION'
    const p=await retain('project_metadata',projectId,c21.readerFrame({id:1,version:1,event:payload},protocol===3),projectId,'upsert',revision,eventId)
    const before={source:await nativeRows('localProjects'),notes:await nativeRows('localNotes'),history:await nativeRows('legacyNoteHistory')}
    const k=await recovery.run(s,{maxEvents:32});if(k.blocker.kind!=='unsupported_route')throw Error('K_METADATA_GUARD_CHANGED')
    const metadataToken=await session.metadata.prepareVerified(s,p.event,meta.auth,meta.bindings,meta.keys),atomicBefore=await all(),put=IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put=function(...args){const q=put.apply(this,args);if(this.name==='inbox'&&args[0].event_id===p.event.event_id)throw new DOMException('AUDIT_METADATA_FAILURE','QuotaExceededError');return q}
    let failed
    try{failed=await rejected(()=>session.metadata.commitVerifiedImportedMetadataApply(s,metadataToken))}finally{IDBObjectStore.prototype.put=put}
    if(!failed||JSON.stringify(await all())!==JSON.stringify(atomicBefore))throw Error('METADATA_ATOMIC_ROLLBACK_FAILED')
    const applied=await session.metadata.apply(s,p.event,meta.auth,meta.bindings,meta.keys)
    const after={source:await nativeRows('localProjects'),notes:await nativeRows('localNotes'),history:await nativeRows('legacyNoteHistory')}
    if(JSON.stringify(before)!==JSON.stringify(after)||applied!=='applied')throw Error('METADATA_SOURCE_MUTATION')
    await transport.replayInboundPage(s,p.since,p.page)
    const token=await prefix.prepare(s);await prefix.commit(await prefix.prepareCommit(token))
    return p
   }
   await metadata(project);await metadata('other-project')
   const results=[]
   for(const projectId of [project,'other-project'])for(const transportProtocol of [2,3]){
    const id=`independent-${projectId}-${transportProtocol}`,eventId=crypto.randomUUID(),h={event_id:eventId,project_id:projectId,entity_id:id,entity_type:'note',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null}
    const note={id,project_id:projectId,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE_ORDINARY',content:'REAL_ENCRYPTED_INDEPENDENT_NOTE'.repeat(40),checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
    const plain=c21.createNoteSyncPlaintext(h,null,note).plaintext,b=(await nativeRows('projectBindings')).find(b=>b.project_id===projectId),mh=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===projectId)
    const frame=transportProtocol===2?c21.encodeNoteSyncPlaintext(plain):c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:mh.tip_event_ids[0],stage_event_ids:[]},event:plain}},protocol===3)
    const p=await retain('note',id,frame,projectId,transportProtocol===2?'upsert':'event',1,eventId,transportProtocol),before=await all(),reader=transportProtocol===2?session.notes:session.contentNotes
    const code=await rejected(()=>reader.bind(meta.auth,meta.bindings,meta.keys).prepare(s,p.sequence))
    if(code!=='corrupt_record'||JSON.stringify(await all())!==JSON.stringify(before))throw Error('ORDINARY_REJECTION_BOUNDARY_CHANGED')
    results.push(code)
   }
   for(const order of [false,true]){
    const eventId=crypto.randomUUID(),b=(await nativeRows('projectBindings')).find(b=>b.project_id===project),mh=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),payload=c21.readerCases().find(c=>c.id===(order?3:2)&&c.version===1).event,id=order?'stage_order':'boundary-stage'
    Object.assign(payload.header,{account_id:s.canonicalUserId,bootstrap_id:b.bootstrap_id,project_id:project,entity_id:id,event_id:eventId,device_id:peer,operation:'create',revision:1,generation:1,parent_event_ids:[],metadata_event_id:mh.tip_event_ids[0],updated_at:stamp})
    if(order){payload.stage=null;payload.stage_ids=[];payload.stage_heads={}}
    const p=await retain(order?'stage_order':'stage',id,c21.readerFrame({id:order?3:2,version:1,event:payload},protocol===3),project,'upsert',1,eventId),before=await all()
    const code=await rejected(()=>(order?session.stageOrder:session.stages).bind(meta.auth,meta.bindings,meta.keys).prepare(s,p.sequence))
    if(code!=='corrupt_record'||JSON.stringify(await all())!==JSON.stringify(before))throw Error('STRUCTURAL_REJECTION_BOUNDARY_CHANGED')
    results.push(code);globalThis.lastBoundaryPage=p
   }
   const before=await all(),k=await recovery.run(s,{maxEvents:32})
   if(k.applied.length||k.blocker.kind!=='unsupported_route'||JSON.stringify(await all())!==JSON.stringify(before))throw Error('K_SKIPPED_BOUNDARY')
   await transport.replayInboundPage(s,lastBoundaryPage.since,lastBoundaryPage.page)
   await continuation.history(s);const g=await prefix.calculate(await prefix.prepare(s))
   return{results,prefix:g.candidate_proven_prefix,firstPending:k.blocker.sequence,metadata:2}
  },protocol)
  assert.deepEqual(audit.results,Array(6).fill('corrupt_record'));assert.equal(audit.prefix,audit.firstPending-1)
  assert.equal(network.length,traffic);metadataOwners+=audit.metadata;metadataRollbacks+=audit.metadata;ordinaryRejects+=4;structuralRejects+=2
  if(witnessMode)await checkWitness()
  const intact=await snapshot();await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),intact)
  assert.equal(await page.evaluate(async()=>{const r=await recovery.run(s,{maxEvents:32});await continuation.history(s);return r.blocker.kind}),'unsupported_route');assert.deepEqual(await snapshot(),intact)
  if(witnessMode)await checkWitness()
  // NEGATIVE ONLY: valid encrypted revision drift, never a positive applied
  // ordinary specimen or source authority. Original R/F/H evidence is untouched.
  assert.equal(await page.evaluate(async()=>{
   const source=(await nativeRows('localProjects')).find(p=>p.project_id==='planner-project'),lease=meta.keys.leaseForAccount(s.accountId)
   const envelope=await lease.use(async amk=>{
    // Canonical local source is opened via its real owner, not a guessed payload.
    let project
    const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),snapshot=await local.readSnapshot(s,'planner-project')
    await local.withDecryptedSnapshot(s,snapshot.token,async opened=>{project={local_format:1,kind:'project',account_id:s.accountId,device_id:s.deviceId,project_id:'planner-project',source_revision:source.source_revision+1,deleted_at:null,project:opened.project,member_ids:opened.notes.map(n=>n.note.id).sort()}})
    const raw=new TextEncoder().encode(c21.canonical(project)),o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:'planner-project',entityId:'planner-project',entityType:'project_metadata'},raw)
    try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{raw.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)}
   })
   const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
   try{await c21.runBrowserTransaction(db,['localProjects'],'readwrite',(tx,result)=>{tx.objectStore('localProjects').put({...source,source_revision:source.source_revision+1,envelope});result(undefined)})}finally{db.close()}
   const names=['inbox','outbox','receipts','projectBindings','ownerHeads','legacyNoteHistory','legacyNoteIntents','localProjects','localNotes','cursors'],a=await Promise.all(names.map(n=>nativeRows(n)))
   const v={rows:a[0],out:a[1],receipts:a[2],bindings:a[3],owners:a[4],history:a[5],intents:a[6],projects:a[7],localNotes:a[8],checkpoints:a[9],cursor:a[9][0]}
   await lease.use(amk=>c21.authenticateResolutionHistory(s,v,amk,()=>lease.isCurrent()))
   let rejected=0;for(const action of [()=>continuation.history(s),()=>prefix.prepare(s),()=>recovery.run(s)])try{await action()}catch{rejected++}
   return rejected
  }),3)
  const drift=await snapshot();assert.deepEqual(drift.legacyNoteHistory,intact.legacyNoteHistory);assert.deepEqual(drift.inbox,intact.inbox);assert.deepEqual(drift.localNotes,intact.localNotes);sourceRejects+=3
  if(witnessMode){assert.equal(await page.evaluate(async()=>{try{await witness.inspect(s);return false}catch(e){return e.code==='source_mismatch'}}),true);witnessRejects++;assert.deepEqual(await snapshot(),drift)}
  await context.close();await launch();await bind();restarts++;assert.deepEqual(await snapshot(),drift)
  assert.equal(await page.evaluate(async()=>{try{await prefix.prepare(s);return false}catch{return true}}),true);assert.deepEqual(await snapshot(),drift)
  if(witnessMode){assert.equal(await page.evaluate(async()=>{try{await witness.inspect(s);return false}catch(e){return e.code==='source_mismatch'}}),true);witnessRejects++;assert.deepEqual(await snapshot(),drift)}
  profiles++
 }finally{await context?.close();await rm(directory,{recursive:true,force:true})}
}
assert.deepEqual(errors,[])
assert.equal(network.filter(n=>n.includes('note-reader-capabilities')||n.includes('/ack')||n.includes('/push')).length,0)
if(!ordinaryMode)console.log(JSON.stringify({result:'PASS',L:'STOP_SOURCE_AUTHORITY_AUDIT',profiles,restarts,metadataOwners,metadataRollbacks,ordinaryRejects,structuralRejects,sourceRejects,registrations,pageErrors:0,newProductionRoutes:0,ContentPush:0,ResolutionAck:0,NoteCapabilityPut:0,ready:false}))
if(witnessMode&&!ordinaryMode)console.log(JSON.stringify({result:'PASS',N:'READ_ONLY_MIXED_SOURCE_WITNESS',witnessReads,witnessRaces,witnessRevocations,witnessTabs,witnessRejects,ordinaryPostFPositiveClaims:0,witnessWrites:0,witnessNonces:0,ready:false}))

if(ordinaryMode)assert.equal(network.filter(n=>!/^PUT:\/api\/v1\/sync\/devices\/[^/]+$/.test(n)).length,0)
if(ordinaryMode)console.log(JSON.stringify({result:'PASS',O:'DORMANT_V10_ORDINARY_OWNER',...ordinaryTotals,profiles,restarts,registrations,pageErrors:0,unauthorizedHttp:0,productionRoutes:0,ContentPush:0,ResolutionAck:0,NoteCapabilityPut:0,ready:false}))

if(continuationMode)console.log(JSON.stringify({result:'PASS',P:'H_MIXED_SOURCE_CONTINUATION',...hTotals,profiles,pageErrors:0,unauthorizedHttp:0,GIntegration:0,KRouting:0,ResolutionAck:0,ready:false}))
if(prefixMode)console.log(JSON.stringify({result:'PASS',Q:'G_MIXED_SOURCE_LOCAL_PREFIX',...qTotals,profiles,pageErrors:0,unauthorizedHttp:0,KRouting:0,ResolutionAck:0,NoteCapabilityPut:0,ContentPush:0,ready:false}))
if(recoveryMode)console.log(JSON.stringify({result:'PASS',stage:'C21.2.09',...kTotals,profiles,pageErrors:0,unauthorizedHttp:0,defaultKUnchanged:true,productionRecovery:0,ResolutionAck:0,NoteCapabilityPut:0,ContentPush:0,ready:false}))
