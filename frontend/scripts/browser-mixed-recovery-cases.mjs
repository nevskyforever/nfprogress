import assert from 'node:assert/strict'
/** .09 reuses the genuine O/P/Q profile and its authenticated source history. */
export async function runMixedRecoveryCase({getPage,snapshot,restart,rebind,compete,send,protocol,strategy}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg),deleted=strategy==='delete'
 const bind=()=>evaluate(()=>{globalThis.mixedRecovery=c21.mixedV10RecoveryFixture(session,meta,verifiedDevice)})
 const run=(options={})=>evaluate(options=>mixedRecovery.run(s,options),options)
 const totals={kApplied:0,kRestarts:0,kRollback:0,kPrefixRecovery:0,kRevoked:0,kTabs:0,kReplay:0,kBounded:0}
 await bind()
 const frozen=await snapshot(),ordinary=await send({id:'k-independent',protocol:2,create:true}),child=await send({id:`note-${protocol}`,protocol:3,compressed:true,deleted})
 let r=await run({maxEvents:1});assert.deepEqual(r.applied,[{sequence:ordinary.sequence,route:'legacy',status:'applied'}]);totals.kApplied++
 assert.equal(r.blocker.sequence,child.sequence);assert.equal(r.blocker.kind,'budget_exhausted');assert.equal(r.prefix.candidate_proven_prefix,ordinary.sequence);totals.kBounded++
 const bounded=await snapshot();await restart();totals.kRestarts++;assert.deepEqual(await snapshot(),bounded);await bind()
 r=await run({replay:{since:child.since,rawPage:child.rawPage}});assert.deepEqual(r.applied,[{sequence:child.sequence,route:'continuation',status:'applied'}]);totals.kApplied++;totals.kReplay++
 assert.equal(r.prefix.candidate_proven_prefix,child.sequence);assert.equal(r.readiness,null)
 for(const row of frozen.inbox)assert.deepEqual((await snapshot()).inbox.find(r=>r.event_id===row.event_id),row)
 for(const options of [{id:'k-independent',protocol:3,compressed:false},{id:'k-independent',protocol:3,compressed:true,deleted:true}]){
  const row=await send(options);r=await run();assert.deepEqual(r.applied,[{sequence:row.sequence,route:'content',status:'applied'}]);totals.kApplied++
 }
 if(strategy==='keep_both'){
  const retained=await send({id:`clone-${protocol}`,protocol:3,compressed:false,deleted:true});r=await run();assert.equal(r.applied[0].sequence,retained.sequence);assert.equal(r.applied[0].route,'continuation');totals.kApplied++
 }
 const aborted=await send({id:'k-rollback',protocol:3,compressed:true,create:true}),beforeAbort=await snapshot()
 assert.equal(await evaluate(async()=>{
  const put=IDBObjectStore.prototype.put;let injected=false,rejected=false
  IDBObjectStore.prototype.put=function(value,...args){const r=put.call(this,value,...args);if(this.name==='localNotes'){injected=true;r.addEventListener('success',()=>this.transaction.abort(),{once:true})}return r}
  try{await mixedRecovery.run(s)}catch{rejected=true}finally{IDBObjectStore.prototype.put=put}
  return injected&&rejected
 }),true);assert.deepEqual(await snapshot(),beforeAbort);totals.kRollback++
 r=await run();assert.equal(r.applied[0].sequence,aborted.sequence);totals.kApplied++
 const pending=await send({id:'k-prefix-recovery',protocol:3,compressed:true,create:true}),beforePrefix=await snapshot()
 assert.equal(await evaluate(async()=>{
  const put=IDBObjectStore.prototype.put;let injected=false,rejected=false
  IDBObjectStore.prototype.put=function(value,...args){const r=put.call(this,value,...args);if(this.name==='cursors'){injected=true;r.addEventListener('success',()=>this.transaction.abort(),{once:true})}return r}
  try{await mixedRecovery.run(s)}catch{rejected=true}finally{IDBObjectStore.prototype.put=put}
  return injected&&rejected
 }),true);totals.kApplied++
 const proven=await snapshot();assert.equal(proven.inbox.find(r=>r.event_id===pending.event_id).state,'content_note_proven');assert.deepEqual(proven.cursors,beforePrefix.cursors)
 await restart();totals.kRestarts++;assert.deepEqual(await snapshot(),proven);await bind()
 r=await run();assert.deepEqual(r.applied,[]);assert.equal(r.prefix.candidate_proven_prefix,pending.sequence);totals.kPrefixRecovery++
 const revoked=await send({id:'k-revoked',protocol:3,compressed:true,create:true}),beforeRevoke=await snapshot()
 await evaluate(async strategy=>{if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')},strategy)
 assert.equal(await evaluate(async()=>{try{await mixedRecovery.run(s);return false}catch{return true}}),true);assert.deepEqual(await snapshot(),beforeRevoke);totals.kRevoked++
 await rebind();await bind();r=await run();assert.equal(r.applied[0].sequence,revoked.sequence);totals.kApplied++
 const stable=await snapshot();await compete();totals.kTabs++;assert.deepEqual(await snapshot(),stable)
 assert.equal(await evaluate(async()=>{try{await recovery.run(s);return false}catch{return true}}),true)
 r=await run({replay:{since:revoked.since,rawPage:revoked.rawPage}});assert.deepEqual(r.applied,[]);assert.equal(r.ready,false);assert.equal(r.ackAuthorized,false);assert.equal(r.declarationAllowed,false);assert.equal(r.readiness,null);totals.kReplay++
 assert.deepEqual(await snapshot(),stable);assert.equal(stable.cursors[0].ack_cursor,frozen.cursors[0].ack_cursor)
 return{...totals,lastH:child}
}
