import assert from 'node:assert/strict'
/** Real F/H/O seed, original AEAD, actual owner and strict native transactions. */
export async function runPrivateMetadataCase({getPage,snapshot,restart,compete,protocol,strategy,decision}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg)
 let restarts=0,rollbacks=0,replays=0,crashes=0
 const crashRestart=async()=>{
  const page=getPage(),cdp=await page.context().newCDPSession(page),crashed=page.waitForEvent('crash',{timeout:5000})
  void cdp.send('Page.crash').catch(()=>undefined)
  await crashed;crashes++;await restart();restarts++
 }
 const setup=()=>evaluate(async({protocol,strategy,decision})=>{
  const project='planner-project',peer='44444444-4444-4444-8444-444444444444',stamp='2026-10-22T00:00:00.000000Z'
  const binding=(await nativeRows('projectBindings')).find(b=>b.project_id===project)
  globalThis.privateWriter=c21.privateMetadataFixture(session,meta,verifiedDevice)
  globalThis.sendPrivateEvent=async(event,frame)=>{
   const cursor=(await nativeRows('cursors'))[0];event={...event,device_id:peer,server_sequence:cursor.pull_cursor+1}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:event.entity_id,entityType:event.entity_type},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   try{await session.sync.commitInboundPage(s,cursor.pull_cursor,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event,object}],next_cursor:event.server_sequence,has_more:false}))}finally{frame.fill(0)}return event
  }
  globalThis.sendPrivateMetadata=async(operation)=>{
   const head=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),prior=head.history.find(p=>p.event_id===head.tip_event_ids[0]),payload=c21.readerCases().find(c=>c.id===1&&c.version===1).event
   Object.assign(payload.header,{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation,revision:prior.revision+1,generation:prior.generation+1,parent_event_ids:[prior.event_id],updated_at:stamp})
   if(operation==='delete'){payload.metadata=null;payload.deleted_at=stamp}else payload.metadata.name='PRIVATE_HANDOFF_METADATA'.repeat(10)
   return sendPrivateEvent({event_id:payload.header.event_id,project_id:project,entity_id:project,entity_type:'project_metadata',operation:operation==='delete'?'delete':'upsert',revision:payload.header.revision,updated_at:stamp,deleted_at:payload.deleted_at},c21.readerFrame({id:1,version:1,event:payload},operation!=='delete'))
  }
  globalThis.sendPrivateNote=async(id,parent=null,revision=1,deleted=false,compressed=true)=>{
   const metadata=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null}
   const note=deleted?{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE',content:'PRIVATE_HANDOFF_REAL_NOTE'.repeat(40),checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
   const event=c21.createNoteSyncPlaintext(h,parent,note).plaintext
   return sendPrivateEvent({...h,operation:'event',deleted_at:null},c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:binding.bootstrap_id,metadata_event_id:metadata.tip_event_ids[0],stage_event_ids:[]},event}},compressed))
  }
 },{protocol,strategy,decision})
 const apply=async(sequence,fault)=>evaluate(async({sequence,fault})=>{
  const writer=c21.privateMetadataFixture(session,meta,verifiedDevice,fault)
  const random=crypto.getRandomValues,fetch=globalThis.fetch;let nonces=0,http=0
  crypto.getRandomValues=()=>{nonces++;throw Error('HANDOFF_NONCE_FORBIDDEN')};globalThis.fetch=()=>{http++;throw Error('HANDOFF_HTTP_FORBIDDEN')}
  try{const token=await writer.prepare(s,sequence),result=await writer.commit(token);return{result,nonces,http}}catch(e){return{error:e.code??e.name,commitMayHaveOccurred:e.commitMayHaveOccurred??false,nonces,http}}
  finally{crypto.getRandomValues=random;globalThis.fetch=fetch}
 },{sequence,fault})
 await setup()
 // Genuine mixed history: O and H, including both original/retained roles.
 await evaluate(async({protocol,strategy,decision})=>{
  const o=await sendPrivateNote('private-independent');await ordinaryOwner.apply(s,o.server_sequence)
  const h=await sendPrivateNote(`note-${protocol}`,decision.children[0].event_id,5,strategy==='delete',false);await continuation.apply(s,h.server_sequence)
  if(strategy==='keep_both'){const r=await sendPrivateNote(`clone-${protocol}`,decision.children[1].event_id,5,false,true);await continuation.apply(s,r.server_sequence)}
 },{protocol,strategy,decision})
 const update=await evaluate(()=>sendPrivateMetadata('update')),before=await snapshot()
 await compete();assert.deepEqual(await snapshot(),before)
 for(const fault of ['abort','request']){
  const result=await apply(update.server_sequence,fault);assert.ok(result.error);assert.equal(result.commitMayHaveOccurred,false);assert.equal(result.nonces,0);assert.equal(result.http,0);assert.deepEqual(await snapshot(),before);rollbacks++
 }
 const fault=['key','profile','auth','epoch'][['choose_version','manual_merge','delete','keep_both'].indexOf(strategy)],revocation=await apply(update.server_sequence,fault)
 assert.ok(revocation.error);assert.equal(revocation.commitMayHaveOccurred,false);assert.equal(revocation.nonces,0);assert.equal(revocation.http,0);assert.deepEqual(await snapshot(),before);rollbacks++
 await restart();restarts++;await setup();assert.deepEqual(await snapshot(),before)
 // Genuine inbound transport races the prepared snapshot; O cannot skip the earlier Metadata.
 await evaluate(async sequence=>{globalThis.stalePrivatePlan=await privateWriter.prepare(s,sequence);globalThis.racingPrivateNote=await sendPrivateNote('private-racing-note')},update.server_sequence)
 const raced=await snapshot()
 assert.equal(await evaluate(async()=>{try{await privateWriter.commit(stalePrivatePlan);return false}catch(e){return e.code==='stale_source'}}),true);assert.deepEqual(await snapshot(),raced)
 const success=await apply(update.server_sequence);assert.equal(success.result.status,'applied');assert.equal(success.nonces,0);assert.equal(success.http,0)
 const active=await snapshot()
 for(const name of ['identities','accountBindings','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','outbox','receipts','projectBindings','cursors'])assert.deepEqual(active[name],raced[name])
 assert.equal(active.inbox.filter((r,i)=>JSON.stringify(r)!==JSON.stringify(raced.inbox[i])).length,1)
 assert.equal(active.ownerHeads.filter((r,i)=>JSON.stringify(r)!==JSON.stringify(raced.ownerHeads[i])).length,1)
 await evaluate(()=>ordinaryOwner.apply(s,racingPrivateNote.server_sequence))
 // Create a delete, lose a prepared plan through a full process close, then reopen actual disk.
 const deletion=await evaluate(()=>sendPrivateMetadata('delete')),received=await snapshot()
 await evaluate(sequence=>privateWriter.prepare(s,sequence).then(t=>{globalThis.lostPrivatePlan=t}),deletion.server_sequence)
 await crashRestart();await setup();assert.deepEqual(await snapshot(),received)
 const post=await apply(deletion.server_sequence,'postcheck');assert.equal(post.error,'post_commit_verification_failed');assert.equal(post.commitMayHaveOccurred,true);assert.equal(post.nonces,0);assert.equal(post.http,0)
 const terminal=await snapshot();assert.equal(terminal.inbox.find(r=>r.event_id===deletion.event_id).state,'applied')
 for(const name of ['identities','accountBindings','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','outbox','receipts','projectBindings','cursors'])assert.deepEqual(terminal[name],received[name])
 await crashRestart();await setup();assert.deepEqual(await snapshot(),terminal)
 for(const sequence of [1,update.server_sequence,deletion.server_sequence]){
  const result=await evaluate(async sequence=>{
   const random=crypto.getRandomValues,fetch=globalThis.fetch
   crypto.getRandomValues=()=>{throw Error('REPLAY_NONCE_FORBIDDEN')};globalThis.fetch=()=>{throw Error('REPLAY_HTTP_FORBIDDEN')}
   try{return await privateWriter.replay(s,sequence)}finally{crypto.getRandomValues=random;globalThis.fetch=fetch}
  },sequence);assert.equal(result.status,'already_applied');assert.equal(result.ackAuthorized,false);assert.equal(result.ready,false);replays++
 }
 const prefix=await evaluate(()=>c21.historicalPrefixFixture(session,meta,verifiedDevice).inspect(s));assert.equal(prefix.candidate_historical_prefix,deletion.server_sequence)
 assert.equal(await evaluate(async diagnostic=>{try{await privateWriter.commit(diagnostic);return false}catch(e){return e.code==='invalid_plan'}},prefix),true)
 assert.deepEqual(await snapshot(),terminal)
 assert.equal(await evaluate(async()=>{let rejected=0;for(const action of [()=>mixedRecovery.run(s),()=>c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice).prepare(s)])try{await action()}catch{rejected++}return rejected}),2)
 assert.deepEqual(await snapshot(),terminal)
 return{applied:2,rollbacks,restarts,replays,crashes,tabs:1,races:1,revoked:1,postCommitFailures:1}
}
