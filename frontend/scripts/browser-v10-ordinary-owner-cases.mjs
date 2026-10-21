import {runMixedContinuationCase} from './browser-mixed-continuation-cases.mjs'
import assert from 'node:assert/strict'
/** O acceptance core; optional P extends the same real-owner disk profiles. */
export async function runOrdinaryOwnerCase({getPage,snapshot,restart,rebind,compete,protocol,strategy,continuationMode=false,prefixMode=false,recoveryMode=false}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg)
 let applied=0,replays=0,rollbacks=0,races=0,revocations=0,barriers=0,restarts=0
 const send=options=>evaluate(async options=>{
  const id=options.id,project='planner-project',stamp='2026-10-21T00:00:00.000000Z',peer='44444444-4444-4444-8444-444444444444',protocol=options.protocol??3,deleted=options.deleted??false
  const rows=await nativeRows('legacyNoteHistory'),head=rows.find(r=>r.record_kind==='head'&&r.project_id===project&&r.note_id===id),parent=Object.hasOwn(options,'parent')?options.parent:options.create?null:head?.linear_head_event_id??null,prior=parent&&(await nativeRows('inbox')).find(r=>r.event_id===parent)
  const revision=options.revision??(parent?JSON.parse(prior.wire_item).event.revision+1:1),header={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null}
  let note={id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:options.plain?'plain':'html',title:'DISPOSABLE_O_NOTE',content:'ACTUAL_ORDINARY_AFTER_F'.repeat(40),checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
  if(parent){
   const local=session.localSource.bind(meta.auth,meta.bindings,meta.keys)
   await local.withDecryptedSnapshot(s,(await local.readSnapshot(s,project)).token,async opened=>{
    const before=opened.notes.find(n=>n.note.id===id);const {revision:_rev,...value}=before.note
    note=before.state==='tombstone'?value:{...value,updated_at:stamp,content:'ACTUAL_ORDINARY_AFTER_F_UPDATE'.repeat(40)}
   })
  }
  if(deleted)note={id,project_id:project,stage_id:note.stage_id,source_type:note.source_type,source_map_id:note.source_map_id,source_node_id:note.source_node_id,content_format:note.content_format,deleted_at:stamp}
  const plaintext=c21.createNoteSyncPlaintext(header,parent,note).plaintext,b=(await nativeRows('projectBindings')).find(b=>b.project_id===project),mh=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project)
  const wrapper={version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:mh.tip_event_ids[0],stage_event_ids:[]},event:plaintext},frame=protocol===2?c21.encodeNoteSyncPlaintext(plaintext):c21.readerFrame({id:8,version:1,event:wrapper},options.compressed??false)
  const cursor=(await nativeRows('cursors'))[0],sequence=cursor.pull_cursor+1,event={event_id:header.event_id,device_id:peer,server_sequence:sequence,project_id:project,entity_id:id,entity_type:'note',operation:protocol===2?header.operation:'event',revision,updated_at:stamp,deleted_at:protocol===2?header.deleted_at:null}
  const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
  const rawPage=JSON.stringify({protocol_version:protocol,encrypted_sync_version:protocol,items:[{event,object}],next_cursor:sequence,has_more:false})
  try{await session.sync.commitInboundPage(s,cursor.pull_cursor,rawPage)}finally{frame.fill(0)}
  return{sequence,event_id:event.event_id,since:cursor.pull_cursor,rawPage,parent_event_id:parent,revision}
 },options)
 const apply=async event=>{assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),event.sequence),'applied');applied++}
 const rejected=async(fn,arg)=>{assert.equal(await evaluate(async({source,arg})=>{try{await(0,eval)(source)(arg);return false}catch{return true}},{source:fn.toString(),arg}),true);barriers++}
 const inspect=async count=>{
  const before=await snapshot()
  assert.deepEqual(await evaluate(async()=>{
   const transaction=IDBDatabase.prototype.transaction,random=crypto.getRandomValues;let writes=0,nonces=0
   IDBDatabase.prototype.transaction=function(stores,mode,...rest){if(mode==='readwrite'){writes++;throw Error('N_WRITE')}return transaction.call(this,stores,mode,...rest)}
   crypto.getRandomValues=()=>{nonces++;throw Error('N_NONCE')}
   try{const result=await witness.inspect(s);return{count:result.ordinaryTransitions,commit:result.commitAuthorized,ready:result.ready,writes,nonces}}
   finally{IDBDatabase.prototype.transaction=transaction;crypto.getRandomValues=random}
  }),{count,commit:false,ready:false,writes:0,nonces:0})
  assert.deepEqual(await snapshot(),before)
 }
 const initial=await snapshot()
 const first=await send({id:'o-legacy',protocol:2,create:true})
 await evaluate(async seq=>{globalThis.preparedO=await ordinaryOwner.prepare(s,seq)},first.sequence)
 const second=await send({id:'o-content-id1',protocol:3,compressed:true,create:true}),pending=await snapshot()
 await rejected(()=>ordinaryOwner.commit(preparedO));races++
 await rejected(seq=>ordinaryOwner.apply(s,seq),second.sequence)
 assert.deepEqual(await snapshot(),pending)
 await apply(first)
 const beforeRollback=await snapshot()
 assert.equal(await evaluate(async seq=>{
  const p=await ordinaryOwner.prepare(s,seq),put=IDBObjectStore.prototype.put;let injected=false,rejected=false
  IDBObjectStore.prototype.put=function(value,...rest){const request=put.call(this,value,...rest);if(this.name==='localNotes'){injected=true;request.addEventListener('success',()=>this.transaction.abort(),{once:true})}return request}
  try{await ordinaryOwner.commit(p)}catch{rejected=true}finally{IDBObjectStore.prototype.put=put}
  return rejected&&injected
 },second.sequence),true);rollbacks++
 assert.deepEqual(await snapshot(),beforeRollback);await apply(second)
 // Real disk/process restart after preparation cannot persist or reuse its plan.
 const third=await send({id:'o-content-id0',protocol:3,plain:true,create:true})
 await evaluate(async seq=>{globalThis.preparedO=await ordinaryOwner.prepare(s,seq)},third.sequence)
 const prepared=await snapshot();await restart();restarts++;assert.deepEqual(await snapshot(),prepared)
 await rejected(()=>ordinaryOwner.commit({}));await apply(third)
 // Two actual owners race on a real source change, not a forged source revision.
 const update=await send({id:'baseline-live',protocol,compressed:true})
 await evaluate(async seq=>{globalThis.preparedO=await ordinaryOwner.prepare(s,seq);const other=c21.v10OrdinaryOwnerFixture(session,meta,verifiedDevice);await other.apply(s,seq)},update.sequence);applied++
 const raced=await snapshot();await rejected(()=>ordinaryOwner.commit(preparedO));races++;assert.deepEqual(await snapshot(),raced)
 const deletion=await send({id:'o-legacy',protocol:2,deleted:true});await apply(deletion)
 const repeat=await send({id:'o-legacy',protocol:2,deleted:true});await apply(repeat)
 const updateContent=await send({id:'o-content-id1',protocol:3,compressed:true});await apply(updateContent)
 const lifecycle=await send({id:'o-lifecycle',protocol:3,compressed:true,create:true})
 await evaluate(async({seq,strategy})=>{
  globalThis.preparedO=await ordinaryOwner.prepare(s,seq)
  if(strategy==='choose_version')await meta.keys.lock();else if(strategy==='manual_merge')await meta.auth.logout();else if(strategy==='delete')await session.close();else await meta.auth.login('fixture','fixture')
 },{seq:lifecycle.sequence,strategy})
 const revoked=await snapshot();await rejected(()=>ordinaryOwner.commit(preparedO));revocations++;assert.deepEqual(await snapshot(),revoked)
 await rebind();await apply(lifecycle)
 await inspect(applied)
 const stable=await snapshot();await restart();restarts++;assert.deepEqual(await snapshot(),stable);await inspect(applied)
 assert.equal(await evaluate(seq=>ordinaryOwner.apply(s,seq),first.sequence),'already_applied');replays++
 assert.equal(await evaluate(async e=>(await transport.replayInboundPage(s,e.since,e.rawPage)).new_events,lifecycle),0);replays++
 assert.deepEqual(await snapshot(),stable)
 // P admits H-only mixed history; G/K authority remains closed.
 assert.equal(await evaluate(async()=>(await continuation.history(s)).readOnly),true)
 for(const action of [()=>prefix.prepare(s),()=>recovery.run(s)])await rejected(action)
 assert.deepEqual(await snapshot(),stable)
 await compete()
 // F/H encrypted evidence is immutable; old retained tombstones are not removed.
 for(const old of initial.legacyNoteHistory.filter(r=>r.record_kind!=='head'))assert.deepEqual(stable.legacyNoteHistory.find(r=>r.project_id===old.project_id&&r.note_id===old.note_id&&r.record_kind===old.record_kind&&r.record_id===old.record_id),old)
 for(const old of initial.inbox)assert.deepEqual(stable.inbox.find(r=>r.event_id===old.event_id),old)
 for(const old of initial.localNotes.filter(n=>n.note_id!=='baseline-live'))assert.deepEqual(stable.localNotes.find(n=>n.note_id===old.note_id),old)
 for(const name of ['outbox','receipts','legacyNoteIntents','ownerHeads','projectBindings'])assert.deepEqual(stable[name],initial[name])
 const original=stable.legacyNoteHistory.filter(r=>r.record_kind==='resolution')
 assert.equal(original.length,1);assert.equal(stable.localNotes.find(n=>n.note_id==='baseline-deleted').deleted,true)
 const h=continuationMode?await runMixedContinuationCase({getPage,snapshot,restart,rebind,compete,send,protocol,strategy,prefixMode,recoveryMode}):null
 const own=await send({id:`note-${protocol}`,protocol,deleted:strategy==='delete'}),boundary=await snapshot()
 await rejected(seq=>ordinaryOwner.apply(s,seq),own.sequence);assert.deepEqual(await snapshot(),boundary)
 // Corruption negative only, never a manufactured positive proof.
 await evaluate(async()=>{
  const db=await new Promise((resolve,reject)=>{const r=indexedDB.open(c21.WEB_DATABASE_NAME);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})
  try{await new Promise((resolve,reject)=>{const tx=db.transaction('localNotes','readwrite'),store=tx.objectStore('localNotes'),r=store.get([s.accountId,'planner-project','o-content-id1']);r.onsuccess=()=>{const n=r.result;n.envelope.ciphertext='AA';store.put(n)};tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error)})}finally{db.close()}
 })
 const corrupt=await snapshot();if(continuationMode)await rejected(()=>continuation.history(s));await rejected(()=>witness.inspect(s));await rejected(seq=>ordinaryOwner.reconcile(s,seq),first.sequence)
 if(prefixMode)await rejected(()=>c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice).prepare(s))
 if(recoveryMode)await rejected(()=>mixedRecovery.run(s))
 assert.deepEqual(await snapshot(),corrupt);await restart();restarts++;assert.deepEqual(await snapshot(),corrupt)
 await rejected(seq=>ordinaryOwner.reconcile(s,seq),first.sequence)
 return{applied,replays,rollbacks,races,revocations,barriers,restarts:restarts+(h?.hRestarts??0)+(h?.q?.qRestarts??0)+(h?.k?.kRestarts??0),tabs:1,h}
}
