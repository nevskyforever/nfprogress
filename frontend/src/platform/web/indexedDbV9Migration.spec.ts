// @vitest-environment node
import {expect,it} from 'vitest'
import {validateBrowserV9State} from './indexedDbV9Migration'
import {scope,fixture,amk} from './bootstrap.testFixture'
import {mixedSelfEcho} from './mixedSelfEcho.testFixture'
import {contentAuthorityFixture} from './contentAuthority.testFixture'
import {authenticateContentAuthorityInventory} from './contentAuthorityInventory'
import {validateBrowserV8State} from './contentAuthorityMigration'
const names=['outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const stores=(f:{db:Record<string,unknown[]>})=>names.map(n=>structuredClone(f.db[n]!))
function preserved(data:unknown[][]){const before=structuredClone(data);validateBrowserV9State([scope],data);expect(data).toEqual(before)}
function rejected(data:unknown[][]){const before=structuredClone(data);expect(()=>validateBrowserV9State([scope],data)).toThrow();expect(data).toEqual(before)}
it('empty v9 inventory has no fabricated cursor or authority',()=>preserved(names.map(()=>[])))
it('initial encrypted Legacy cohort retains all source, outbox, cursor and history bytes',async()=>{const f=await fixture();await f.capture.capture(scope,f.registered);preserved(stores(f))})
it.each([false,true])('accepted mixed Legacy/Content history and frozen local versions survive newer=%s',async newer=>{const f=await mixedSelfEcho({accepted:true,newer});await f.notes.apply(scope,f.sequence);await f.proven.advance(scope);const data=stores(f);validateBrowserV8State([scope],data);preserved(data)})
it.each(['intent','sealed','accepted','echo'] as const)('real AEAD v9 %s I2/C3/R2/inbox9 dispatch preserves evidence without activating authority',async kind=>{
 for(const compressed of [false,true]){const f=await contentAuthorityFixture(compressed,kind);await authenticateContentAuthorityInventory(scope,f.inventory(),amk,()=>true);preserved(stores(f));expect(()=>validateBrowserV8State([scope],stores(f))).toThrow()}
})
it.each(names)('rejects malformed v9 %s without repair',async name=>{const f=await mixedSelfEcho({newer:true});const data=stores(f);expect(data[names.indexOf(name)]!.length).toBeGreaterThan(0);(data[names.indexOf(name)]![0] as any).record_version=99;rejected(data)})
it.each(['foreign account','wrong device','bootstrap','missing source','missing parent','duplicate event','duplicate sequence','ordinal','missing cursor','pull','ack','prefix','future history','future inbox','orphan receipt','missing outbox','malformed intent','malformed candidate','self echo prefix','missing metadata','missing stage','missing intent parent'] as const)('v9 rejects %s at the structural boundary',async change=>{
 const f=await contentAuthorityFixture(false,['malformed intent','missing metadata','missing stage','missing intent parent'].includes(change)?'intent':'echo'),data=stores(f)
 const [out,inbox,cursors,receipts,bindings,,projects,,history,intents]=data as any[][],c=cursors![0]
 switch(change){
 case 'foreign account': out![0].account_id=scope.deviceId;break
 case 'wrong device': out![0].device_id=scope.accountId;break
 case 'bootstrap': bindings![0].bootstrap_id=crypto.randomUUID();break
 case 'missing source': projects!.length=0;break
 case 'missing parent': history!.splice(history!.findIndex(h=>h.record_kind==='candidate'&&h.record_version===2),1);break
 case 'duplicate event': out!.push(structuredClone(out![0]));break
 case 'duplicate sequence': inbox!.push({...inbox![0],event_id:crypto.randomUUID()});break
 case 'ordinal': c.next_local_ordinal++;break
 case 'missing cursor': cursors!.length=0;break
 case 'pull': c.pull_cursor++;break
 case 'ack': c.ack_cursor=c.pull_cursor+1;break
 case 'prefix': c.proven_prefix=c.pull_cursor+1;break
 case 'future history': history!.push({...history![0],record_version:4,record_kind:'resolution'});break
 case 'future inbox': inbox![0].record_version=10;break
 case 'orphan receipt': receipts![0].event_id=crypto.randomUUID();break
 case 'missing outbox': out!.length=0;break
 case 'malformed intent': intents![0].intent_envelope.nonce='invalid';break
 case 'malformed candidate': history!.find(h=>h.record_version===3).authorship_envelope.nonce='invalid';break
 case 'self echo prefix': c.proven_prefix=3;break
 case 'missing metadata': intents![0].dependencies.metadata_event_id=crypto.randomUUID();break
 case 'missing stage': intents![0].dependencies.stage_event_ids=[crypto.randomUUID()];break
 case 'missing intent parent': intents![0].parent_event_id=crypto.randomUUID();break
 }
 rejected(data)
})
it('keyless acceptance never substitutes for current-key authentication after unlock',async()=>{
 const f=await contentAuthorityFixture();const c=f.db.legacyNoteHistory!.find((r:any)=>r.record_version===3) as any
 c.authorship_envelope.ciphertext=c.authorship_envelope.ciphertext.replace(/^./,c.authorship_envelope.ciphertext[0]==='A'?'B':'A')
 preserved(stores(f));const before=structuredClone(f.db)
 await expect(authenticateContentAuthorityInventory(scope,f.inventory(),amk,()=>true)).rejects.toThrow()
 await expect(f.proven.prepare(scope)).rejects.toThrow();expect(f.db).toEqual(before)
})
it('revoked authentication fails before authority checks and keeps encrypted evidence',async()=>{const f=await contentAuthorityFixture(false,'intent');const before=structuredClone(f.db);await expect(authenticateContentAuthorityInventory(scope,f.inventory(),amk,()=>false)).rejects.toThrow();expect(f.db).toEqual(before)})
