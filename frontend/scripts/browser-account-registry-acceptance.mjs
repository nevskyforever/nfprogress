/** C21.1.13: actual account-wide IDB transactions, intercepted existing GET only. */
import assert from 'node:assert/strict'
export async function acceptAccountRegistry({page,scope,users,cases,expectCode,tab,reopenProfile}) {
  let mode='ok',cursor=5000,release
  const bind=()=>page.evaluate(()=>{globalThis.registry=session.registry.bind(meta.auth,meta.bindings,meta.keys)})
  const snapshot=()=>page.evaluate(async()=>Object.fromEntries(await Promise.all(['projectBindings','outbox','receipts','cursors','inbox','ownerHeads','localProjects','localNotes'].map(async s=>[s,await nativeRows(s)]))))
  const install=()=>page.route('**/api/**',async route=>{
    const req=route.request();assert.equal(req.method(),'GET');assert.equal(new URL(req.url()).pathname,'/api/v1/cloud/projects/bootstrap');assert.equal(req.headers().authorization,'Bearer fixture-access');assert.equal(req.postData(),null)
    const rows=(await page.evaluate(()=>nativeRows('projectBindings'))).filter(b=>b.account_id===scope.accountId)
    const projects=rows.map(b=>({project_id:b.project_id,bootstrap_id:b.bootstrap_id,origin_device_id:b.mode==='import_remote'?users[3]:b.device_id,state:b.mode==='import_remote'||b.phase==='completing'?'active':'initializing',initial_event_count:b.mode==='import_remote'?0:b.phase==='completing'?b.initial_event_count:null,initial_max_server_sequence:b.mode==='import_remote'?0:b.phase==='completing'?b.initial_max_server_sequence:null}))
    if(mode==='duplicate')projects.push({...projects.at(-1)})
    if(mode==='malformed')projects.at(-1).extra=true
    if(mode==='missing')projects.splice(projects.findIndex(p=>p.project_id==='completion-project'),1)
    if(mode==='bootstrap')projects.find(p=>p.project_id==='completion-project').bootstrap_id=crypto.randomUUID()
    if(mode==='unknown')projects.push({project_id:'unknown-registry-peer',bootstrap_id:crypto.randomUUID(),origin_device_id:users[3],state:'active',initial_event_count:0,initial_max_server_sequence:0})
    if(mode==='race')await page.evaluate(scope=>session.projects.prepare(scope,{project_id:'registry-raced',mode:'upload_existing'}),scope)
    if(mode==='hold')await new Promise(r=>{release=r})
    if(mode==='keylock')await page.evaluate(()=>meta.keys.lock())
    if(mode==='logout'){await page.evaluate(()=>meta.auth.logout());try{await route.abort('failed')}catch{/* Auth invalidation may already abort this intercepted request. */}return}
    if(mode==='close')await page.evaluate(()=>session.close())
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({projects,current_cursor:cursor})})
  })
  const reconcile=()=>page.evaluate(async scope=>{globalThis.registryResult=await registry.reconcile(scope);return {bindings:registryResult.bindings,unknown:registryResult.unknown_projects}},scope)
  const diagnose=()=>page.evaluate(scope=>registry.ackPrerequisites(scope,'completion-project',registryResult.token),scope)
  await page.unroute('**/api/**');await bind();await install()
  const before=await snapshot(),result=await reconcile(),after=await snapshot()
  const complete=result.bindings.find(b=>b.project_id==='completion-project'),imported=result.bindings.find(b=>b.project_id==='imported-project')
  assert.equal(complete.phase,'completing');assert.equal(complete.initial_max_server_sequence,501);assert.equal(complete.remote_high_water,5000);assert.equal(imported.device_id,scope.deviceId);assert.equal(imported.initial_event_count,0);assert.equal(imported.remote_high_water,5000)
  assert.deepEqual({...after,projectBindings:before.projectBindings},before)
  const diagnosis=await diagnose();assert.equal(diagnosis.code,'pull_required');assert.equal(diagnosis.required_cursor,5000);assert.equal(diagnosis.proven_prefix,0);assert.equal(diagnosis.ack_cursor,0);assert.equal(diagnosis.ready,false)
  cases.push('registry existing GET/Bearer and full vector update known upload+peer-origin import atomically; each frozen cohort preserved; account high-water5000 never proves ACK/ready')
  await reconcile();assert.deepEqual(await snapshot(),after)
  cases.push('exact complete-account registry retry byte-stable; read-only prerequisite inventory never changes inbox/history/cursor/receipts/local source')
  for(const [test,code] of [['duplicate','registry_rejected'],['malformed','registry_rejected'],['missing','registry_conflict'],['bootstrap','registry_conflict'],['regression','registry_conflict']]){
    mode=test;cursor=test==='regression'?4999:5000;await expectCode(page,'registry.reconcile(scopeA)',code);assert.deepEqual(await snapshot(),after)
  }
  cases.push('malformed later/duplicate/bootstrap mismatch/missing bound project/regressing account cursor reject entire response without partial writes or deletion')
  mode='unknown';cursor=5000;assert.deepEqual((await reconcile()).unknown,['unknown-registry-peer']);assert.deepEqual(await snapshot(),after);assert.equal((await diagnose()).code,'registry_reconciliation_required')
  cases.push('unknown remote peer is explicit account blocker; never imported or turned into a local source')
  mode='race';await expectCode(page,'registry.reconcile(scopeA)','stale_lineage');const raced=await snapshot();assert.deepEqual({...raced,projectBindings:after.projectBindings},after);assert.deepEqual(raced.projectBindings.filter(b=>b.project_id!=='registry-raced'),after.projectBindings)
  cases.push('binding insertion during HTTP rejects complete old-account-set CAS; retains new binding and every old high-water')
  mode='ok';cursor=6000
  for(const kind of ['abort','quota']){
    const saved=await snapshot();const code=await page.evaluate(async({scope,kind})=>{const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(v,...args){if(this.name==='projectBindings'&&kind==='quota')throw new DOMException('fixture','QuotaExceededError');const r=put.call(this,v,...args);if(this.name==='projectBindings'&&kind==='abort')r.addEventListener('success',()=>this.transaction.abort(),{once:true});return r};try{await registry.reconcile(scope);return'bad'}catch(e){return e.code}finally{IDBObjectStore.prototype.put=put}},{scope,kind});assert.equal(code,kind==='abort'?'storage_failed':'quota_exceeded');assert.deepEqual(await snapshot(),saved)
  }
  cases.push('native IDB abort after request success and quota failure roll back all registry high-waters together')
  for(const test of ['keylock','logout','close']){
    mode=test;const saved=await snapshot();await expectCode(page,'registry.reconcile(scopeA)','closed');assert.deepEqual(await snapshot(),saved)
    if(test==='close')await page.evaluate(async()=>{globalThis.session=await c21.openBrowserPersistence(users[0])})
    await page.evaluate(async scope=>{await meta.keys.dispose();globalThis.meta=await c21.metadataFixture(session,scope)},scope);await bind()
  }
  cases.push('key lock/logout/session close during GET forbid response commit and proof creation')
  mode='hold';const pending=reconcile();while(!release)await new Promise(r=>setTimeout(r,10));const second=await tab();await expectCode(second,'c21.openBrowserPersistence(users[0])','writer_busy');await second.close();release();await pending;mode='ok'
  cases.push('second Chromium tab cannot acquire writer while registry HTTP waits outside IDB')
  const durable=await snapshot();page=await reopenProfile();await page.evaluate(async({scope,users})=>{globalThis.scopeA=scope;globalThis.users=users;globalThis.session=await c21.openBrowserPersistence(users[0]);globalThis.meta=await c21.metadataFixture(session,scope)},{scope,users});await bind();await install();assert.deepEqual(await snapshot(),durable)
  assert.equal((await page.evaluate(scope=>registry.ackPrerequisites(scope,'completion-project'),scope)).code,'registry_reconciliation_required');await reconcile();assert.deepEqual(await snapshot(),durable);assert.equal((await diagnose()).proven_prefix,0)
  cases.push('disk-profile reopen retains per-binding registry projection; complete-account runtime proof expires, explicit refetch required; ACK/proven stay0 and ready false')
  return page
}
