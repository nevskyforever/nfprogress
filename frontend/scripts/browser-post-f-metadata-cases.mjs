import assert from 'node:assert/strict'

/** Original sender events, accepted F/H/O owners, actual native IndexedDB. */
export async function runPostFMetadataCase({getPage,snapshot,restart,compete,protocol,strategy,decision}){
 const evaluate=(fn,arg)=>getPage().evaluate(fn,arg)
 let ownerCommits=0,cursorCommits=0,rollbacks=0,restarts=0,crashes=0,races=0,replays=0
 const crashRestart=async()=>{
  const page=getPage(),cdp=await page.context().newCDPSession(page),crashed=page.waitForEvent('crash',{timeout:5000})
  void cdp.send('Page.crash').catch(()=>undefined);await crashed;crashes++;await restart();restarts++
 }
 const setup=()=>evaluate(async()=>{
  const project='planner-project',peer='44444444-4444-4444-8444-444444444444',stamp='2026-10-22T00:00:00.000000Z'
  const binding=(await nativeRows('projectBindings')).find(b=>b.project_id===project)
  globalThis.postMetadata=c21.postFMetadataFixture(session,meta,verifiedDevice)
  globalThis.sendPostEvent=async(event,frame)=>{
   const cursor=(await nativeRows('cursors'))[0];event={...event,device_id:peer,server_sequence:cursor.pull_cursor+1}
   const object=await meta.keys.leaseForAccount(s.accountId).use(async amk=>{const o=await c21.encryptObjectBytes(amk,{userId:s.canonicalUserId,projectId:project,entityId:event.entity_id,entityType:event.entity_type},frame);try{return{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}finally{o.nonce.fill(0);o.ciphertext.fill(0)}})
   const rawPage=JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[{event,object}],next_cursor:event.server_sequence,has_more:false})
   try{await session.sync.commitInboundPage(s,cursor.pull_cursor,rawPage)}finally{frame.fill(0)}return{...event,since:cursor.pull_cursor,rawPage}
  }
  globalThis.sendPostMetadata=async(operation)=>{
   const head=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),prior=head.history.find(p=>p.event_id===head.tip_event_ids[0]),payload=c21.readerCases().find(c=>c.id===1&&c.version===1).event
   Object.assign(payload.header,{account_id:s.canonicalUserId,bootstrap_id:binding.bootstrap_id,device_id:peer,project_id:project,entity_id:project,event_id:crypto.randomUUID(),operation,revision:prior.revision+1,generation:prior.generation+1,parent_event_ids:[prior.event_id],updated_at:stamp})
   if(operation==='delete'){payload.metadata=null;payload.deleted_at=stamp}else payload.metadata.name='POST_F_METADATA'.repeat(10)
   return sendPostEvent({event_id:payload.header.event_id,project_id:project,entity_id:project,entity_type:'project_metadata',operation:operation==='delete'?'delete':'upsert',revision:payload.header.revision,updated_at:stamp,deleted_at:payload.deleted_at},c21.readerFrame({id:1,version:1,event:payload},operation!=='delete'))
  }
  globalThis.sendPostNote=async(id,parent=null,revision=1,deleted=false,compressed=true)=>{
   const metadata=(await nativeRows('ownerHeads')).find(h=>h.owner_kind==='project_metadata'&&h.owner_id===project),h={event_id:crypto.randomUUID(),project_id:project,entity_id:id,entity_type:'note',operation:deleted?'delete':'upsert',revision,updated_at:stamp,deleted_at:deleted?stamp:null}
   const note=deleted?{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:stamp}:{id,project_id:project,stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'DISPOSABLE',content:'AUTHENTIC_POST_F_NOTE'.repeat(40),checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
   const event=c21.createNoteSyncPlaintext(h,parent,note).plaintext
   return sendPostEvent({...h,operation:'event',deleted_at:null},c21.readerFrame({id:8,version:1,event:{version:1,account_id:s.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:binding.bootstrap_id,metadata_event_id:metadata.tip_event_ids[0],stage_event_ids:[]},event}},compressed))
  }
 })
 const run=(fault,options,allowOrdinarySource=false)=>evaluate(async({fault,options,allowOrdinarySource})=>{
  const fixture=c21.postFMetadataFixture(session,meta,verifiedDevice,fault),random=crypto.getRandomValues,fetch=globalThis.fetch;let nonces=0,http=0
  crypto.getRandomValues=value=>{nonces++;if(!allowOrdinarySource)throw Error('ROUTING_NONCE_FORBIDDEN');return random.call(crypto,value)};globalThis.fetch=()=>{http++;throw Error('ROUTING_HTTP_FORBIDDEN')}
  try{return{result:await fixture.recovery.run(s,options),nonces,http}}catch(e){return{error:e.code??e.name,commitMayHaveOccurred:e.commitMayHaveOccurred??false,nonces,http}}finally{crypto.getRandomValues=random;globalThis.fetch=fetch}
 },{fault,options,allowOrdinarySource})
 const privateCursor=(fault)=>evaluate(async fault=>{
  const prefix=c21.postFMetadataFixture(session,meta,verifiedDevice,fault).prefix
  try{const token=await prefix.prepareCommit(await prefix.prepare(s));return{result:await prefix.commit(token)}}catch(e){return{error:e.code??e.name,commitMayHaveOccurred:e.commitMayHaveOccurred??false}}
 },fault)
 const quiet=r=>{assert.equal(r.nonces,0);assert.equal(r.http,0)}
 const sourceStable=(a,b)=>{for(const name of ['identities','accountBindings','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','outbox','receipts','projectBindings'])assert.deepEqual(b[name],a[name])}
 const ownerDelta=(a,b,event)=>{
  assert.equal(b.inbox.length,a.inbox.length);assert.equal(b.ownerHeads.length,a.ownerHeads.length)
  assert.equal(b.inbox.filter((r,i)=>JSON.stringify(r)!==JSON.stringify(a.inbox[i])).length,1)
  assert.equal(b.ownerHeads.filter((r,i)=>JSON.stringify(r)!==JSON.stringify(a.ownerHeads[i])).length,1)
  for(const row of a.inbox)if(row.event_id!==event)assert.deepEqual(b.inbox.find(r=>r.event_id===row.event_id),row)
  assert.equal(b.inbox.find(r=>r.event_id===event).wire_item,a.inbox.find(r=>r.event_id===event).wire_item)
  assert.equal(b.inbox.find(r=>r.event_id===event).state,'applied')
 }
 await setup()
 await evaluate(async({protocol,strategy,decision})=>{
  const o=await sendPostNote('post-f-independent');await ordinaryOwner.apply(s,o.server_sequence)
  const h=await sendPostNote(`note-${protocol}`,decision.children[0].event_id,5,strategy==='delete',false);await continuation.apply(s,h.server_sequence)
  if(strategy==='keep_both'){const r=await sendPostNote(`clone-${protocol}`,decision.children[1].event_id,5,false,true);await continuation.apply(s,r.server_sequence)}
 },{protocol,strategy,decision})
 const update=await evaluate(()=>sendPostMetadata('update')),before=await snapshot()
 await compete();assert.deepEqual(await snapshot(),before)
 for(const fault of ['owner-abort','owner-request']){const r=await run(fault);assert.ok(r.error);quiet(r);assert.deepEqual(await snapshot(),before);rollbacks++}
 const life=['key','profile','auth','epoch'][['choose_version','manual_merge','delete','keep_both'].indexOf(strategy)]
 const revoked=await run(`owner-${life}`);assert.ok(revoked.error);quiet(revoked);assert.deepEqual(await snapshot(),before);rollbacks++
 await restart();restarts++;await setup()
 // A real later transport page invalidates private prefix authority prepared
 // before the Metadata mutation; no filtered/partial account can survive CAS.
 await evaluate(async()=>{globalThis.stalePostPrefix=await postMetadata.prefix.prepareCommit(await postMetadata.prefix.prepare(s));globalThis.racingPostNote=await sendPostNote('post-f-racing')})
 const raced=await snapshot()
 assert.equal(await evaluate(async()=>{try{await postMetadata.prefix.commit(stalePostPrefix);return false}catch(e){return e.code==='stale_source'}}),true);assert.deepEqual(await snapshot(),raced);races++
 const applied=await run(undefined,{maxEvents:1});quiet(applied);assert.deepEqual(applied.result.applied,[{sequence:update.server_sequence,route:'metadata',status:'applied'}]);assert.equal(applied.result.blocker.kind,'budget_exhausted')
 const active=await snapshot();sourceStable(raced,active);ownerDelta(raced,active,update.event_id);assert.equal(active.cursors[0].proven_prefix,update.server_sequence);assert.deepEqual({...active.cursors[0],proven_prefix:raced.cursors[0].proven_prefix},raced.cursors[0]);ownerCommits++;cursorCommits++
 const ordinary=await run(undefined,undefined,true);assert.equal(ordinary.http,0);assert.ok(ordinary.nonces>0);assert.equal(ordinary.result.applied[0].route,'content');assert.equal(ordinary.result.blocker,null);cursorCommits++
 const stable=await snapshot();const again=await run();quiet(again);assert.deepEqual(again.result.applied,[]);assert.deepEqual(await snapshot(),stable);replays++
 const deletion=await evaluate(()=>sendPostMetadata('delete')),received=await snapshot()
 await evaluate(async sequence=>{globalThis.lostPostOwnerPlan=await c21.privateMetadataFixture(session,meta,verifiedDevice).prepare(s,sequence)},deletion.server_sequence)
 await crashRestart();await setup();assert.deepEqual(await snapshot(),received)
 const stopped=await run('prefix-abort');quiet(stopped);assert.deepEqual(stopped.result.applied,[{sequence:deletion.server_sequence,route:'metadata',status:'applied'}]);assert.equal(stopped.result.blocker.reason,'historical_prefix_verification_failed');assert.equal(stopped.result.prefixCommitMayHaveOccurred,false)
 const terminal=await snapshot();sourceStable(received,terminal);ownerDelta(received,terminal,deletion.event_id);assert.deepEqual(terminal.cursors,received.cursors);ownerCommits++;rollbacks++
 // Native request failure, abort and lifecycle invalidation all preserve the
 // already committed owner, while consuming the failed cursor authority.
 for(const fault of ['prefix-abort','prefix-request',`prefix-${life}`]){const r=await privateCursor(fault);assert.ok(r.error);assert.equal(r.commitMayHaveOccurred,false);assert.deepEqual(await snapshot(),terminal);rollbacks++}
 await restart();restarts++;await setup();assert.deepEqual(await snapshot(),terminal)
 await evaluate(async()=>{globalThis.staleTerminalPrefix=await postMetadata.prefix.prepareCommit(await postMetadata.prefix.prepare(s));globalThis.pendingAfterDelete=await sendPostNote('received-after-delete')})
 const pending=await evaluate(()=>pendingAfterDelete),terminalPending=await snapshot()
 assert.equal(await evaluate(async()=>{try{await postMetadata.prefix.commit(staleTerminalPrefix);return false}catch(e){return e.code==='stale_source'}}),true);assert.deepEqual(await snapshot(),terminalPending);races++
 await crashRestart();await setup();assert.deepEqual(await snapshot(),terminalPending)
 const committed=await run('prefix-postcheck');quiet(committed);assert.equal(committed.result.prefixCommitMayHaveOccurred,true);assert.equal(committed.result.blocker.reason,'historical_prefix_verification_failed');assert.deepEqual(committed.result.applied,[])
 const cursorState=await snapshot();sourceStable(terminalPending,cursorState);assert.deepEqual(cursorState.ownerHeads,terminalPending.ownerHeads);assert.deepEqual(cursorState.inbox,terminalPending.inbox);assert.equal(cursorState.cursors[0].proven_prefix,deletion.server_sequence);assert.equal(cursorState.cursors[0].ack_cursor,terminalPending.cursors[0].ack_cursor);cursorCommits++
 await crashRestart();await setup();assert.deepEqual(await snapshot(),cursorState)
 const diagnostic=await evaluate(()=>c21.historicalPrefixFixture(session,meta,verifiedDevice).inspect(s));assert.equal(diagnostic.candidate_historical_prefix,deletion.server_sequence)
 assert.equal(await evaluate(async diagnostic=>{try{await postMetadata.prefix.commit(diagnostic);return false}catch(e){return e.code==='invalid_token'}},diagnostic),true)
 const replay=await run(undefined,{replay:{since:pending.since,rawPage:pending.rawPage}});quiet(replay);assert.deepEqual(replay.result.applied,[]);assert.equal(replay.result.blocker.reason,'deleted_metadata_live_apply');assert.equal(replay.result.prefix.counts.resolution,1);assert.equal(replay.result.prefix.counts.metadata,3);assert.equal(replay.result.prefix.candidate_proven_prefix,deletion.server_sequence);assert.equal(replay.result.prefix.first_blocking_sequence,pending.server_sequence);assert.equal(replay.result.replayed_events,1);replays++
 assert.equal(await evaluate(async sequence=>{try{await ordinaryOwner.apply(s,sequence);return false}catch{return true}},pending.server_sequence),true)
 assert.equal(await evaluate(async()=>{let rejected=0;for(const action of [()=>mixedRecovery.run(s),()=>c21.mixedResolutionPrefixFixture(session,meta,verifiedDevice).prepare(s)])try{await action()}catch{rejected++}return rejected}),2)
 assert.deepEqual(await snapshot(),cursorState)
 return{ownerCommits,cursorCommits,rollbacks,restarts,crashes,races,replays,tabs:1,postCommitFailures:1}
}
