/** C21.1.11 production runtime, actual auth/crypto/IDB/Web Locks, disposable profile only. */
import assert from 'node:assert/strict'
export async function acceptInitialNotes({ page, scope, users, cases, expectCode, tab, reopenProfile }) {
  const at = '2026-10-13T00:00:00.000000Z'
  const project = id => ({ id, name: 'PRIVATE_COHORT_PROJECT_SENTINEL', goal: null, infinite: true, unit: 'symbols', status: 'active', created_at: null, updated_at: null, payload: {} })
  const note = (id, project_id) => ({ id, project_id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', title: 'PRIVATE_COHORT_TITLE_SENTINEL', content: '<b>PRIVATE_COHORT_BODY_SENTINEL</b>', checklist: [{ id: 'item', text: 'private checklist', checked: false }], color: 'default', pinned: true, archived: false, sort_order: 0, tags: ['tag'], created_at: at, updated_at: at, metadata: { nullable: null, nested: [true, 1] }, revision: 7 })
  const bind = async () => page.evaluate(() => { globalThis.initial = session.initialNotes.bind(meta.auth,meta.bindings,meta.keys); globalThis.local = session.localSource.bind(meta.auth,meta.bindings,meta.keys) })
  await bind()
  const initialize = async (id, ids) => page.evaluate(async ({ scope, project, notes }) => {
    await local.initializeProject(scope,{project,notes:notes.map(note => ({state:'live',note}))})
    const prepared = await session.projects.prepare(scope,{project_id:project.id,mode:'upload_existing'})
    return session.projects.confirmRegistration(scope,prepared,{remote_state:'initializing',remote_high_water:0})
  }, {scope,project:project(id),notes:ids.map(i => note(i,id))})
  const out = () => page.evaluate(() => nativeRows('outbox'))
  const durable = () => page.evaluate(async () => Object.fromEntries(await Promise.all(['outbox','inbox','cursors','receipts','projectBindings','localProjects','localNotes','ownerHeads'].map(async store => [store,await nativeRows(store)]))))
  const store = async (name, action, value) => page.evaluate(async ({ name, action, value }) => {
    const db = await new Promise((resolve,reject) => { const r=indexedDB.open(c21.WEB_DATABASE_NAME);r.onsuccess=()=>resolve(r.result);r.onerror=reject })
    try { await c21.runBrowserTransaction(db,[name],'readwrite',(tx,result)=>{tx.objectStore(name)[action](value);result(undefined)}) } finally { db.close() }
  }, {name,action,value})
  const before = await durable()
  const registered = await initialize('initial-note-project',['z-cohort','a-cohort','deleted-cohort'])
  await page.evaluate(async ({scope,id,at}) => { await local.tombstoneNote(scope,(await local.readSnapshot(scope,id)).token,'deleted-cohort',at) },{scope,id:registered.project_id,at})
  await page.evaluate(async ({scope,registered}) => {globalThis.registeredInitial=registered;globalThis.initialPlan=await initial.prepare(scope,registered)}, {scope,registered})
  const success = await page.evaluate(scope=>initial.commit(scope,initialPlan),scope), captured=success.binding
  assert.equal(success.status,'captured');assert.equal(captured.phase,'captured');assert.equal(captured.initial_event_count,2);assert.equal(captured.initial_max_server_sequence,null)
  const all=await out(), cohort=all.filter(r=>r.local_ordinal>=captured.initial_local_ordinal_hi-1&&r.local_ordinal<=captured.initial_local_ordinal_hi).sort((a,b)=>a.local_ordinal-b.local_ordinal)
  assert.equal(cohort.length,2);assert.deepEqual(cohort.map(r=>JSON.parse(r.raw_body).items[0].event.entity_id),['a-cohort','z-cohort']);assert.deepEqual(cohort.map(r=>r.local_ordinal),[captured.initial_local_ordinal_hi-1,captured.initial_local_ordinal_hi])
  assert.deepEqual(all.filter(r=>!cohort.some(c=>c.event_id===r.event_id)),before.outbox)
  const opened = await page.evaluate(async ({scope,rows}) => {
    const lease=meta.keys.leaseForAccount(scope.accountId)
    return lease.use(async amk=>{const result=[];for(const row of rows){const item=JSON.parse(row.raw_body).items[0];const nonce=c21.decodeBase64Url(item.object.nonce),ciphertext=c21.decodeBase64Url(item.object.ciphertext);try{result.push(await c21.openNoteSyncEvent(amk,scope.canonicalUserId,item.event,{crypto_version:1,aad_version:1,nonce,ciphertext}))}finally{nonce.fill(0);ciphertext.fill(0)}}return result})
  },{scope,rows:cohort})
  assert.deepEqual(opened.map(v=>v.note),['a-cohort','z-cohort'].map(id=>{const {revision,...n}=note(id,registered.project_id);return n}));assert.equal(opened.every(p=>p.mutation==='create'&&p.header.parent_event_id===null&&p.header.revision===1),true)
  cases.push('real atomic registered/initializing Legacy Note capture: complete live-only source, stable ID ordering, contiguous ordinals, exact count/HI and frozen reader roundtrip of all native fields')
  let status=await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured})
  assert.deepEqual(status,{event_count:2,accepted_count:0,complete:false,max_server_sequence:0})
  const accept=async (row,sequence)=>page.evaluate(({scope,row,sequence})=>session.sync.commitUploadAcceptance(scope,row,{protocol_version:row.protocol_version,encrypted_sync_version:row.protocol_version,current_cursor:sequence,results:[{event_id:row.event_id,server_sequence:sequence,duplicate:false}]}),{scope,row,sequence})
  await accept(cohort[0],101);status=await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured});assert.deepEqual(status,{event_count:2,accepted_count:1,complete:false,max_server_sequence:101})
  await accept(cohort[1],99);status=await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured});assert.deepEqual(status,{event_count:2,accepted_count:2,complete:true,max_server_sequence:101})
  assert.equal((await page.evaluate(()=>nativeRows('projectBindings'))).find(r=>r.project_id===captured.project_id).initial_max_server_sequence,null)
  cases.push('read-only exact cohort status joins immutable normal upload receipts: zero/partial/all counts and max sequence; no completing/initial_max persistence')
  const sameProjectExtra=JSON.parse(cohort[0].raw_body);sameProjectExtra.items[0].event.event_id=crypto.randomUUID();sameProjectExtra.items[0].event.entity_id='unrelated-later-note'
  const later=(await page.evaluate(({scope,raw})=>session.sync.enqueue(scope,[raw]),{scope,raw:JSON.stringify(sameProjectExtra)}))[0].item;await accept(later,102)
  assert.deepEqual(await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured}),status)
  cases.push('pre-existing account outbox and post-capture same-project unrelated receipt excluded by exact interval; no prefix-only cohort inference')
  const originalCohort=cohort.map(r=>r.raw_body)
  await page.evaluate(async ({scope,id,at,note})=>{await local.updateNote(scope,(await local.readSnapshot(scope,id)).token,'a-cohort',{title:'POST_CAPTURE_PRIVATE'},at);await local.createNote(scope,(await local.readSnapshot(scope,id)).token,note)}, {scope,id:registered.project_id,at,note:{...note('post-capture-note',registered.project_id),revision:0}})
  const afterMutation=await durable();assert.equal((await page.evaluate(scope=>initial.commit(scope,initialPlan),scope)).status,'already_captured');assert.equal((await page.evaluate(({scope,registered})=>initial.capture(scope,registered),{scope,registered})).status,'already_captured');assert.deepEqual(await durable(),afterMutation)
  assert.deepEqual((await out()).filter(r=>cohort.some(c=>c.event_id===r.event_id)).sort((a,b)=>a.local_ordinal-b.local_ordinal).map(r=>r.raw_body),originalCohort)
  cases.push('successful exact replay never reads current source/allocates new ordinals; later local create/update cannot recapture or rewrite initial sealed bytes')
  const stale=await initialize('stale-source-project',['stale-source-note'])
  await page.evaluate(async ({scope,binding,at})=>{globalThis.staleSourcePlan=await initial.prepare(scope,binding);await local.updateNote(scope,(await local.readSnapshot(scope,binding.project_id)).token,'stale-source-note',{content:'STALE_PRIVATE'},at)},{scope,binding:stale,at})
  const staleSaved=await durable();await expectCode(page,'initial.commit(scopeA,staleSourcePlan)','stale_source');assert.deepEqual(await durable(),staleSaved)
  assert.equal((await page.evaluate(({scope,binding})=>initial.capture(scope,binding),{scope,binding:stale})).status,'captured')
  cases.push('mutation after crypto preparation rejects source CAS in commit with zero rows/allocator/binding changes; fresh snapshot retry succeeds')
  const rollback=await initialize('rollback-cohort-project',['rollback-a','rollback-z'])
  for(const mode of ['quota','abort','constraint','keylock','logout','close']){
    await page.evaluate(async ({scope,binding})=>{globalThis.rollbackPlan=await initial.prepare(scope,binding)},{scope,binding:rollback})
    const saved=await durable()
    const code=await page.evaluate(async mode=>{
      const add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put;let firstOrdinal
      IDBObjectStore.prototype.add=function(value,...args){if(this.name==='outbox'&&mode==='constraint'){if(firstOrdinal===undefined)firstOrdinal=value.local_ordinal;else value={...value,local_ordinal:firstOrdinal}}const r=add.call(this,value,...args);if(this.name==='outbox')r.addEventListener('success',()=>{if(mode==='abort')this.transaction.abort();else if(mode==='keylock')void meta.keys.lock();else if(mode==='logout')void meta.auth.logout();else if(mode==='close')void session.close()},{once:true});return r}
      IDBObjectStore.prototype.put=function(value,...args){if(this.name==='projectBindings'&&mode==='quota')throw new DOMException('fixture','QuotaExceededError');return put.call(this,value,...args)}
      try{await initial.commit(scopeA,rollbackPlan);return 'unexpected_success'}catch(e){return e.code}finally{IDBObjectStore.prototype.add=add;IDBObjectStore.prototype.put=put}
    },mode)
    assert.equal(code,mode==='quota'?'quota_exceeded':['keylock','logout','close'].includes(mode)?'closed':'storage_failed');assert.deepEqual(await durable(),saved)
    if(mode==='close')await page.evaluate(async()=>{globalThis.session=await c21.openBrowserPersistence(users[0])})
    if(['keylock','logout','close'].includes(mode)){await page.evaluate(async scope=>{await meta.keys.dispose();globalThis.meta=await c21.metadataFixture(session,scope)},scope);await bind()}
  }
  assert.equal((await page.evaluate(({scope,binding})=>initial.capture(scope,binding),{scope,binding:rollback})).status,'captured')
  cases.push('real quota after queued cohort/allocator writes, request abort, async ordinal constraint, key lock, logout and close roll back ALL capture state; fresh retry succeeds')
  const changed=await initialize('changed-lineage-project',['changed-lineage-note'])
  await page.evaluate(async ({scope,binding})=>{globalThis.changedPlan=await initial.prepare(scope,binding);await session.projects.confirmRegistration(scope,binding,{remote_state:'initializing',remote_high_water:1})},{scope,binding:changed})
  const changedSaved=await durable();await expectCode(page,'initial.commit(scopeA,changedPlan)','stale_lineage');assert.deepEqual(await durable(),changedSaved)
  cases.push('full expected-old projectBinding CAS refuses concurrent registration evidence change atomically')
  const collide=await initialize('collision-cohort-project',['collision-a','collision-z'])
  await page.evaluate(async ({scope,binding})=>{const uuid=crypto.randomUUID.bind(crypto),id=uuid();crypto.randomUUID=()=>id;try{globalThis.collisionPlan=await initial.prepare(scope,binding)}finally{crypto.randomUUID=uuid}},{scope,binding:collide})
  const collisionSaved=await durable();await expectCode(page,'initial.commit(scopeA,collisionPlan)','conflicting_record');assert.deepEqual(await durable(),collisionSaved)
  await expectCode(page,'initial.commit(scopeA,{})','conflicting_record')
  cases.push('duplicate frozen event UUIDs and forged plan DTO refuse capture without partial outbox or counters')
  const empty=await initialize('empty-cohort-project',[]),allocatorBefore=await page.evaluate(()=>nativeRows('cursors'))
  const emptyCapture=await page.evaluate(({scope,binding})=>initial.capture(scope,binding),{scope,binding:empty});assert.equal(emptyCapture.binding.initial_event_count,0);assert.equal(emptyCapture.binding.initial_local_ordinal_hi,0);assert.deepEqual(await page.evaluate(()=>nativeRows('cursors')),allocatorBefore)
  assert.deepEqual(await page.evaluate(({scope,binding})=>initial.readStatus(scope,binding),{scope,binding:emptyCapture.binding}),{event_count:0,accepted_count:0,complete:true,max_server_sequence:0})
  cases.push('empty-project capture after pre-existing outbox uses native count0/hi0 and complete true/max0; no invented ordinal/allocator change')
  const savedReceipt=(await page.evaluate(()=>nativeRows('receipts'))).find(r=>r.event_id===cohort[0].event_id)
  await store('receipts','delete',[scope.accountId,savedReceipt.event_id]);await expectCode(page,`initial.readStatus(scopeA,${JSON.stringify(captured)})`,'corrupt_record');await store('receipts','add',savedReceipt)
  await store('receipts','put',{...savedReceipt,device_id:scope.canonicalUserId});await expectCode(page,`initial.readStatus(scopeA,${JSON.stringify(captured)})`,'corrupt_record');await store('receipts','put',savedReceipt)
  cases.push('missing accepted receipt or conflicting receipt device fails closed without fake acceptance/completion or repair')
  const final=await durable();assert.equal(JSON.stringify(final).includes('PRIVATE_'),false);const checkpoint=await page.evaluate(scope=>session.sync.readCheckpoint(scope),scope);assert.equal(checkpoint.ack_cursor,0);assert.equal(checkpoint.proven_prefix,0)
  assert.deepEqual(final.inbox,before.inbox);assert.deepEqual(final.ownerHeads,before.ownerHeads)
  const finalStatus=await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured})
  const reopen=async()=>page.evaluate(async ({scope,users})=>{globalThis.users=users;globalThis.scopeA=scope;globalThis.session=await c21.openBrowserPersistence(users[0]);globalThis.meta=await c21.metadataFixture(session,scope);globalThis.initial=session.initialNotes.bind(meta.auth,meta.bindings,meta.keys)}, {scope,users})
  await page.reload();await reopen();assert.deepEqual(await durable(),final);assert.deepEqual(await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured}),finalStatus);assert.equal((await page.evaluate(({scope,registered})=>initial.capture(scope,registered),{scope,registered})).status,'already_captured')
  page=await reopenProfile();await reopen();assert.deepEqual(await durable(),final);assert.deepEqual(await page.evaluate(({scope,captured})=>initial.readStatus(scope,captured),{scope,captured}),finalStatus)
  cases.push('same immutable cohort and read-only receipt proof survive renderer reload and full disk-profile reopen; original registered request replays exactly')
  let competing=await tab();await expectCode(competing,'c21.openBrowserPersistence(users[0])','writer_busy');await page.close();page=competing;await reopen();assert.deepEqual(await durable(),final)
  await page.evaluate(async()=>{globalThis.staleInitial=initial;await session.resetForLogout()});await expectCode(page,`staleInitial.readStatus(scopeA,${JSON.stringify(captured)})`,'closed');await reopen();assert.deepEqual(await durable(),final)
  cases.push('cohort writer follows native Web Locks exclusion/termination transfer and stale logout session rejection without erasing receipts')
  cases.push('encrypted capture persists no manuscript/title/project plaintext; ACK/proven0, Metadata protected apply/inbox unchanged, no completing/ready/network activation')
  return page
}
