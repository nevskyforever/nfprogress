import assert from 'node:assert/strict'
export async function acceptMetadataPrefix({page,scope:originalScope,cases,reopenProfile,network}){
 const names=['identities','accountBindings','inbox','outbox','receipts','cursors','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents'],project='metadata-prefix-project',stamp='2026-10-14T00:00:00.000000Z',peer='44444444-4444-4444-8444-444444444444'
 const snap=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
 const start={reg:network.registration.length,cap:network.capability.length,ack:network.ack.length,mode:network.mode.length,registry:network.registry.length}
 let lastScope,reference,final
 for(const applied of [true,false]){
  await page.evaluate(async()=>{await meta.keys.dispose();await session.close()})
  const user=applied?'ffffffff-ffff-4fff-8fff-ffffffffffff':'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
  const scope=await page.evaluate(async user=>{globalThis.session=await c21.openBrowserPersistence(user);const id=await session.read(user);return{canonicalUserId:user,accountId:id.local_account_id,deviceId:id.device_id}},user)
  await page.evaluate(async({scope,project})=>{globalThis.meta=await c21.metadataFixture(session,scope);globalThis.mpScope=scope;globalThis.mpPrefix=session.proven.bind(meta.auth,meta.bindings,meta.keys);globalThis.mpNotes=session.notes.bind(meta.auth,meta.bindings,meta.keys);await session.localSource.bind(meta.auth,meta.bindings,meta.keys).initializeProject(scope,{project:{id:project,name:'PRIVATE_METADATA_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[]});globalThis.mpBinding=await session.projects.importRemote(scope,{project_id:project,bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0})},{scope,project})
  const note=seq=>page.evaluate(async({scope,project,stamp,peer,seq})=>{
   const event={event_id:crypto.randomUUID(),project_id:project,entity_id:'note-'+seq,entity_type:'note',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null},n={id:event.entity_id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'PRIVATE_NOTE',content:'PRIVATE_BODY',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
   const item=await meta.keys.leaseForAccount(scope.accountId).use(async amk=>{const {plaintext}=c21.createNoteSyncPlaintext(event,null,n),bytes=c21.encodeNoteSyncPlaintext(plaintext);try{const o=await c21.encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:project,entityId:event.entity_id,entityType:'note'},bytes);return{event:{...event,device_id:peer,server_sequence:seq},object:{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}}finally{bytes.fill(0)}})
   await session.sync.commitInboundPage(scope,seq-1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[item],next_cursor:seq,has_more:false}));await mpNotes.apply(scope,seq)
  },{scope,project,stamp,peer,seq})
  await note(1);assert.equal((await page.evaluate(scope=>mpPrefix.advance(scope),scope)).candidate_proven_prefix,1)
  const ref=await page.evaluate(async({scope,project,stamp,peer})=>{
   const e={version:2,header:{account_id:scope.canonicalUserId,bootstrap_id:mpBinding.bootstrap_id,device_id:peer,entity_id:project,event_id:crypto.randomUUID(),generation:1,operation:'create',parent_event_ids:[],project_id:project,revision:1,updated_at:stamp},metadata:{name:'PRIVATE_METADATA'.repeat(30),goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false,cover_reference:null},deleted_at:null}
   const reference={event_id:e.header.event_id,device_id:peer,server_sequence:2,project_id:project,entity_id:project,entity_type:'project_metadata',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null}
   const item=await meta.keys.leaseForAccount(scope.accountId).use(async amk=>{const original=c21.frameProjectMetadata(e),frame=c21.compressCanonicalFrame(original);if(frame[11]!==1)throw Error('expected_ID1');try{const o=await c21.encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:project,entityId:project,entityType:'project_metadata'},frame);return{event:reference,object:{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}}finally{frame.fill(0);original.fill(0)}})
   await session.sync.commitInboundPage(scope,1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[item],next_cursor:2,has_more:false}));return reference
  },{scope,project,stamp,peer})
  if(applied)assert.equal(await page.evaluate(({scope,ref})=>session.metadata.apply(scope,ref,meta.auth,meta.bindings,meta.keys),{scope,ref}),'applied')
  await note(3)
  const target=applied?3:1;assert.equal((await page.evaluate(scope=>mpPrefix.calculate(scope),scope)).candidate_proven_prefix,target)
  if(applied){
   const before=await snap()
   const aborted=await page.evaluate(async scope=>{const p=await mpPrefix.prepare(scope),put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,...args){const r=put.call(this,v,...args);if(this.name==='cursors')r.addEventListener('success',()=>this.transaction.abort(),{once:true});return r};try{await mpPrefix.commit(p);return false}catch{return true}finally{IDBObjectStore.prototype.put=put}},scope)
   assert.equal(aborted,true);assert.deepEqual(await snap(),before)
   for(const kind of ['lock','logout']){const rejected=await page.evaluate(async({scope,kind})=>{const p=await mpPrefix.prepare(scope);if(kind==='lock')meta.keys.lock();else await meta.auth.logout();try{await mpPrefix.commit(p);return false}catch{return true}},{scope,kind});assert.equal(rejected,true);assert.deepEqual(await snap(),before);await page.evaluate(async scope=>{await meta.keys.dispose();globalThis.meta=await c21.metadataFixture(session,scope);globalThis.mpPrefix=session.proven.bind(meta.auth,meta.bindings,meta.keys)},scope)}
   assert.equal(await page.evaluate(async originalScope=>{try{await mpPrefix.prepare(originalScope);return false}catch{return true}},originalScope),true)
  }
  const countBefore=network.ack.length+network.mode.length+network.registration.length+network.capability.length+network.registry.length
  await page.evaluate(scope=>mpPrefix.advance(scope),scope)
  assert.equal(network.ack.length+network.mode.length+network.registration.length+network.capability.length+network.registry.length,countBefore)
  await page.route('**/api/v1/sync/devices/*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:0})}))
  await page.route('**/api/v2/sync/encrypted/capabilities',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2})}))
  await page.route('**/api/v3/sync/encrypted/compression-reader-capabilities',async r=>{assert.deepEqual(r.request().postDataJSON(),{device_id:scope.deviceId,compression_id1:true});await r.fulfill({status:204})})
  await page.route('**/api/v1/cloud/projects/bootstrap',async r=>{const b=await page.evaluate(async account=>(await nativeRows('projectBindings')).find(b=>b.account_id===account),scope.accountId);await r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({projects:[{project_id:project,bootstrap_id:b.bootstrap_id,origin_device_id:peer,state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:3})})})
  await page.route('**/api/v3/sync/encrypted/ack',async r=>{assert.deepEqual(r.request().postDataJSON(),{protocol_version:3,encrypted_sync_version:3,device_id:scope.deviceId,cursor:target});await r.fulfill({status:204})})
  const result=await page.evaluate(async scope=>{const device=await session.device.bind(meta.auth,meta.bindings).registerVerified(scope),reader=await session.readers.bind(meta.auth,meta.bindings).declare(scope,device),registry=(await session.registry.bind(meta.auth,meta.bindings,meta.keys).reconcile(scope)).token,p=await mpPrefix.prepareAck(scope,reader,registry);const result=await mpPrefix.ackOnce(p);if((await mpPrefix.ackOnce(p)).status!=='no_progress')throw Error('replay');return result},scope)
  assert.deepEqual(result,{status:'advanced',cursor:target,ready:false})
  const state=await page.evaluate(scope=>session.sync.readCheckpoint(scope),scope);assert.equal(state.proven_prefix,target);assert.equal(state.ack_cursor,target);assert.equal(state.pull_cursor,3)
  for(const pattern of ['**/api/v1/sync/devices/*','**/api/v2/sync/encrypted/capabilities','**/api/v3/sync/encrypted/compression-reader-capabilities','**/api/v1/cloud/projects/bootstrap','**/api/v3/sync/encrypted/ack'])await page.unroute(pattern)
  cases.push(applied?'real imported coverless ID1 Metadata2 between Notes1/3 verifies prefix3/ACK3; prefix abort/key/logout/isolation safe, proof and prefix preparation zero HTTP':'received-only readable ID1 Metadata2 blocks Note3; prefix1/ACK1 max, reader capability cannot replace applied proof')
  if(applied){lastScope=scope;reference=ref;final=await snap()}
 }
 await page.evaluate(async()=>{await meta.keys.dispose();await session.close()})
 const open=()=>page.evaluate(async scope=>{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope);globalThis.mpPrefix=session.proven.bind(meta.auth,meta.bindings,meta.keys)},lastScope)
 await page.reload();await open();const reopened=await page.evaluate(scope=>session.sync.readCheckpoint(scope),lastScope);assert.equal(reopened.proven_prefix,3);assert.equal(reopened.ack_cursor,3)
 page=await reopenProfile();await open();assert.deepEqual(await page.evaluate(scope=>session.sync.readCheckpoint(scope),lastScope),reopened)
 assert.equal(await page.evaluate(({scope,ref})=>session.metadata.apply(scope,ref,meta.auth,meta.bindings,meta.keys),{scope:lastScope,ref:reference}),'already_applied')
 const after=await snap();for(const name of names){const old=final[name].filter(r=>r.account_id===lastScope.accountId||r.local_account_id===lastScope.accountId),now=after[name].filter(r=>r.account_id===lastScope.accountId||r.local_account_id===lastScope.accountId);assert.deepEqual(now,old)}
 cases.push('Metadata-qualified prefix3/ACK3 authority/history/bytes survive renderer and disk reopen; exact applied replay preserves state without new network or ready')
 assert.equal(network.registration.length-start.reg,2);assert.equal(network.capability.length-start.cap,2);assert.equal(network.ack.length-start.ack,2);assert.equal(network.mode.length-start.mode,6);assert.equal(network.registry.length-start.registry,2)
 await page.evaluate(async scope=>{await meta.keys.dispose();await session.close();globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope)},originalScope)
 return page
}
