import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {chromium} from '@playwright/test'
import {schema} from './browser-content-authority-migration-acceptance.mjs'

/** Physical v9 profiles seeded with exact encrypted rows from accepted real runtimes.
 * All seeding/fault injection is restricted to newly created disposable disk profiles.
 * C3 is a format specimen in unit tests, never a browser producer in this package. */
export async function acceptIndexedDbV10({origin,cases,profiles}){
 assert.equal(profiles.length,3)
 const errors=[],http=[]
 for(const variant of ['empty','legacy-sealed','legacy-accepted','intent','blocked','abort','interruption','identity','source','history','schema','cursor','bootstrap','intent-corrupt','crypto']){
  const selected=profiles.find(p=>p.phase===(['intent','intent-corrupt','crypto'].includes(variant)?'intent':variant==='legacy-sealed'?'seal':'accept'))
  const scope=selected.scope,data=Object.fromEntries(Object.entries(structuredClone(selected.snapshot)).map(([name,rows])=>[name,rows.filter(r=>['identities','accountBindings'].includes(name)?r.local_account_id===scope.accountId:r.account_id===scope.accountId)]))
  if(variant==='identity')data.identities[0].record_version=99
  if(variant==='source')data.localNotes[0].envelope.nonce='invalid'
  if(variant==='history')data.legacyNoteHistory[0].record_version=99
  if(variant==='cursor')data.cursors[0].proven_prefix=data.cursors[0].pull_cursor+1
  if(variant==='bootstrap')data.projectBindings[0].bootstrap_id=crypto.randomUUID()
  if(variant==='intent-corrupt')data.legacyNoteIntents.find(i=>i.record_version===2).intent_envelope.nonce='invalid'
  if(variant==='crypto'){const i=data.legacyNoteIntents.find(i=>i.record_version===2);i.intent_envelope.ciphertext=(i.intent_envelope.ciphertext[0]==='A'?'B':'A')+i.intent_envelope.ciphertext.slice(1)}
  const directory=await mkdtemp(join(tmpdir(),'c21-v9-v10-'));let context,page
  const launch=async()=>{context=await chromium.launchPersistentContext(directory,{headless:true});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))http.push(r.url())});await page.goto(`${origin}/scripts/browser-persistence-harness.html`)}
  const snapshot=()=>page.evaluate(async()=>{
   const q=globalThis.blocker?null:indexedDB.open(c21.WEB_DATABASE_NAME),db=globalThis.blocker??await new Promise((resolve,reject)=>{q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)})
   try{const names=Array.from(db.objectStoreNames),tx=db.transaction(names),rows={},shape=[];await Promise.all(names.map(name=>new Promise((resolve,reject)=>{const s=tx.objectStore(name),r=s.getAll();shape.push([name,s.keyPath,Array.from(s.indexNames).map(n=>[n,s.index(n).keyPath,s.index(n).unique,s.index(n).multiEntry])]);r.onsuccess=()=>{rows[name]=r.result;resolve()};r.onerror=()=>reject(r.error)})));return{version:db.version,shape,rows}}finally{if(!globalThis.blocker)db.close()}
  })
  const open=()=>page.evaluate(async scope=>{try{globalThis.session=await c21.openBrowserPersistence(scope.canonicalUserId);return'opened'}catch(e){return e.code}},scope)
  try{
   await launch()
   if(variant!=='empty')await page.evaluate(async({schema,data,variant})=>{
    const q=indexedDB.open(c21.WEB_DATABASE_NAME,9)
    q.onupgradeneeded=()=>{for(const [name,keyPath,indexes] of schema){const s=q.result.createObjectStore(name,{keyPath});for(const [index,path,unique] of indexes)if(!(variant==='schema'&&name==='localNotes'&&index==='identity'))s.createIndex(index,path,{unique})}}
    const db=await new Promise((resolve,reject)=>{q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)})
    try{await c21.runBrowserTransaction(db,schema.map(s=>s[0]),'readwrite',(tx,result)=>{for(const [name,rows] of Object.entries(data))for(const row of rows)tx.objectStore(name).add(row);result(undefined)})}finally{db.close()}
   },{schema,data,variant})
   const before=variant==='empty'?null:await snapshot()
   if(before)assert.equal(before.version,9)
   if(variant==='blocked'){
    await page.evaluate(async()=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME,9);globalThis.blocker=await new Promise(resolve=>q.onsuccess=()=>resolve(q.result))})
    assert.equal(await open(),'upgrade_blocked')
    assert.deepEqual(await snapshot(),before)
    await page.evaluate(async()=>{blocker.close();globalThis.blocker=null;await navigator.locks.request('worta-web:writer',()=>{})})
   }
   if(['abort','interruption'].includes(variant)){
    await page.evaluate(variant=>{
     const getAll=IDBObjectStore.prototype.getAll
     IDBObjectStore.prototype.getAll=function(...args){
      const q=getAll.apply(this,args)
      if(this.name==='legacyNoteIntents'&&this.transaction.mode==='versionchange'){
       if(variant==='abort')q.addEventListener('success',()=>this.transaction.abort(),{once:true})
       else {globalThis.upgradePaused=true;const keepAlive=()=>{const r=getAll.call(this);r.onsuccess=keepAlive};keepAlive()}
      }
      return q
     }
    },variant)
    if(variant==='abort'){assert.equal(await open(),'storage_failed');await page.reload()}
    else {const opening=open().catch(()=>{});await page.waitForFunction(()=>globalThis.upgradePaused===true);await context.close();await opening;await launch()}
    assert.deepEqual(await snapshot(),before)
   }
   const opened=await open()
   if(['identity','source','history','schema','cursor','bootstrap','intent-corrupt'].includes(variant)){
    assert.equal(opened,'corrupt_record',variant);assert.deepEqual(await snapshot(),before)
   }else{
    assert.equal(opened,'opened',variant);const after=await snapshot();assert.equal(after.version,11);assert.equal(after.shape.length,13)
    if(before){
     assert.deepEqual(after.shape.filter(([name])=>name!=='localStages'),before.shape)
     assert.deepEqual(Object.fromEntries(Object.entries(after.rows).filter(([name])=>name!=='localStages')),before.rows)
     assert.deepEqual(after.rows.localStages,[])
    }
    assert.equal(await page.evaluate(()=>new Promise(resolve=>{const q=indexedDB.open(c21.WEB_DATABASE_NAME,9);q.onerror=()=>resolve(q.error.name);q.onsuccess=()=>{q.result.close();resolve('unsafe')}})),'VersionError')
    if(variant!=='empty'){
     await page.evaluate(async scope=>{globalThis.meta=await c21.metadataFixture(session,scope)},scope)
     if(variant==='crypto')assert.equal(await page.evaluate(async scope=>{try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(scope);return false}catch{return true}},scope),true)
     else await page.evaluate(scope=>session.proven.bind(meta.auth,meta.bindings,meta.keys).calculate(scope),scope)
     await page.evaluate(async()=>meta.keys.lock())
     assert.equal(await page.evaluate(async scope=>{try{await session.proven.bind(meta.auth,meta.bindings,meta.keys).prepare(scope);return false}catch{return true}},scope),true)
    }
    assert.deepEqual(await snapshot(),after)
    await page.evaluate(()=>session.close());await context.close();await launch()
    assert.equal(await open(),'opened');assert.deepEqual(await snapshot(),after)
    // Reopening obtains fresh auth and a fresh key lease; nothing positive is persisted.
    if(variant!=='empty'&&variant!=='crypto')await page.evaluate(async scope=>{const meta=await c21.metadataFixture(session,scope);await session.proven.bind(meta.auth,meta.bindings,meta.keys).calculate(scope);await meta.keys.dispose()},scope)
    assert.deepEqual(await snapshot(),after)
   }
   cases.push(`C21.2.08D ${variant}: native v9→v10→v11 format gate / atomic rollback / exact encrypted rows and schema / fresh key / disk reopen PASS`)
  }finally{await context?.close();await rm(directory,{recursive:true,force:true})}
 }
 assert.deepEqual(errors,[]);assert.deepEqual(http,[])
 cases.push('C21.2.08D: 15 disposable native profiles, accepted encrypted Legacy/peer Content/mixed history and genuine I2; no migration writes, HTTP, Resolution, Content sealing, or cursor/ACK changes; page errors0')
}
