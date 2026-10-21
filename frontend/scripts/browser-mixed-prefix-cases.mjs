import assert from 'node:assert/strict'
/** Q adds local-prefix checks to the existing genuine O/P disk profiles. */
export async function runMixedPrefixCase({getPage,snapshot,restart,rebind,send,strategy}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg)
 const bind=()=>evaluate(()=>{globalThis.qPrefix=c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice)})
 const prepare=()=>evaluate(async()=>{globalThis.qPlan=await qPrefix.prepareCommit(await qPrefix.prepare(s))})
 const reject=async()=>assert.equal(await evaluate(async()=>{try{await qPrefix.commit(qPlan);return false}catch{return true}}),true)
 await bind();await prepare()
 // Real O history/source changes invalidate the prepared full-inventory CAS.
 const o=await send({id:'q-independent',protocol:3,compressed:true,create:true})
 assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),o.sequence),'applied')
 const before=await snapshot();await reject();assert.deepEqual(await snapshot(),before)
 await prepare()
 assert.equal(await evaluate(async()=>{
  const put=IDBObjectStore.prototype.put;let injected=false,rejected=false
  IDBObjectStore.prototype.put=function(value,...args){const r=put.call(this,value,...args);if(this.name==='cursors'){injected=true;r.addEventListener('success',()=>this.transaction.abort(),{once:true})}return r}
  try{await qPrefix.commit(qPlan)}catch{rejected=true}finally{IDBObjectStore.prototype.put=put}
  return injected&&rejected
 }),true);assert.deepEqual(await snapshot(),before)
 await prepare()
 await evaluate(async strategy=>{if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')},strategy)
 await reject();assert.deepEqual(await snapshot(),before);await rebind()
 await bind();await prepare();await restart();assert.deepEqual(await snapshot(),before)
 assert.equal(await evaluate(()=>typeof qPlan==='undefined'),true);await bind()
 assert.equal(await evaluate(async()=>{try{await qPrefix.commit({});return false}catch{return true}}),true)
 await prepare()
 const current=getPage(),tab=await current.context().newPage()
 try{
  await tab.goto(current.url());const s=await evaluate(()=>s)
  assert.equal(await tab.evaluate(async s=>{try{await c21.openBrowserPersistence(s.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},s),true)
 }finally{await tab.close()}
 assert.deepEqual(await snapshot(),before)
 // A second actual G runtime is still subject to native atomic inventory CAS.
 assert.equal(await evaluate(async()=>{const q=c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice);return q.commit(await q.prepareCommit(await q.prepare(s)))}),'advanced')
 assert.equal(await evaluate(()=>qPrefix.commit(qPlan)),'already_proven')
 const expected=structuredClone(before);expected.cursors[0].proven_prefix=o.sequence
 assert.deepEqual(await snapshot(),expected)
 assert.deepEqual(await evaluate(async()=>{const r=await qPrefix.calculate(await qPrefix.prepare(s));return{prefix:r.candidate_proven_prefix,blocking:r.first_blocking_sequence,ack:r.ackAuthorized,read:r.readOnly}}),{prefix:o.sequence,blocking:null,ack:false,read:true})
 assert.equal(await evaluate(async row=>(await transport.replayInboundPage(s,row.since,row.rawPage)).new_events,o),0)
 assert.deepEqual(await snapshot(),expected)
 return{qAdvanced:1,qRaces:1,qRollback:1,qRevoked:1,qRestarts:1,qTabs:1,qReplay:1,qOrdinary:1}
}
export async function checkMixedPrefixBarrier({getPage,snapshot}){
 const before=await snapshot()
 const expected=before.inbox.filter(r=>['note_conflict_preserved','content_note_conflict_preserved'].includes(r.state)).sort((a,b)=>a.server_sequence-b.server_sequence).find(r=>r.server_sequence>before.cursors[0].proven_prefix)
 assert.ok(expected)
 assert.deepEqual(await getPage().evaluate(async()=>{
  const q=c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice),token=await q.prepare(s),r=await q.calculate(token)
  return{prefix:r.candidate_proven_prefix,blocking:r.first_blocking_sequence,blocker:r.blocker,ack:r.ackAuthorized,result:await q.commit(await q.prepareCommit(token))}
 }),{prefix:before.cursors[0].proven_prefix,blocking:expected.server_sequence,blocker:'unproven_family',ack:false,result:'no_progress'})
 assert.deepEqual(await snapshot(),before)
 return 1
}
