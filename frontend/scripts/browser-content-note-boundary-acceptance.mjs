import assert from 'node:assert/strict'
/** Blocker evidence only: actual authenticated codec8 objects, no fake Note outcomes. */
export async function acceptContentNoteBoundary({page,scope,project,stamp,peer,metadataEvent,bootstrap,stageEvent,note,cases,counts}){
 const names=['inbox','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents','cursors','outbox','receipts','projectBindings'],snap=()=>page.evaluate(async names=>Object.fromEntries(await Promise.all(names.map(async n=>[n,await nativeRows(n)]))),names),beforeNetwork=counts()
 for(const [seq,kind] of [[10,'ordinary'],[11,'stage'],[12,'resolution']]){
  const read=await page.evaluate(async({scope,project,stamp,peer,metadataEvent,bootstrap,stageEvent,seq,kind})=>{
   const id='content-boundary-'+kind,n={id,project_id:project,stage_id:kind==='stage'?'A':null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'PRIVATE_CONTENT_NOTE',content:'PRIVATE_CONTENT_BODY',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:stamp,updated_at:stamp,metadata:{}}
   let event={version:1,header:{event_id:crypto.randomUUID(),parent_event_id:null,project_id:project,entity_id:id,entity_type:'note',operation:'upsert',revision:1,updated_at:stamp,deleted_at:null},mutation:'create',note:n}
   if(kind==='resolution'){const parents=[crypto.randomUUID(),crypto.randomUUID()].sort();event={version:2,header:{event_id:crypto.randomUUID(),parent_event_id:parents[0],additional_parent_event_ids:[parents[1]],project_id:project,entity_id:id,entity_type:'note',operation:'resolution',revision:3,updated_at:stamp},mutation:'resolution',resolution:{conflict_group_id:crypto.randomUUID(),conflict_generation:1,resolved_event_ids:parents,strategy:'choose_version',selected_event_id:parents[0]},result:{operation:'upsert',note:n}}}
   const wrapper={version:1,account_id:scope.canonicalUserId,device_id:peer,dependencies:{bootstrap_id:bootstrap,metadata_event_id:metadataEvent,stage_event_ids:kind==='stage'?[stageEvent]:[]},event}
   const ref={event_id:event.header.event_id,device_id:peer,server_sequence:seq,project_id:project,entity_id:id,entity_type:'note',operation:'event',revision:event.header.revision,updated_at:stamp,deleted_at:null},item=await meta.keys.leaseForAccount(scope.accountId).use(async amk=>{const frame=c21.readerFrame({id:8,version:1,event:wrapper},true);try{const o=await c21.encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:project,entityId:id,entityType:'note'},frame);const opened=await c21.openBrowserCanonicalObject(amk,{accountId:scope.canonicalUserId,projectId:project,entityId:id,entityType:'note',eventId:event.header.event_id},o);if(c21.canonical(opened)!==c21.canonical(wrapper))throw Error('reader_identity');return{event:ref,object:{crypto_version:1,aad_version:1,nonce:c21.encodeBase64Url(o.nonce),ciphertext:c21.encodeBase64Url(o.ciphertext)}}}finally{frame.fill(0)}})
   await session.sync.commitInboundPage(scope,seq-1,JSON.stringify({protocol_version:3,encrypted_sync_version:3,items:[item],next_cursor:seq,has_more:false}));return event.version
  },{scope,project,stamp,peer,metadataEvent,bootstrap,stageEvent,seq,kind})
  assert.equal(read,kind==='resolution'?2:1)
  const before=await snap();assert.equal(await page.evaluate(async({scope,seq})=>{try{await sn.apply(scope,seq);return false}catch(e){return e.code==='unsupported_local_source'}},{scope,seq}),true);assert.deepEqual(await snap(),before)
 }
 await note(13);assert.equal((await page.evaluate(scope=>sp.advance(scope),scope)).candidate_proven_prefix,9)
 assert.equal((await page.evaluate(scope=>sp.calculate(scope),scope)).first_blocking_sequence,10)
 assert.deepEqual(await page.evaluate(async scope=>sp.ackOnce(await sp.prepareAck(scope,or,og)),scope),{status:'no_progress',cursor:9,ready:false})
 const rows=await page.evaluate(()=>nativeRows('localNotes'));assert.equal(rows.some(r=>r.note_id.startsWith('content-boundary-')),false)
 assert.deepEqual(counts(),beforeNetwork)
 cases.push('codec8 ID1 project HTML, Stage ancestor reference and Resolution2 authenticate/read; Legacy gate rejects all without partial Note/history/wrapper writes')
 cases.push('received Content10 blocks later applied Note13 after accepted Metadata/Stage/Order prefix9; no-progress ACK9 adds zero HTTP and ready=false')
}
