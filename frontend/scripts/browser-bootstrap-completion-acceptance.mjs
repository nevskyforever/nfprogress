/** C21.1.12: intercept existing production completion endpoint, never a real backend. */
import assert from 'node:assert/strict'
export async function acceptBootstrapCompletion({page,scope,users,cases,expectCode,tab,reopenProfile}) {
  const stamp='2026-10-13T00:00:00.000000Z'
  let mode='ok',held,holdRelease
  const installRoute=async()=>page.route('**/api/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname
    assert.equal(req.method(),'POST');assert.match(path,/^\/api\/v1\/cloud\/projects\/[^/]+\/bootstrap\/complete$/)
    assert.equal(req.headers().authorization,'Bearer fixture-access')
    const body=req.postDataJSON();assert.deepEqual(Object.keys(body).sort(),['bootstrap_id','device_id','initial_event_count','initial_max_server_sequence'].sort());assert.equal(body.device_id,scope.deviceId)
    const id=decodeURIComponent(path.split('/')[5])
    const response={project:{project_id:id,bootstrap_id:body.bootstrap_id,origin_device_id:body.device_id,state:'active',initial_event_count:body.initial_event_count,initial_max_server_sequence:body.initial_max_server_sequence},current_cursor:2000}
    if(mode==='server'){await route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({detail:{code:'fixture_failure',message:'PRIVATE_SERVER_FAILURE'}})});return}
    if(mode==='lost'){await route.abort('failed');return}
    if(mode==='timeout'){held=route;return}
    if(mode==='hold'){held=route;await new Promise(resolve=>{holdRelease=resolve})}
    if(mode==='wrong')response.project.bootstrap_id='00000000-0000-4000-8000-000000000000'
    if(mode==='low')response.current_cursor=0
    if(mode==='malformed')response.project.extra='unexpected'
    if(mode==='keylock')await page.evaluate(()=>meta.keys.lock())
    if(mode==='logout'){await page.evaluate(()=>meta.auth.logout());try{await route.abort('failed')}catch{/* Request already aborted by auth invalidation. */}return}
    if(mode==='close')await page.evaluate(()=>session.close())
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(response)})
  })
  const bind=async()=>page.evaluate(()=>{globalThis.completion=session.completion.bind(meta.auth,meta.bindings,meta.keys);globalThis.local=session.localSource.bind(meta.auth,meta.bindings,meta.keys);globalThis.initial=session.initialNotes.bind(meta.auth,meta.bindings,meta.keys)})
  await bind();await installRoute()
  const snapshot=()=>page.evaluate(async()=>Object.fromEntries(await Promise.all(['projectBindings','outbox','receipts','cursors','inbox','ownerHeads','localProjects','localNotes'].map(async s=>[s,await nativeRows(s)]))))
  const read=id=>page.evaluate(({scope,id})=>session.projects.read(scope,id),{scope,id})
  const create=async(id,ids)=>page.evaluate(async({scope,id,ids,stamp})=>{
    const project={id,name:'PRIVATE_COMPLETION_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}}
    const notes=ids.map(n=>({state:'live',note:{id:n,project_id:id,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'PRIVATE_COMPLETION_TITLE',content:'PRIVATE_COMPLETION_BODY',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{},revision:0}}))
    await local.initializeProject(scope,{project,notes});const p=await session.projects.prepare(scope,{project_id:id,mode:'upload_existing'}),r=await session.projects.confirmRegistration(scope,p,{remote_state:'initializing',remote_high_water:0});return(await initial.capture(scope,r)).binding
  },{scope,id,ids,stamp})
  const accept=async(b,base)=>page.evaluate(async({scope,b,base})=>{const rows=(await nativeRows('outbox')).filter(r=>b.initial_event_count>0&&r.local_ordinal>=b.initial_local_ordinal_hi-b.initial_event_count+1&&r.local_ordinal<=b.initial_local_ordinal_hi).sort((a,b)=>a.local_ordinal-b.local_ordinal);for(let i=0;i<rows.length;i++)await session.sync.commitUploadAcceptance(scope,rows[i],{protocol_version:rows[i].protocol_version,encrypted_sync_version:rows[i].protocol_version,current_cursor:base+i,results:[{event_id:rows[i].event_id,server_sequence:base+i,duplicate:false}]})},{scope,b,base})
  const mark=b=>page.evaluate(({scope,b})=>completion.markCompleting(scope,b),{scope,b})
  const remote=b=>page.evaluate(({scope,b})=>completion.completeRemote(scope,b),{scope,b})
  const main=await create('completion-project',['completion-a','completion-z'])
  let saved=await snapshot();await expectCode(page,`completion.markCompleting(scopeA,${JSON.stringify(main)})`,'bootstrap_incomplete');assert.deepEqual(await snapshot(),saved)
  await accept(main,500);const completed=await mark(main);assert.equal(completed.phase,'completing');assert.equal(completed.initial_max_server_sequence,501)
  saved=await snapshot();assert.deepEqual(await mark(main),completed);assert.deepEqual(await snapshot(),saved)
  const firstRow=(await page.evaluate(()=>nativeRows('outbox'))).find(r=>r.local_ordinal===main.initial_local_ordinal_hi)
  const extra=JSON.parse(firstRow.raw_body);extra.items[0].event.event_id=crypto.randomUUID();extra.items[0].event.entity_id='unrelated-completion-later'
  const extraRow=(await page.evaluate(({scope,raw})=>session.sync.enqueue(scope,[raw]),{scope,raw:JSON.stringify(extra)}))[0].item
  await page.evaluate(({scope,row})=>session.sync.commitUploadAcceptance(scope,row,{protocol_version:row.protocol_version,encrypted_sync_version:row.protocol_version,current_cursor:900,results:[{event_id:row.event_id,server_sequence:900,duplicate:false}]}),{scope,row:extraRow})
  assert.equal((await mark(completed)).initial_max_server_sequence,501)
  cases.push('real captured→completing derives exact all-member receipt max in same strict transaction; incomplete fails; exact replay stable; later receipt900 cannot inflate initial max501')
  const active=await remote(completed);assert.equal(active.phase,'completing');assert.equal(active.remote_state,'active');assert.equal(active.remote_high_water,2000);assert.equal(active.initial_max_server_sequence,501)
  assert.deepEqual(await page.evaluate(({scope,id})=>session.projects.evaluateReadiness(scope,id),{scope,id:main.project_id}),{ready:false,code:'ack_proof_unavailable',required_cursor:2000});assert.deepEqual(await remote(active),active)
  cases.push('exact production POST endpoint/body/Bearer auth intercepted; authoritative active/high-water persists with completing phase; exact durable replay sends no HTTP, ACK/ready remain blocked')
  const partial=await create('partial-completion',['partial-a','partial-z'])
  const partialRows=(await page.evaluate(()=>nativeRows('outbox'))).filter(r=>r.local_ordinal>=partial.initial_local_ordinal_hi-1&&r.local_ordinal<=partial.initial_local_ordinal_hi)
  await page.evaluate(({scope,row})=>session.sync.commitUploadAcceptance(scope,row,{protocol_version:row.protocol_version,encrypted_sync_version:row.protocol_version,current_cursor:510,results:[{event_id:row.event_id,server_sequence:510,duplicate:false}]}),{scope,row:partialRows[0]})
  saved=await snapshot();await expectCode(page,`completion.markCompleting(scopeA,${JSON.stringify(partial)})`,'bootstrap_incomplete');assert.deepEqual(await snapshot(),saved)
  const conflicted=await create('conflict-completion',['conflict-completion-note']);await accept(conflicted,520)
  const receipt=(await page.evaluate(()=>nativeRows('receipts'))).find(r=>r.server_sequence===520)
  const mutate=async(value)=>page.evaluate(async value=>{const db=await new Promise((resolve,reject)=>{const r=indexedDB.open(c21.WEB_DATABASE_NAME);r.onsuccess=()=>resolve(r.result);r.onerror=reject});try{await c21.runBrowserTransaction(db,['receipts'],'readwrite',(tx,result)=>{tx.objectStore('receipts').put(value);result(undefined)})}finally{db.close()}},value)
  await mutate({...receipt,device_id:scope.canonicalUserId});await expectCode(page,`completion.markCompleting(scopeA,${JSON.stringify(conflicted)})`,'corrupt_record');await mutate(receipt)
  const beforeAbort=await snapshot(),code=await page.evaluate(async({scope,b})=>{const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,...a){const r=put.call(this,v,...a);if(this.name==='projectBindings')r.addEventListener('success',()=>this.transaction.abort(),{once:true});return r};try{await completion.markCompleting(scope,b);return'bad'}catch(e){return e.code}finally{IDBObjectStore.prototype.put=put}},{scope,b:conflicted})
  assert.equal(code,'storage_failed');assert.deepEqual(await snapshot(),beforeAbort)
  cases.push('real partial receipt/conflicting receipt reject; abort after binding request success rolls back phase AND frozen max without receipt/outbox/ACK changes')
  const empty=await create('empty-completion',[]),emptyCompleting=await mark(empty);assert.equal(emptyCompleting.initial_max_server_sequence,0);assert.equal((await remote(emptyCompleting)).remote_state,'active')
  cases.push('native empty cohort count0/HI0/max0 completes locally and via exact zero-proof POST, without nonexistent receipts or ordinals')
  const failure=await create('failure-completion',['failure-completion-note']);await accept(failure,530);const failureCompleting=await mark(failure)
  for(const testMode of ['server','lost','malformed','wrong','low']){
    mode=testMode;saved=await snapshot();const result=await page.evaluate(async({scope,b})=>{try{await completion.completeRemote(scope,b);return'bad'}catch(e){return e.code}},{scope,b:failureCompleting});assert.equal(result,['server','lost'].includes(mode)?'bootstrap_completion_failed':'bootstrap_response_rejected');assert.deepEqual(await snapshot(),saved)
  }
  mode='timeout';saved=await snapshot()
  const timed=await page.evaluate(async({scope,b})=>{const timer=globalThis.setTimeout;globalThis.setTimeout=(fn,ms,...a)=>timer(fn,ms===30000?20:ms,...a);try{await completion.completeRemote(scope,b);return'bad'}catch(e){return e.code}finally{globalThis.setTimeout=timer}},{scope,b:failureCompleting})
  assert.equal(timed,'bootstrap_completion_failed');assert.deepEqual(await snapshot(),saved);try{await held.abort('failed')}catch{/* Browser timeout already aborted this intercepted request. */}
  mode='ok';assert.equal((await remote(failureCompleting)).remote_state,'active')
  cases.push('HTTP failure/lost response/bounded timeout and malformed/wrong-bootstrap/nonmonotone response retain exact completing proof; explicit idempotent retry uses same body')
  const crash=await create('response-commit-failure',['response-commit-note']);await accept(crash,540);const crashCompleting=await mark(crash);saved=await snapshot()
  const commitCode=await page.evaluate(async({scope,b})=>{const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,...a){if(this.name==='projectBindings'&&v.remote_state==='active')throw new DOMException('fixture','QuotaExceededError');return put.call(this,v,...a)};try{await completion.completeRemote(scope,b);return'bad'}catch(e){return e.code}finally{IDBObjectStore.prototype.put=put}},{scope,b:crashCompleting})
  assert.equal(commitCode,'quota_exceeded');assert.deepEqual(await snapshot(),saved)
  await page.reload();await page.evaluate(async({scope,users})=>{globalThis.users=users;globalThis.scopeA=scope;globalThis.session=await c21.openBrowserPersistence(users[0]);globalThis.meta=await c21.metadataFixture(session,scope)},{scope,users});await bind();await installRoute()
  assert.deepEqual(await read(crash.project_id),crashCompleting);assert.equal((await remote(crashCompleting)).remote_state,'active')
  cases.push('server success/local quota retains completing; renderer reload and exact already-active server replay safely commit original proof')
  const lifecycle=await create('lifecycle-completion',['lifecycle-completion-note']);await accept(lifecycle,550);const lifecycleCompleting=await mark(lifecycle)
  for(const testMode of ['keylock','logout','close']){mode=testMode;saved=await snapshot();const result=await page.evaluate(async({scope,b})=>{try{await completion.completeRemote(scope,b);return'bad'}catch(e){return e.code}},{scope,b:lifecycleCompleting});assert.equal(result,'closed');assert.deepEqual(await snapshot(),saved);if(testMode==='close')await page.evaluate(async()=>{globalThis.session=await c21.openBrowserPersistence(users[0])});await page.evaluate(async scope=>{await meta.keys.dispose();globalThis.meta=await c21.metadataFixture(session,scope)},scope);await bind()}
  mode='hold';const inFlight=remote(lifecycleCompleting);while(!holdRelease)await new Promise(r=>setTimeout(r,10));const competing=await tab();await expectCode(competing,'c21.openBrowserPersistence(users[0])','writer_busy');await competing.close();holdRelease();await inFlight;mode='ok'
  cases.push('logout/key revocation/session close before response commit retain completing; second real tab cannot acquire writer or race active proof while HTTP awaits outside IDB')
  const final=await snapshot();assert.equal(JSON.stringify(final).includes('PRIVATE_'),false)
  const reopen=async()=>{await page.evaluate(async({scope,users})=>{globalThis.users=users;globalThis.scopeA=scope;globalThis.session=await c21.openBrowserPersistence(users[0]);globalThis.meta=await c21.metadataFixture(session,scope)},{scope,users});await bind();await installRoute()}
  page=await reopenProfile();await reopen();assert.deepEqual(await snapshot(),final);assert.deepEqual(await remote(await read(main.project_id)),active)
  const checkpoint=await page.evaluate(scope=>session.sync.readCheckpoint(scope),scope);assert.equal(checkpoint.ack_cursor,0);assert.equal(checkpoint.proven_prefix,0)
  assert.equal(await page.evaluate(()=>typeof completion.markReady),'undefined')
  cases.push('completing/authoritative active/frozen maxima survive full disk-profile reopen; no plaintext request/storage, no ACK/proven/ready/protected apply or other-family activation')
  return page
}
