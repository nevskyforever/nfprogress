import assert from 'node:assert/strict'
export async function acceptReaderAck({page,scope:originalScope,cases,reopenProfile,network}){
 const names=['identities','accountBindings','inbox','outbox','receipts','cursors','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents'],user='eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
 const snap=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names)
 const beforeReaders=await snap()
 const matrix=await page.evaluate(async()=>{
  const result=[]
  for(const c of c21.readerCases()){
   const a=await c21.readFixture(c,c21.readerFrame(c)),b=await c21.readFixture(c,c21.readerFrame(c,true));if(c21.canonical(a)!==c21.canonical(b)||c21.canonical(b)!==c21.canonical(c.event))throw Error('canonical_mismatch')
   for(const kind of ['codec','version','truncated','stream','length','trailing','semantic','family']){
    let f=c21.readerFrame(c,true)
    if(kind==='codec')f[9]=99;else if(kind==='version')f[10]=99;else if(kind==='truncated')f=f.slice(0,19);else if(kind==='stream')f[f.length-1]^=255;else if(kind==='length')new DataView(f.buffer).setUint32(12,new DataView(f.buffer).getUint32(12)+1);else if(kind==='trailing'){const x=new Uint8Array(f.length+1);x.set(f);new DataView(x.buffer).setUint32(16,x.length-20);f=x}else f=c21.readerFrame({...c,event:kind==='semantic'?{...c.event,version:99}:{version:1,header:{},wrong:true}},true)
    let rejected=false;try{await c21.readFixture(c,f)}catch{rejected=true}if(!rejected)throw Error('malformed_accepted')
   }
   result.push([c.id,c.version])
  }
  return result
 })
 assert.equal(matrix.length,16);assert.deepEqual([...new Set(matrix.map(c=>c[0]))],[1,2,3,4,5,6,7,8,9,10,11,12,13]);assert.deepEqual(await snap(),beforeReaders)
 cases.push('all13 canonical readers/all16 codec-version pairs authenticated ID0/ID1 equivalent in Chromium; eight malformed categories per pair reject with all12 stores unchanged')
 await page.evaluate(async()=>{await meta.keys.dispose();await session.close()})
 const scope=await page.evaluate(async user=>{globalThis.session=await c21.openBrowserPersistence(user);const id=await session.read(user);return{canonicalUserId:user,accountId:id.local_account_id,deviceId:id.device_id}},user)
 let registered=false,declared=false,serverAck=0,behavior='normal'
 const counts={registration:network.registration.length,capability:network.capability.length,ack:network.ack.length,mode:network.mode.length,registry:network.registry.length}
 async function routes(){
  await page.route('**/api/v1/sync/devices/*',async r=>{assert.equal(r.request().method(),'PUT');assert.equal(r.request().headers().authorization,'Bearer fixture-access');assert.equal(r.request().postData(),null);assert.equal(new URL(r.request().url()).pathname.split('/').at(-1),scope.deviceId);registered=true;await r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({protocol_version:1,device_id:scope.deviceId,last_ack_cursor:serverAck})})})
  await page.route('**/api/v2/sync/encrypted/capabilities',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2})}))
  await page.route('**/api/v3/sync/encrypted/compression-reader-capabilities',async r=>{assert.equal(registered,true);assert.equal(r.request().method(),'PUT');assert.deepEqual(r.request().postDataJSON(),{device_id:scope.deviceId,compression_id1:true});assert.equal(r.request().headers().authorization,'Bearer fixture-access');declared=true;await r.fulfill({status:204})})
  await page.route('**/api/v1/cloud/projects/bootstrap',async r=>{const b=await page.evaluate(async account=>(await nativeRows('projectBindings')).find(b=>b.account_id===account),scope.accountId);await r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({projects:[{project_id:b.project_id,bootstrap_id:b.bootstrap_id,origin_device_id:'44444444-4444-4444-8444-444444444444',state:'active',initial_event_count:0,initial_max_server_sequence:0}],current_cursor:9})})})
  await page.route('**/api/v3/sync/encrypted/ack',async r=>{
   assert.equal(registered&&declared,true);assert.equal(r.request().headers().authorization,'Bearer fixture-access');assert.deepEqual(r.request().postDataJSON(),{protocol_version:3,encrypted_sync_version:3,device_id:scope.deviceId,cursor:7})
   if(behavior==='failure'){await r.fulfill({status:503,contentType:'application/json',body:'{}'});return}serverAck=Math.max(serverAck,7)
   if(behavior==='lost'){await r.abort();return}await r.fulfill({status:204})
  })
 }
 const open=()=>page.evaluate(async scope=>{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope);globalThis.ackScope=scope;globalThis.ackPrefix=session.proven.bind(meta.auth,meta.bindings,meta.keys)},scope)
 await page.evaluate(async scope=>{globalThis.meta=await c21.metadataFixture(session,scope);globalThis.ackScope=scope;globalThis.ackPrefix=session.proven.bind(meta.auth,meta.bindings,meta.keys)},scope)
 await routes()
 const gates=()=>page.evaluate(async scope=>{globalThis.deviceProof=await session.device.bind(meta.auth,meta.bindings).registerVerified(scope);globalThis.readerProof=await session.readers.bind(meta.auth,meta.bindings).declare(scope,deviceProof);globalThis.registryProof=(await session.registry.bind(meta.auth,meta.bindings,meta.keys).reconcile(scope)).token},scope)
 await gates()
 await page.evaluate(async scope=>{await session.readers.bind(meta.auth,meta.bindings).declare(scope,deviceProof);globalThis.ackPlan=await ackPrefix.prepareAck(scope,readerProof,registryProof)},scope)
 const before=await snap(),invoke=()=>page.evaluate(()=>ackPrefix.ackOnce(ackPlan)),reject=async()=>assert.equal(await page.evaluate(async()=>{try{await ackPrefix.ackOnce(ackPlan);return false}catch{return true}}),true)
 behavior='failure';await reject();assert.deepEqual(await snap(),before);assert.equal(serverAck,0)
 behavior='lost';await reject();assert.deepEqual(await snap(),before);assert.equal(serverAck,7)
 behavior='normal'
 const metadata=await page.evaluate(scope=>session.device.bind(meta.auth,meta.bindings).registerOnce(scope),scope);assert.equal(metadata.serverAckCursor,7);assert.deepEqual(await snap(),before)
 const aborted=await page.evaluate(async()=>{const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,...args){const r=put.call(this,v,...args);if(this.name==='cursors')r.addEventListener('success',()=>this.transaction.abort(),{once:true});return r};try{await ackPrefix.ackOnce(ackPlan);return false}catch{return true}finally{IDBObjectStore.prototype.put=put}})
 assert.equal(aborted,true);assert.deepEqual(await snap(),before);assert.equal(serverAck,7)
 assert.deepEqual(await invoke(),{status:'advanced',cursor:7,ready:false})
 const advanced=await snap(),expected=structuredClone(before);expected.cursors.find(r=>r.account_id===scope.accountId).ack_cursor=7;assert.deepEqual(advanced,expected)
 assert.equal((await invoke()).status,'no_progress');assert.equal(network.ack.length-counts.ack,4)
 assert.equal((await page.evaluate(scope=>ackPrefix.calculate(scope),scope)).first_blocking_sequence,8)
 cases.push('explicit current registration + ID1-only declaration + authoritative mode3 ACK7; HTTP failure/lost response/local abort keep ACK0, exact retry advances only ACK, replay no HTTP, Document8 barrier still blocks Note9')
 await page.reload();await open();await routes();await gates();await page.evaluate(async scope=>{globalThis.ackPlan=await ackPrefix.prepareAck(scope,readerProof,registryProof)},scope);assert.equal((await invoke()).status,'no_progress')
 page=await reopenProfile();await open();await routes();await gates();await page.evaluate(async scope=>{globalThis.ackPlan=await ackPrefix.prepareAck(scope,readerProof,registryProof)},scope);assert.equal((await invoke()).status,'no_progress')
 const persisted=await snap();assert.deepEqual(persisted.identities,advanced.identities);assert.deepEqual(persisted.cursors,advanced.cursors)
 cases.push('positive ACK7/proven7/pull9 and exact durable device survive reload + disk reopen; separate registration/redeclaration/current registry repeated, no extra ACK')
 await page.evaluate(()=>meta.auth.logout());await reject();assert.deepEqual(await snap(),persisted)
 cases.push('stale auth revokes reader/registration/ACK evidence after restart; no stale HTTP or local cursor write, ready=false')
 assert.equal(network.registration.length-counts.registration,4);assert.equal(network.capability.length-counts.capability,4);assert.equal(network.registry.length-counts.registry,3);assert.equal(network.ack.length-counts.ack,4);assert.equal(network.mode.length-counts.mode,9)
 for(const pattern of ['**/api/v1/sync/devices/*','**/api/v2/sync/encrypted/capabilities','**/api/v3/sync/encrypted/compression-reader-capabilities','**/api/v1/cloud/projects/bootstrap','**/api/v3/sync/encrypted/ack'])await page.unroute(pattern)
 await page.evaluate(async scope=>{await meta.keys.dispose();await session.close();globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);globalThis.meta=await c21.metadataFixture(session,scope)},originalScope)
 return page
}
