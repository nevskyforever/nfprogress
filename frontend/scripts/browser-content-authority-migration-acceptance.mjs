import assert from 'node:assert/strict'
import {chromium} from '@playwright/test'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
// Frozen v8 physical schema. Seed only newly created disposable profiles; never reset a profile.
export const schema=[
 ['identities','canonical_user_id',[['local_account_id','local_account_id',true],['device_id','device_id',true]]],
 ['accountBindings','local_account_id',[['canonical_user_id','canonical_user_id',true]]],
 ['outbox',['account_id','event_id'],[['ordinal',['account_id','device_id','local_ordinal'],true],['state',['account_id','state','local_ordinal'],false]]],
 ['inbox',['account_id','server_sequence'],[['event',['account_id','event_id'],true],['state',['account_id','state','server_sequence'],false]]],
 ['cursors',['account_id','device_id'],[]],['receipts',['account_id','event_id'],[['server_sequence',['account_id','server_sequence'],true]]],
 ['projectBindings',['account_id','project_id'],[['bootstrap',['account_id','bootstrap_id'],true]]],['ownerHeads',['account_id','owner_kind','owner_id'],[]],
 ['localProjects',['account_id','project_id'],[]],['localNotes',['account_id','project_id','note_id'],[['identity',['account_id','note_id'],true]]],
 ['legacyNoteHistory',['account_id','project_id','note_id','record_kind','record_id'],[['event',['account_id','event_id'],true]]],
 ['legacyNoteIntents',['account_id','event_id'],[['note',['account_id','project_id','note_id'],true],['ordinal',['account_id','device_id','local_ordinal'],true]]],
]
export async function acceptContentAuthorityMigration({origin,profiles,cases}){
 assert.equal(profiles.length,2)
 const errors=[],api=[]
 for(const variant of ['empty','sealed','accepted','interrupted','schema','schema-multientry','corrupt','crypto-corruption','future']){
  const selected=profiles.find(p=>p.phase===(variant==='accepted'?'accept':'seal')),scope=selected.scope
  const data=Object.fromEntries(Object.entries(structuredClone(selected.snapshot)).map(([name,rows])=>[name,rows.filter(r=>name==='identities'||name==='accountBindings'?r.local_account_id===scope.accountId:r.account_id===scope.accountId)]))
  if(variant==='corrupt')data.receipts[0].record_version=99
  if(variant==='crypto-corruption')data.legacyNoteHistory.find(r=>r.record_kind==='candidate'&&r.record_version===1&&r.origin==='local_sealed').record_digest='0'.repeat(64)
  const directory=await mkdtemp(join(tmpdir(),'c21-v8-v9-'));let context
  const launch=async()=>{context=await chromium.launchPersistentContext(directory,{headless:true});const p=await context.newPage();p.on('pageerror',()=>errors.push(variant));p.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))api.push(variant)});await p.goto(`${origin}/scripts/browser-persistence-harness.html`);return p}
  try{
   let page=await launch()
   await page.evaluate(async({schema,data,variant})=>{
    const q=indexedDB.open(c21.WEB_DATABASE_NAME,variant==='future'?11:8)
    q.onupgradeneeded=()=>{for(const [name,keyPath,indexes] of schema){const store=q.result.createObjectStore(name,{keyPath});for(const [index,path,unique] of indexes)if(!(variant==='schema'&&name==='localNotes'&&index==='identity'))store.createIndex(index,path,{unique,multiEntry:variant==='schema-multientry'&&name==='identities'&&index==='local_account_id'})}}
    const db=await new Promise((resolve,reject)=>{q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)})
    try{await c21.runBrowserTransaction(db,schema.map(s=>s[0]),'readwrite',(tx,result)=>{if(variant!=='empty')for(const [store,rows] of Object.entries(data))for(const row of rows)tx.objectStore(store).add(row);result(undefined)})}finally{db.close()}
   },{schema,data,variant})
   const snapshot=()=>page.evaluate(async()=>{
    const q=indexedDB.open(c21.WEB_DATABASE_NAME),db=await new Promise((resolve,reject)=>{q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)})
    try{const names=Array.from(db.objectStoreNames),t=db.transaction(names),data={},schema=[];await Promise.all(names.map(name=>new Promise((resolve,reject)=>{const store=t.objectStore(name),r=store.getAll();schema.push([name,store.keyPath,Array.from(store.indexNames).map(n=>[n,store.index(n).keyPath,store.index(n).unique,store.index(n).multiEntry])]);r.onsuccess=()=>{data[name]=r.result;resolve()};r.onerror=()=>reject(r.error)})));return{version:db.version,schema,data}}finally{db.close()}
   })
   const before=await snapshot();assert.equal(before.version,variant==='future'?11:8);assert.equal(before.schema.length,12)
   const opened=await page.evaluate(async({scope,variant})=>{
    const open=IDBFactory.prototype.open
    if(variant==='interrupted')IDBFactory.prototype.open=function(...args){const q=open.apply(this,args);q.addEventListener('upgradeneeded',e=>{if(e.oldVersion===8&&e.newVersion===10)q.transaction.abort()},{once:true});return q}
    try{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);return'opened'}catch(e){return e.code}finally{IDBFactory.prototype.open=open}
   },{scope,variant})
   if(['schema','schema-multientry','corrupt','interrupted','future'].includes(variant)){
    assert.equal(opened,variant==='future'?'unsupported_version':variant==='interrupted'?'storage_failed':'corrupt_record')
    assert.deepEqual(await snapshot(),before)
    if(variant==='interrupted'){
     await page.evaluate(async scope=>{await navigator.locks.request('worta-web:writer',()=>{});globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId)},scope)
     assert.equal((await snapshot()).version,10);assert.deepEqual((await snapshot()).data,before.data)
    }
   }else{
    assert.equal(opened,'opened',variant);const after=await snapshot();assert.equal(after.version,10);assert.deepEqual(after.schema,before.schema)
    if(variant==='empty'){for(const name of schema.map(s=>s[0]).filter(s=>!['identities','accountBindings'].includes(s)))assert.deepEqual(after.data[name],[])}
    else assert.deepEqual(after.data,before.data)
    assert.equal(await page.evaluate(async()=>new Promise(resolve=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME,8);q.onsuccess=()=>{q.result.close();resolve('unsafe_open')};q.onerror=()=>resolve(q.error.name)})),'VersionError')
    assert.deepEqual(await snapshot(),after)
    if(variant!=='empty'){
     await page.evaluate(async scope=>{globalThis.meta=await c21.metadataFixture(session,scope)},scope)
     if(variant==='crypto-corruption')assert.equal(await page.evaluate(async scope=>{try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(scope);return false}catch{return true}},scope),true)
     else{
      assert.equal(await page.evaluate(scope=>session.notes.bind(meta.auth,meta.bindings,meta.keys).apply(scope,60),scope),'already_applied')
      assert.equal(await page.evaluate(scope=>session.contentNotes.bind(meta.auth,meta.bindings,meta.keys).apply(scope,67),scope),'already_applied')
      assert.equal(await page.evaluate(async scope=>{try{await session.contentNotes.bind(meta.auth,meta.bindings,meta.keys).apply(scope,62);return false}catch(e){return e.code==='unsupported_local_source'}},scope),true)
      assert.equal((await page.evaluate(scope=>session.proven.bind(meta.auth,meta.bindings,meta.keys).calculate(scope),scope)).candidate_proven_prefix,61)
      assert.deepEqual(await page.evaluate(scope=>session.sync.readCheckpoint(scope),scope),{pull_cursor:70,ack_cursor:61,proven_prefix:61,next_local_ordinal:after.data.cursors[0].next_local_ordinal})
     }
     assert.deepEqual((await snapshot()).data,before.data)
     await page.evaluate(async()=>{await meta.keys.dispose();await session.close()})
    }else await page.evaluate(()=>session.close())
    await context.close();page=await launch()
    await page.evaluate(async scope=>{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId)},scope)
    assert.deepEqual(await snapshot(),after)
   }
   cases.push(`C21.2.06 ${variant}: native disposable v8/v9 profile, exact records/schema preserved; format gate and fail-closed boundary PASS`)
  }finally{if(context)await context.close();await rm(directory,{recursive:true,force:true})}
 }
 assert.deepEqual(errors,[]);assert.deepEqual(api,[])
 cases.push('C21.2.06 populated v8 includes encrypted projects/Notes, Legacy unsealed/sealed/accepted/self-echo, peer Content proof1/conflict1/2, mixed group1/frozen history, prefix61/ACK61 and own barrier62; upgrade and disk restart retain exact bytes, no new Content authority or HTTP/page errors')
}
