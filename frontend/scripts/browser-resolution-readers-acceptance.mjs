/** Isolated readers over a real disposable v10 profile; never stores a future authority format. */
import assert from 'node:assert/strict'
import {mkdtemp,rm} from 'node:fs/promises'
import {join} from 'node:path'
import {tmpdir} from 'node:os'
import {chromium} from '@playwright/test'
const origin=new URL(process.argv[2]||'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname,'127.0.0.1')
const directory=await mkdtemp(join(tmpdir(),'c21-resolution-readers-')),errors=[],requests=[]
let context
const launch=async()=>{context=await chromium.launchPersistentContext(directory,{headless:true});context.on('page',page=>{page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))requests.push(r.url())})});const page=await context.newPage();await page.goto(`${origin}/scripts/browser-persistence-harness.html`);return page}
try{
 let page=await launch()
 const before=await page.evaluate(async()=>{
  const user='11111111-1111-4111-8111-111111111111',session=await c21.openBrowserPersistence(user),identity=await session.provision(user)
  const scope={canonicalUserId:user,accountId:identity.local_account_id,deviceId:identity.device_id},meta=await c21.metadataFixture(session,scope),local=session.localSource.bind(meta.auth,meta.bindings,meta.keys),at='2026-10-19T00:00:00.000000Z'
  await local.initializeProject(scope,{project:{id:'p',name:'DISPOSABLE_READER_PROJECT',goal:null,infinite:true,unit:'symbols',status:'active',created_at:null,updated_at:null,payload:{}},notes:[{state:'live',note:{id:'n',project_id:'p',stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',title:'reader fixture',content:'<p>fixture</p>',checklist:[],color:'default',pinned:false,archived:false,sort_order:0,tags:[],created_at:at,updated_at:at,metadata:{},revision:0}}]})
  const prepared=await session.projects.prepare(scope,{project_id:'p',mode:'upload_existing'}),registered=await session.projects.confirmRegistration(scope,prepared,{remote_state:'initializing',remote_high_water:0})
  await session.initialNotes.bind(meta.auth,meta.bindings,meta.keys).capture(scope,registered)
  const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents'],snapshot=async()=>Object.fromEntries(await Promise.all(names.map(async name=>[name,await nativeRows(name)]))),saved=await snapshot(),history=saved.legacyNoteHistory
  if(!history.some(r=>r.record_kind==='candidate'))throw Error('genuine history required')
  const transaction=IDBDatabase.prototype.transaction;let writes=0
  IDBDatabase.prototype.transaction=function(stores,mode,...args){if(mode==='readwrite')writes++;return transaction.call(this,stores,mode,...args)}
  try{
   for(const row of history)c21.resolutionRecords.readFutureHistoryRecord(row,scope)
   c21.inspectResolutionDag(scope,history)
   const lease=meta.keys.leaseForAccount(scope.accountId),cursor=saved.cursors[0]
   const result=await lease.use(amk=>c21.authenticateResolutionHistory(scope,{history,rows:saved.inbox,bindings:saved.projectBindings,owners:saved.ownerHeads,out:saved.outbox,receipts:saved.receipts,cursor},amk,()=>lease.isCurrent()))
   if(result.resolutions!==0)throw Error('Resolution authority invented')
   const candidate=history.find(r=>r.record_kind==='candidate');let rejected=false
   try{c21.resolutionRecords.readFutureHistoryRecord({...candidate,record_version:4,record_kind:'resolution'},scope)}catch{rejected=true}
   if(!rejected||writes!==0||JSON.stringify(await snapshot())!==JSON.stringify(saved))throw Error('reader boundary changed durable state')
  }finally{IDBDatabase.prototype.transaction=transaction}
  await session.close()
  return saved
 })
 await context.close();page=await launch()
 const after=await page.evaluate(async()=>{
  const user='11111111-1111-4111-8111-111111111111',session=await c21.openBrowserPersistence(user)
  try{const names=['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents'];return {version:c21.WEB_DATABASE_VERSION,saved:Object.fromEntries(await Promise.all(names.map(async name=>[name,await nativeRows(name)])))}}finally{await session.close()}
 })
 assert.equal(after.version,11);assert.deepEqual(after.saved,before);assert.deepEqual(requests,[]);assert.deepEqual(errors,[])
 console.log('PASS: Chromium v11 real encrypted Legacy history; isolated readers read only; exact disk reopen; no future records, HTTP, ACK or writer activation; page errors 0')
}finally{await context?.close();await rm(directory,{recursive:true,force:true})}
