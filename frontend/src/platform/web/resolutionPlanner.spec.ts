// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {plannerFixture} from './resolutionPlanner.testFixture'
import {scope,amk} from './bootstrap.testFixture'
import type {BrowserSyncTransaction} from './syncDurability'
import {BrowserResolutionPlanner} from './resolutionPlanner'
afterEach(()=>vi.restoreAllMocks())
it.each(['choose_version','manual_merge','delete','keep_both'] as const)('genuine original protocol3 %s plan; exact real conflict witnesses and zero durable writes',async strategy=>{
 const f=await plannerFixture(strategy),before=f.before(),start=f.f.calls.length
 const p=await f.runtime.prepare(scope,f.sequence)
 expect(p.status).toMatchObject({readOnly:true,commitAuthorized:false,ackAuthorized:false,strategy,parentCount:2});expect(Object.keys(p.token)).toEqual([])
 expect(await f.runtime.inspect(p.token)).toEqual(p.status);expect((await f.runtime.prepare(scope,f.sequence)).status).toEqual(p.status)
 expect(f.f.db).toEqual(before);expect(f.f.calls.slice(start).every((c:any)=>c.mode==='readonly')).toBe(true)
 expect(f.resolution.resolution.conflict_group_id).not.toBe(f.evidence.group_snapshot.group_id)
 expect(f.http).toHaveBeenCalledTimes(1)
})
it.each(['choose_version','manual_merge','delete','keep_both'] as const)('genuine protocol2 %s with real Legacy parents and no invented Content dependency',async strategy=>{
 const f=await plannerFixture(strategy,2,false,true),before=f.before()
 expect((await f.runtime.prepare(scope,f.sequence)).status.strategy).toBe(strategy);expect(f.f.db).toEqual(before)
})
it.each([3,64])('full %i-parent authenticated actual conflict, not a structural DAG-only fixture',async count=>{
 const f=await plannerFixture('choose_version',count),before=f.before()
 expect((await f.runtime.prepare(scope,f.sequence)).status.parentCount).toBe(count);expect(f.f.db).toEqual(before)
},30000)
it('published frozen local Legacy parent uses actual seal+receipt without self echo',async()=>{const f=await plannerFixture('choose_version',2,true),before=f.before();expect((await f.runtime.prepare(scope,f.sequence)).status.parentCount).toBe(2);expect(f.f.db).toEqual(before)})
it.each(['ciphertext','source device','server event','sequence','own source','bootstrap','missing parent','unpublished local','receipt missing','extra tip','group generation','source revision','note changed','metadata','wrong key','wrong device','wrong account','wrong protocol','fake token','source corrupt'] as const)('%s fails closed with all durable rows unchanged',async kind=>{
 const f=await plannerFixture('choose_version',2,['unpublished local','receipt missing'].includes(kind)),w=JSON.parse(f.received.wire_item)
 if(kind==='ciphertext')w.object.ciphertext=(w.object.ciphertext[0]==='A'?'B':'A')+w.object.ciphertext.slice(1)
 if(kind==='source device')w.event.device_id=crypto.randomUUID()
 if(kind==='own source')w.event.device_id=scope.deviceId
 if(kind==='server event')w.event.event_id=crypto.randomUUID()
 if(kind==='sequence')f.received.server_sequence++
 if(kind==='bootstrap')f.content.dependencies.bootstrap_id=crypto.randomUUID()
 if(kind==='wrong protocol')f.received.protocol_version=2
 f.received.wire_item=JSON.stringify(w)
 if(kind==='bootstrap')await f.reseal()
 if(kind==='missing parent')f.f.db.legacyNoteHistory=f.f.db.legacyNoteHistory.filter((r:any)=>r.event_id!==f.parents[0]!.event_id)
 if(kind==='unpublished local'){f.f.db.outbox=[];f.f.db.receipts=[]}
 if(kind==='receipt missing')f.f.db.receipts=[]
 if(kind==='extra tip'){const g=f.f.db.legacyNoteHistory.find((r:any)=>r.record_kind==='group');g.tip_event_ids.pop()}
 if(kind==='group generation')f.f.db.legacyNoteHistory.find((r:any)=>r.record_kind==='group').conflict_generation++
 if(kind==='source revision')f.f.db.localProjects[0].source_revision++
 if(kind==='note changed')f.f.db.localNotes[0].note_revision++
 if(kind==='metadata')f.f.db.ownerHeads[0].tip_event_ids=[crypto.randomUUID()]
 if(kind==='source corrupt')f.f.db.localNotes[0].envelope.ciphertext='AAAA'
 let old:Uint8Array|undefined
 if(kind==='wrong key'){old=amk.slice();amk.fill(0)}
 const before=f.before(),changed={...scope,...(kind==='wrong device'?{deviceId:crypto.randomUUID()}:{}),...(kind==='wrong account'?{accountId:crypto.randomUUID()}: {})}
 try{if(kind==='fake token')await expect(f.runtime.inspect({} as never)).rejects.toThrow();else await expect(f.runtime.prepare(changed,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before)}finally{if(old){amk.set(old);old.fill(0)}}
})
it.each(['logout','key','profile','source','conflict','dependency','cursor','other instance'] as const)('private token invalidates on %s; no authority survives',async kind=>{
 const f=await plannerFixture(),p=await f.runtime.prepare(scope,f.sequence)
 if(kind==='logout')await f.f.auth.logout()
 if(kind==='key')f.f.lock()
 if(kind==='profile')f.close()
 if(kind==='source')f.f.db.localProjects[0].source_revision++
 if(kind==='conflict')f.f.db.legacyNoteHistory.find((r:any)=>r.record_kind==='group').conflict_generation++
 if(kind==='dependency')f.f.db.ownerHeads[0].tip_event_ids=[crypto.randomUUID()]
 if(kind==='cursor')f.f.db.cursors[0].pull_cursor++
 const before=f.before(),runtime=kind==='other instance'?f.factory.bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device):f.runtime
 await expect(runtime.inspect(p.token)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
it.each(['logout','key','profile','account'] as const)('invalidation during async preparation: %s',async kind=>{
 const f=await plannerFixture(),before=f.before(),digest=crypto.subtle.digest.bind(crypto.subtle);let hit=false
 const spy=vi.spyOn(crypto.subtle,'digest').mockImplementation(async(...args)=>{const r=await digest(...args);if(!hit){hit=true;if(kind==='logout')await f.f.auth.logout();if(kind==='account')await f.f.auth.logout();if(kind==='key')f.f.lock();if(kind==='profile')f.close()}return r})
 await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before);spy.mockRestore()
})
it.each(['local note','tombstone','other project','history','intent','outbox','genesis inbox'] as const)('keep_both %s clone collision preserves everything',async kind=>{
 const f=await plannerFixture('keep_both'),id='retained-note'
 if(['local note','tombstone','other project'].includes(kind))f.f.db.localNotes.push({...f.f.db.localNotes[0],note_id:id,project_id:kind==='other project'?'foreign':'p',deleted:kind==='tombstone'})
 if(kind==='history')f.f.db.legacyNoteHistory.push({...f.f.db.legacyNoteHistory[0],note_id:id})
 if(kind==='intent')f.f.db.legacyNoteIntents.push({account_id:scope.accountId,note_id:id})
 if(kind==='outbox'){const wire=JSON.parse(f.received.wire_item);f.f.db.outbox.push({record_version:1,account_id:scope.accountId,device_id:scope.deviceId,event_id:wire.event.event_id,local_ordinal:1,state:'sealed',protocol_version:2,raw_body:JSON.stringify({protocol_version:2,encrypted_sync_version:2,device_id:scope.deviceId,items:[{event:{...wire.event,device_id:undefined,server_sequence:undefined,entity_id:id,operation:'upsert'},object:wire.object}]})})}
 if(kind==='genesis inbox'){const w=JSON.parse(f.received.wire_item);w.event.entity_id=id;w.event.event_id=crypto.randomUUID();w.event.server_sequence++;w.event.revision=1;f.f.db.inbox.push({...f.received,event_id:w.event.event_id,server_sequence:w.event.server_sequence,wire_item:JSON.stringify(w)})}
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
it.each(['choose_version','manual_merge','delete','keep_both'] as const)('Stage/plain %s uses actual current Metadata/Stage proofs and original parent routes',async strategy=>{
 const f=await plannerFixture(strategy,2,false,false,{stage:true,format:'plain',compressed:true}),before=f.before()
 expect((await f.runtime.prepare(scope,f.sequence)).status.strategy).toBe(strategy);expect(f.f.db).toEqual(before)
})
it.each(['missing metadata','missing stage','stage changed','stage refs','newer edit','selected result','retained route','oversized source','timestamp','missing bootstrap','remote publication','stale parents','cycle'] as const)('%s blocks an authenticated decision without mutation',async kind=>{
 const f=await plannerFixture(kind==='retained route'?'keep_both':'choose_version',kind==='stale parents'?3:2,false,false,kind.includes('stage')?{stage:true,format:'html'}:undefined)
 if(kind==='missing metadata')f.f.db.ownerHeads=f.f.db.ownerHeads.filter((h:any)=>h.owner_kind!=='project_metadata')
 if(kind==='missing stage')f.f.db.ownerHeads=f.f.db.ownerHeads.filter((h:any)=>h.owner_kind!=='stage')
 if(kind==='stage changed')f.f.db.ownerHeads.find((h:any)=>h.owner_kind==='stage').tip_event_ids=[crypto.randomUUID()]
 if(kind==='stage refs'){f.content.dependencies.stage_event_ids=[crypto.randomUUID()];await f.reseal()}
 if(kind==='newer edit'){const source=f.f.local,token=(await source.readSnapshot(scope,'p')).token;await source.updateNote(scope,token,'content-note',{content:'NEWER_LOCAL_EDIT'},'2026-10-19T00:00:00.000000Z')}
 if(kind==='selected result'){if(f.resolution.result.operation!=='upsert')throw Error('fixture');f.resolution.result.note.content='UNSELECTED_TEXT';await f.reseal()}
 if(kind==='retained route'){const d=f.resolution.resolution;if(d.strategy!=='keep_both')throw Error('fixture');d.retained_note.source_map_id='map';/* frozen Content encoder rejects this; use protocol2 malformed route below */ const {encodeNoteSyncResolutionV2}=await import('@/cloud/noteSyncResolutionV2Codec');expect(()=>encodeNoteSyncResolutionV2(f.resolution)).not.toThrow();await expect(f.reseal()).rejects.toThrow();d.retained_note.source_map_id=null;d.retained_note.content='WRONG_OTHER_PARENT';await f.reseal()}
 if(kind==='oversized source'){if(f.resolution.result.operation!=='upsert')throw Error('fixture');f.resolution.result.note.content='x'.repeat(300001);await f.reseal()}
 if(kind==='timestamp'){const w=JSON.parse(f.received.wire_item);w.event.updated_at='2026-10-19T00:00:00.000000Z';f.received.wire_item=JSON.stringify(w)}
 if(kind==='missing bootstrap')f.f.db.projectBindings=[]
 if(kind==='remote publication'){const r=f.f.db.inbox.find((r:any)=>r.event_id===f.parents[0]!.event_id);for(const key of Object.keys(r))if(key.endsWith('_proof'))delete r[key];r.record_version=1;r.state='received'}
 if(kind==='stale parents'){const ids=f.resolution.resolution.resolved_event_ids.slice(0,2);f.resolution.resolution.resolved_event_ids=ids;f.resolution.header.parent_event_id=ids[0]!;f.resolution.header.additional_parent_event_ids=ids.slice(1);if(f.resolution.resolution.strategy==='choose_version')f.resolution.resolution.selected_event_id=ids[0]!;await f.reseal()}
 if(kind==='cycle'){const c=f.f.db.legacyNoteHistory.find((r:any)=>r.record_kind==='candidate'&&r.header.revision===1);c.header.parent_event_id=f.parents[0]!.event_id;c.header.revision=3}
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
it('orphan classification is bounded and does not turn missing publication into success',async()=>{
 for(const [kind,code] of [['parent','missing_parent'],['bootstrap','missing_bootstrap'],['conflict','missing_conflict']] as const){
  const f=await plannerFixture()
  if(kind==='parent')f.f.db.legacyNoteHistory=f.f.db.legacyNoteHistory.filter((r:any)=>r.event_id!==f.parents[0]!.event_id)
  if(kind==='bootstrap')f.f.db.projectBindings=[]
  if(kind==='conflict')f.f.db.legacyNoteHistory=f.f.db.legacyNoteHistory.filter((r:any)=>r.record_kind!=='group')
  const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toMatchObject({code});expect(f.f.db).toEqual(before)
 }
})
it('concurrent project/source change during async preparation invalidates the snapshot',async()=>{
 const f=await plannerFixture(),original=f.f.transaction as BrowserSyncTransaction;let count=0
 const tx:typeof original=async(...args)=>{const value=await original(...args);if(++count===1)f.f.db.localProjects[0].source_revision++;return value}
 const runtime=new BrowserResolutionPlanner(tx,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never,f.device)
 await expect(runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db.localProjects[0].source_revision).toBeGreaterThan(0)
})
it('keep_both future child referencing the proposed clone is not an allocated clone',async()=>{
 const f=await plannerFixture('keep_both'),{contentRow}=await import('./noteTransport.testFixture')
 await contentRow(f.f,f.sequence+1,{id:'retained-note',mutation:'update',revision:4,parent:f.resolution.header.event_id})
 const before=f.before();expect((await f.runtime.prepare(scope,f.sequence)).status.strategy).toBe('keep_both');expect(f.f.db).toEqual(before)
})
it('opaque token is not accepted by the existing prefix/ACK authority runtime',async()=>{
 const f=await plannerFixture(),p=await f.runtime.prepare(scope,f.sequence),before=f.before()
 await expect(f.f.proven.commit(p.token as never)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
it.each(['map-owned','format','selected parent','tombstone','retained route','parent revision'] as const)('authenticated but invalid %s payload is rejected by the planner, not just a test encoder',async kind=>{
 const f=await plannerFixture(kind==='retained route'?'keep_both':'choose_version')
 const result=f.resolution.result as any,decision=f.resolution.resolution as any
 if(kind==='map-owned'){result.note.source_type='mindmap';result.note.source_map_id='map';result.note.source_node_id='node'}
 if(kind==='format')result.note.content_format='markdown'
 if(kind==='selected parent')decision.selected_event_id=crypto.randomUUID()
 if(kind==='tombstone')result.operation='delete'
 if(kind==='retained route')decision.retained_note.stage_id='foreign-stage'
 if(kind==='parent revision'){f.resolution.header.revision++;const w=JSON.parse(f.received.wire_item);w.event.revision++;f.received.wire_item=JSON.stringify(w)}
 // Deliberately malicious sender material: real AEAD, invalid frozen payload.
 // Bypassing the encoder is restricted to this negative fixture, never production.
 await f.reseal(true);const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
it('genuine pending I2 is never admitted as a published parent',async()=>{
 const f=await plannerFixture(),{BrowserContentNoteIntents}=await import('./contentNoteIntents'),{note}=await import('./bootstrap.testFixture')
 const writer=new BrowserContentNoteIntents(f.f.transaction,f.f.localOwner,()=>true).bind(f.f.auth,f.f.bindings as never,f.f.keys as never)
 await writer.local.createNote(scope,(await writer.local.readSnapshot(scope,'p')).token,{...note('unpublished'),metadata:{},revision:0})
 const intent=(await writer.list(scope,'p'))[0]!,ids=[f.parents[0]!.event_id,intent.event_id].sort()
 f.resolution.header.parent_event_id=ids[0]!;f.resolution.header.additional_parent_event_ids=ids.slice(1);f.resolution.resolution.resolved_event_ids=ids
 if(f.resolution.resolution.strategy==='choose_version')f.resolution.resolution.selected_event_id=f.parents[0]!.event_id
 await f.reseal();const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toMatchObject({code:'missing_publication'});expect(f.f.db).toEqual(before)
})

it.each(['pull','prefix','ordinal'] as const)('corrupt current %s cursor cannot mint even a read-only token',async kind=>{
 const f=await plannerFixture(),cursor=f.f.db.cursors[0]
 if(kind==='pull')cursor.pull_cursor++
 if(kind==='prefix')cursor.proven_prefix=cursor.pull_cursor
 if(kind==='ordinal')cursor.next_local_ordinal++
 const before=f.before();await expect(f.runtime.prepare(scope,f.sequence)).rejects.toThrow();expect(f.f.db).toEqual(before)
})
