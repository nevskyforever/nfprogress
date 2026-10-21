import assert from 'node:assert/strict'
import {runMixedPrefixCase,checkMixedPrefixBarrier} from './browser-mixed-prefix-cases.mjs'
import {runMixedRecoveryCase} from './browser-mixed-recovery-cases.mjs'
/** P extends the O disk profiles with real interleaved H/O source outcomes. */
export async function runMixedContinuationCase({getPage,snapshot,restart,rebind,compete,send,protocol,strategy,prefixMode=false,recoveryMode=false}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg),id=`note-${protocol}`,deleted=strategy==='delete'
 const totals={hApplied:0,hPreserved:0,hReplays:0,hRollback:0,hRaces:0,hRevoked:0,hBarriers:0,hRestarts:0,hTabs:0,oInterleaved:0}
 const reject=async(fn,arg)=>{assert.equal(await evaluate(async({code,arg})=>{try{await(0,eval)(code)(arg);return false}catch{return true}},{code:fn.toString(),arg}),true);totals.hBarriers++}
 const applyH=async row=>{assert.equal(await evaluate(seq=>continuation.apply(s,seq),row.sequence),'applied');totals.hApplied++}
 const frozen=await snapshot()
 const legacy=await send({id,protocol:2,deleted});await applyH(legacy)
 const ordinary=await send({id:'p-between',protocol:3,create:true,plain:true});assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),ordinary.sequence),'applied');totals.oInterleaved++
 const content=await send({id,protocol:3,compressed:true,deleted});await applyH(content)
 if(strategy==='keep_both'){
  const retained=await send({id:`clone-${protocol}`,protocol:3,compressed:false,deleted:true});await applyH(retained)
 }
 const oUpdate=await send({id:'p-between',protocol:3,compressed:true});assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),oUpdate.sequence),'applied');totals.oInterleaved++
 // Inbox drift makes an already prepared source plan stale. No skip-ahead.
 const pendingH=await send({id,protocol:3,deleted,compressed:false})
 await evaluate(async seq=>{globalThis.hPlan=await continuation.prepare(s,seq)},pendingH.sequence)
 const pendingO=await send({id:'p-racing',protocol:2,create:true}),beforeRace=await snapshot()
 await reject(()=>continuation.commit(hPlan));totals.hRaces++;assert.deepEqual(await snapshot(),beforeRace)
 await reject(seq=>ordinaryOwner.apply(s,seq),pendingO.sequence)
 await applyH(pendingH);assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),pendingO.sequence),'applied');totals.oInterleaved++
 // Competing genuine H owners change the actual source once, never twice.
 const raced=await send({id,protocol:3,deleted,compressed:true})
 await evaluate(async seq=>{
  globalThis.hPlan=await continuation.prepare(s,seq)
  const other=c21.resolutionContinuationFixture(session,meta,verifiedDevice);await other.apply(s,seq)
 },raced.sequence);totals.hApplied++
 const sourceRaced=await snapshot();await reject(()=>continuation.commit(hPlan));totals.hRaces++;assert.deepEqual(await snapshot(),sourceRaced)
 const aborting=await send({id,protocol:2,deleted}),preAbort=await snapshot()
 assert.equal(await evaluate(async seq=>{
  const p=await continuation.prepare(s,seq),put=IDBObjectStore.prototype.put;let injected=false,rejected=false
  IDBObjectStore.prototype.put=function(value,...rest){const request=put.call(this,value,...rest);if(this.name==='localNotes'){injected=true;request.addEventListener('success',()=>this.transaction.abort(),{once:true})}return request}
  try{await continuation.commit(p)}catch{rejected=true}finally{IDBObjectStore.prototype.put=put}
  return injected&&rejected
 },aborting.sequence),true);totals.hRollback++;assert.deepEqual(await snapshot(),preAbort)
 await evaluate(async seq=>{globalThis.hPlan=await continuation.prepare(s,seq)},aborting.sequence)
 await restart();totals.hRestarts++;assert.deepEqual(await snapshot(),preAbort)
 await reject(()=>continuation.commit({}));await applyH(aborting)
 const revocable=await send({id,protocol:3,compressed:true,deleted}),beforeRevoke=await snapshot()
 await evaluate(async({seq,strategy})=>{
  globalThis.hPlan=await continuation.prepare(s,seq)
  if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')
 },{seq:revocable.sequence,strategy})
 await reject(()=>continuation.commit(hPlan));totals.hRevoked++;assert.deepEqual(await snapshot(),beforeRevoke)
 await rebind();await applyH(revocable)
 const positive=await snapshot();assert.equal(positive.cursors[0].proven_prefix,frozen.cursors[0].proven_prefix);await restart();totals.hRestarts++;assert.deepEqual(await snapshot(),positive)
 assert.deepEqual(await evaluate(async()=>{
  const transaction=IDBDatabase.prototype.transaction,random=crypto.getRandomValues
  IDBDatabase.prototype.transaction=function(stores,mode,...rest){if(mode==='readwrite')throw Error('N_WRITE');return transaction.call(this,stores,mode,...rest)}
  crypto.getRandomValues=()=>{throw Error('N_NONCE')}
  try{const n=await witness.inspect(s);return{read:n.readOnly,commit:n.commitAuthorized,ack:n.ackAuthorized,ready:n.ready}}
  finally{IDBDatabase.prototype.transaction=transaction;crypto.getRandomValues=random}
 }),{read:true,commit:false,ack:false,ready:false})
 assert.equal(await evaluate(seq=>continuation.reconcile(s,seq),legacy.sequence),'already_applied');totals.hReplays++
 assert.equal(await evaluate(async row=>(await transport.replayInboundPage(s,row.since,row.rawPage)).new_events,revocable),0);totals.hReplays++
 await reject(()=>prefix.prepare(s));await reject(()=>recovery.run(s));assert.deepEqual(await snapshot(),positive)
 await compete();totals.hTabs++
 // Keep every original wire/proof and immutable record, including F evidence.
 for(const old of frozen.inbox)assert.deepEqual(positive.inbox.find(r=>r.event_id===old.event_id),old)
 for(const old of frozen.legacyNoteHistory.filter(r=>r.record_kind!=='head'))assert.deepEqual(positive.legacyNoteHistory.find(r=>r.project_id===old.project_id&&r.note_id===old.note_id&&r.record_kind===old.record_kind&&r.record_id===old.record_id),old)
 assert.deepEqual(positive.localNotes.find(n=>n.note_id==='baseline-deleted'),frozen.localNotes.find(n=>n.note_id==='baseline-deleted'))
 for(const name of ['outbox','receipts','ownerHeads','projectBindings','legacyNoteIntents'])assert.deepEqual(positive[name],frozen[name])
 const q=prefixMode?await runMixedPrefixCase({getPage,snapshot,restart,rebind,send,strategy}):null
 const k=recoveryMode?await runMixedRecoveryCase({getPage,snapshot,restart,rebind,compete,send,protocol,strategy}):null
 const forkBasis=k?.lastH??revocable
 // Fork siblings join the last applied parent's role, with NO source mutation.
 for(let n=0;n<2;n++){
  const sibling=await send({id,protocol:n?3:2,compressed:true,deleted,parent:forkBasis.parent_event_id,revision:forkBasis.revision})
  const before=await snapshot()
  if(recoveryMode&&n===0){
   const r=await evaluate(()=>mixedRecovery.run(s));assert.deepEqual(r.applied,[{sequence:sibling.sequence,route:'continuation',status:'conflict_preserved'}]);assert.equal(r.blocker.sequence,sibling.sequence);assert.equal(r.blocker.kind,'unresolved_fork');assert.equal(r.prefix.candidate_proven_prefix,before.cursors[0].proven_prefix)
  }else assert.equal(await evaluate(seq=>continuation.apply(s,seq),sibling.sequence),'conflict_preserved')
  if(recoveryMode&&n!==0){const r=await evaluate(()=>mixedRecovery.run(s));assert.deepEqual(r.applied,[]);assert.equal(r.blocker.kind,'unresolved_fork')}
  totals.hPreserved++
  const after=await snapshot();assert.deepEqual(after.localProjects,before.localProjects);assert.deepEqual(after.localNotes,before.localNotes)
  assert.equal(after.legacyNoteHistory.find(c=>c.record_kind==='candidate'&&c.event_id===sibling.event_id).projection,null)
  for(const name of ['cursors','outbox','receipts','ownerHeads','projectBindings','legacyNoteIntents'])assert.deepEqual(after[name],before[name])
  assert.equal(await evaluate(seq=>continuation.reconcile(s,seq),sibling.sequence),'already_applied');totals.hReplays++
 }
 const open=await snapshot();assert.equal(await evaluate(async()=>(await continuation.history(s)).readOnly),true)
 await reject(()=>witness.inspect(s));await reject(seq=>ordinaryOwner.reconcile(s,seq),ordinary.sequence)
 await reject(()=>prefix.prepare(s));await reject(()=>recovery.run(s));assert.deepEqual(await snapshot(),open)
 if(q)q.qForkBarriers=await checkMixedPrefixBarrier({getPage,snapshot})
 await restart();totals.hRestarts++;assert.deepEqual(await snapshot(),open)
 if(recoveryMode){const r=await evaluate(()=>mixedRecovery.run(s));assert.deepEqual(r.applied,[]);assert.equal(r.blocker.kind,'unresolved_fork');assert.deepEqual(await snapshot(),open)}
 assert.equal(await evaluate(async()=>(await continuation.history(s)).readOnly),true)
 await reject(()=>witness.inspect(s));await reject(()=>prefix.prepare(s))
 if(q)q.qForkBarriers+=await checkMixedPrefixBarrier({getPage,snapshot})
 if(strategy==='keep_both'){
  const retained=await send({id:`clone-${protocol}`,protocol:3,deleted:true}),pending=await snapshot()
  await reject(seq=>continuation.apply(s,seq),retained.sequence);assert.deepEqual(await snapshot(),pending)
 }
 return{...totals,q,k}
}
