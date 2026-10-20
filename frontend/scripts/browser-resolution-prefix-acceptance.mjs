import assert from 'node:assert/strict'
import {runResolutionContinuationAcceptance} from './browser-resolution-continuation-acceptance.mjs'
import {pathToFileURL} from 'node:url'
export async function runResolutionPrefixAcceptance(onVerified){
let cases=0,calculations=0,commits=0,rollbacks=0,restarts=0,casRejects=0,gaps=0,forkBarriers=0,readOnlyWrites=0,competingTabs=0,identityRejects=0
await runResolutionContinuationAcceptance(async c=>{
 const {scope,decisions,progressed,descendants}=c
 const fork=descendants.find(d=>d.conflict),target=fork?fork.sequence-1:progressed.cursors[0].pull_cursor
 // Full fresh-key native historical authentication and isolated calculation must
 // not attempt any write. All positive records came from the accepted F/H runner.
 const calculated=await c.page.evaluate(async()=>{
  const transaction=IDBDatabase.prototype.transaction,add=IDBObjectStore.prototype.add,put=IDBObjectStore.prototype.put,del=IDBObjectStore.prototype.delete,clear=IDBObjectStore.prototype.clear;let writes=0
  IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('G_READONLY_WRITE')}return transaction.call(this,stores,mode,...args)}
  for(const method of ['add','put','delete','clear'])IDBObjectStore.prototype[method]=()=>{writes++;throw Error('G_READONLY_WRITE')}
  try{globalThis.gCertificate=await prefix.prepare(s);return{value:await prefix.calculate(gCertificate),writes}}
  finally{IDBDatabase.prototype.transaction=transaction;Object.assign(IDBObjectStore.prototype,{add,put,delete:del,clear})}
 })
 assert.equal(calculated.writes,0);readOnlyWrites+=calculated.writes;calculations++
 assert.equal(calculated.value.candidate_proven_prefix,target);assert.equal(calculated.value.counts.resolution,1)
 assert.equal(calculated.value.ackAuthorized,false)
 if(fork){assert.equal(calculated.value.first_blocking_sequence,fork.sequence);forkBarriers++}
 else assert.equal(calculated.value.first_blocking_sequence,null)
 assert.deepEqual(await c.snapshot(),progressed)
 // Negative-only native edits are restored byte-for-byte; no positive candidate,
 // head, proof or closure is ever constructed directly in IndexedDB.
 const raw=async(store,method,value)=>c.page.evaluate(async({store,method,value})=>{
  const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((r,j)=>{q.onsuccess=()=>r(q.result);q.onerror=()=>j(q.error)})
  try{await c21.runBrowserTransaction(db,[store],'readwrite',(tx,result)=>{tx.objectStore(store)[method](value);result(undefined)})}finally{db.close()}
 },{store,method,value})
 const metaRow=progressed.inbox.find(r=>JSON.parse(r.wire_item).event.entity_type==='project_metadata')
 await raw('inbox','delete',[scope.accountId,metaRow.server_sequence]);const missing=await c.snapshot()
 const blocked=await c.page.evaluate(async()=>{try{const token=await prefix.prepare(s),r=await prefix.calculate(token);return r.candidate_proven_prefix===0&&r.first_blocking_sequence===1}catch{return true}})
 assert.equal(blocked,true);assert.deepEqual(await c.snapshot(),missing);gaps++
 await raw('inbox','put',metaRow);assert.deepEqual(await c.snapshot(),progressed)
 // A previously minted token cannot survive a dependency change, even with the
 // same cursors. Exercise the actual native full-inventory CAS.
 await c.page.evaluate(async()=>{globalThis.gCommit=await prefix.prepareCommit(await prefix.prepare(s))})
 const owner=progressed.ownerHeads[0];await raw('ownerHeads','put',{...owner,head_revision:owner.head_revision+1})
 const stale=await c.snapshot()
 assert.equal(await c.page.evaluate(async()=>{try{await prefix.commit(gCommit);return false}catch{return true}}),true)
 assert.deepEqual(await c.snapshot(),stale);casRejects++;await raw('ownerHeads','put',owner)
 if(decisions.protocol===3&&decisions.strategy==='choose_version'){
  const competing=await c.page.context().newPage();await competing.goto(c.page.url())
  try{assert.equal(await competing.evaluate(async scope=>{try{await c21.openBrowserPersistence(scope.canonicalUserId);return false}catch(e){return e.code==='writer_busy'}},scope),true);competingTabs++}finally{await competing.close()}
  const identity=progressed.identities[0]
  await raw('identities','put',{...identity,device_id:crypto.randomUUID()});const changed=await c.snapshot()
  assert.equal(await c.page.evaluate(async()=>{try{await prefix.commit(gCommit);return false}catch{return true}}),true)
  assert.deepEqual(await c.snapshot(),changed);identityRejects++;await raw('identities','put',identity)
 }
 if(decisions.strategy==='keep_both'){
  for(let fault=0;fault<5;fault++){
   const before=await c.snapshot()
   const failed=await c.page.evaluate(async fault=>{
    const token=await prefix.prepareCommit(await prefix.prepare(s)),put=IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put=function(...args){
     if(this.name!=='cursors')throw Error('G_FORBIDDEN_WRITE')
     const request=put.apply(this,args)
     if(fault===0)throw new DOMException('G_CURSOR_QUOTA','QuotaExceededError')
     request.addEventListener('success',()=>{if(fault===1)request.transaction.abort();else if(fault===2)void meta.keys.lock();else if(fault===3)void meta.auth.logout();else void session.close()},{once:true})
     return request
    }
    try{await prefix.commit(token);return false}catch{return true}finally{IDBObjectStore.prototype.put=put}
   },fault)
   assert.equal(failed,true);assert.deepEqual(await c.snapshot(),before);rollbacks++
   if(fault>=2){await c.page.evaluate(async()=>{await meta.keys.dispose();await session.close()});await c.bind()}
  }
 }
 const before=await c.snapshot()
 const status=await c.page.evaluate(async()=>{
  globalThis.gCommit=await prefix.prepareCommit(await prefix.prepare(s))
  return{first:await prefix.commit(gCommit),retry:await prefix.commit(gCommit)}
 })
 assert.equal(status.first,'advanced');assert.equal(status.retry,'already_proven');commits++
 const expected=structuredClone(before);expected.cursors[0].proven_prefix=target
 assert.deepEqual(await c.snapshot(),expected)
 // Disk restart at a POSITIVE local prefix proves v10 opening/readers/cursor
 // consumers tolerate it without migration, reset, ACK or history rewriting.
 await c.restart();restarts++
 assert.deepEqual(await c.snapshot(),expected)
 const fresh=await c.page.evaluate(async()=>{
  const token=await prefix.prepare(s),r=await prefix.calculate(token),noProgress=await prefix.commit(await prefix.prepareCommit(token))
  const history=await continuation.history(s)
  let oldAckBlocked=false;try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepareAck(s,{})}catch{oldAckBlocked=true}
  return{r,noProgress,history,oldAckBlocked,cursor:await session.sync.readCheckpoint(s)}
 })
 assert.equal(fresh.r.current_proven_prefix,target);assert.equal(fresh.r.candidate_proven_prefix,target);assert.equal(fresh.noProgress,'no_progress')
 assert.equal(fresh.history.resolutions,1);assert.equal(fresh.history.closedGroups,1);assert.equal(fresh.oldAckBlocked,true)
 assert.equal(fresh.cursor.proven_prefix,target);assert.equal(fresh.cursor.ack_cursor,0);assert.equal(fresh.cursor.pull_cursor,before.cursors[0].pull_cursor)
 assert.deepEqual(await c.snapshot(),expected);calculations++;cases++
 if(onVerified)await onVerified(c)
})
console.log(JSON.stringify({result:'PASS',G:'historical-prefix',cases,calculations,commits,idempotentRetries:commits,nativeRollbacks:rollbacks,fullDiskRestarts:restarts,staleInventoryRejects:casRejects,nativeIdentityRejects:identityRejects,competingTabs,missingSequenceBarriers:gaps,independentForkBarriers:forkBarriers,readOnlyWrites,push:0,serverACK:0,pageErrors:0}))
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await runResolutionPrefixAcceptance()
