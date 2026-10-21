import assert from 'node:assert/strict'
/** Independent .13 branch over the same real native F seed. No synthetic puts. */
export async function runHistoricalMetadataCase({getPage,snapshot,restart,compete,protocol,strategy,decision}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg)
 const ids=await evaluate(async({protocol,strategy,decision})=>{
  const project='planner-project',peer='44444444-4444-4444-8444-444444444444',stamp='2026-10-22T00:00:00.000000Z'
  const b=(await nativeRows('projectBindings')).find(b=>b.project_id===project),m=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project)
  const send=async(event,frame)=>{
   const cursor=(await nativeRows('cursors'))[0];event={...event,device_id:peer,server_sequence:cursor.pull_cursor+1}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:event.entity_id,entityType:event.entity_type},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   try{await session.sync.commitInboundPage(s,cursor.pull_cursor,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event,object}],next_cursor:event.server_sequence,has_more:false}))}finally{frame.fill(0)}
   return event
  }
  const note=async(id,parent=null,revision=1,deleted=false,compressed=true)=>{
   const h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null}
   const n=deleted?{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE',content:'HISTORICAL_DEPENDENCY_SOURCE'.repeat(40),checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
   const plain=c21.createNoteSyncPlaintext(h,parent,n).plaintext
   return send({...h,operation:'event',deleted_at:null},c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:b.bootstrap_id,metadata_event_id:m.tip_event_ids[0],stage_event_ids:[]},event:plain}},compressed))
  }
  const o=await note('historical-independent');await ordinaryOwner.apply(s,o.server_sequence)
  const h=await note(`note-${protocol}`,decision.children[0].event_id,5,strategy==='delete',false);await continuation.apply(s,h.server_sequence)
  let retained
  if(strategy==='keep_both'){retained=await note(`clone-${protocol}`,decision.children[1].event_id,5,false,true);await continuation.apply(s,retained.server_sequence)}
  globalThis.appendHistoricalMetadata=async(operation,revision,parent,compressed=false)=>{
   const payload=c21.readerCases().find(c=>c.id===1&&c.version===1).event
   Object.assign(payload.header,{account_id:s.canonicalUserId,bootstrap_id:b.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation,revision,generation:revision,parent_event_ids:[parent],updated_at:stamp})
   payload.metadata.name='HISTORICAL_METADATA_CONTROL'.repeat(10)
   if(operation==='delete'){payload.metadata=null;payload.deleted_at=stamp}
   const event=await send({event_id:payload.header.event_id,project_id:project,entity_id:project,entity_type:'project_metadata',operation:operation==='delete'?'delete':'upsert',revision,updated_at:stamp,deleted_at:operation==='delete'?stamp:null},c21.readerFrame({id:1,version:1,event:payload},compressed))
   await session.metadata.apply(s,event,meta.auth,meta.bindings,meta.keys);return event
  }
  const update=await appendHistoricalMetadata('update',2,m.tip_event_ids[0],true),deletion=await appendHistoricalMetadata('delete',3,update.event_id)
  globalThis.historical=c21.historicalMetadataFixture(session,meta,verifiedDevice)
  return{o:o.event_id,h:h.event_id,retained:retained?.event_id,F:decision.event_id,deletion:deletion.event_id}
 },{protocol,strategy,decision})
 const check=async()=>{
  const before=await snapshot()
  const result=await evaluate(async ids=>{
   const tx=IDBDatabase.prototype.transaction,random=crypto.getRandomValues,fetch=globalThis.fetch;let writes=0,nonces=0,http=0
   IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite'){writes++;throw Error('NO_VERIFIER_WRITES')}return tx.call(this,stores,mode,...args)}
   crypto.getRandomValues=()=>{nonces++;throw Error('NO_VERIFIER_NONCES')};globalThis.fetch=()=>{http++;throw Error('NO_VERIFIER_HTTP')}
   try{
    const results=[];for(const id of [ids.o,ids.h,...(ids.retained?[ids.retained]:[])])results.push(await historical.inspect(s,id))
    return{results,F:await historical.inspect(s,ids.F),replay:await historical.inspect(s,ids.o),writes,nonces,http,keys:Object.keys(historical)}
   }finally{IDBDatabase.prototype.transaction=tx;crypto.getRandomValues=random;globalThis.fetch=fetch}
  },ids)
  assert.deepEqual(result.keys,['inspect']);assert.equal(result.writes,0);assert.equal(result.nonces,0);assert.equal(result.http,0)
  for(const r of result.results){assert.equal(r.historicalMetadataAdmissible,true);assert.equal(r.fullHistoryAuthenticated,false);assert.equal(r.sourceAuthorized,false);assert.equal(r.firstApplyAllowed,false);assert.equal(r.commitAuthorized,false);assert.equal(r.ackAuthorized,false);assert.equal(r.ready,false)}
  assert.equal(result.F.historicalMetadataAdmissible,protocol===3);assert.equal(result.F.reason,protocol===3?null:'not_content');assert.deepEqual(result.replay,result.results[0]);assert.deepEqual(await snapshot(),before)
  return result
 }
 const original=await check(),intact=await snapshot();await compete();assert.deepEqual(await snapshot(),intact)
 await restart();await evaluate(()=>{globalThis.historical=c21.historicalMetadataFixture(session,meta,verifiedDevice)})
 assert.deepEqual(await snapshot(),intact);assert.deepEqual(await check(),original)
 assert.equal(await evaluate(async()=>{let rejects=0;for(const action of [()=>mixedRecovery.run(s),()=>c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice).prepare(s)])try{await action()}catch{rejects++}return rejects}),2)
 // A separate genuine owner acts between the verifier's two readonly snapshots.
 // Its known fixture writes are not counted as verifier writes.
 const beforeRace=await snapshot()
 assert.equal(await evaluate(async ids=>{
  const racing=c21.historicalMetadataFixture(session,meta,verifiedDevice,async()=>{
   const project='planner-project',binding=(await nativeRows('projectBindings')).find(b=>b.project_id===project),head=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),old=head.history.find(p=>p.event_id===head.tip_event_ids[0]),cursor=(await nativeRows('cursors'))[0]
   const stamp='2026-10-22T00:00:00.000000Z',h={account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:old.source_device_id,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation:'delete',revision:old.revision+1,generation:old.generation+1,parent_event_ids:[old.event_id],updated_at:stamp},payload={version:1,header:h,metadata:null,deleted_at:stamp},frame=c21.frameProjectMetadata(payload)
   const event={event_id:h.event_id,device_id:h.device_id,server_sequence:cursor.pull_cursor+1,project_id:project,entity_id:project,entity_type:'project_metadata',operation:'delete',revision:h.revision,updated_at:stamp,deleted_at:stamp}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:project,entityType:'project_metadata'},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   try{await session.sync.commitInboundPage(s,cursor.pull_cursor,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event,object}],next_cursor:event.server_sequence,has_more:false}))}finally{frame.fill(0)}
   await session.metadata.apply(s,event,meta.auth,meta.bindings,meta.keys)
  })
  try{await racing.inspect(s,ids.o);return false}catch(e){return e.code==='stale_source'}
 },ids),true)
 const raced=await snapshot();for(const name of ['localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','outbox','receipts','projectBindings'])assert.deepEqual(raced[name],beforeRace[name])
 assert.equal((await evaluate(ids=>historical.inspect(s,ids.o),ids)).historicalMetadataAdmissible,false)
 const before=await snapshot();await evaluate(()=>meta.keys.lock())
 assert.equal(await evaluate(async ids=>{try{await historical.inspect(s,ids.o);return false}catch{return true}},ids),true);assert.deepEqual(await snapshot(),before)
 return{historicalChecks:original.results.length+1,restarts:1,tabs:1,revoked:1,races:1,wireAndStorageUnchanged:true}
}
