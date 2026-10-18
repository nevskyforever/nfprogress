// @vitest-environment node
import {it,expect} from 'vitest'
import {validateBrowserV8State} from './contentAuthorityMigration'
import {scope,fixture} from './bootstrap.testFixture'
import {mixedSelfEcho} from './mixedSelfEcho.testFixture'
import {contentConflictSetup} from './contentConflict.testFixture'
import {contentAuthorityFixture} from './contentAuthority.testFixture'
import {contentRow} from './noteTransport.testFixture'
const names=['outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
const stores=(f:{db:Record<string,unknown[]>})=>names.map(n=>structuredClone(f.db[n]!))
it('empty disposable v8 structural profile is unchanged',()=>{const data=names.map(()=>[]);validateBrowserV8State([scope],data);expect(data).toEqual(names.map(()=>[]))})
it.each(['unsealed','sealed','accepted'] as const)('populated v8 %s Legacy lifecycle, peer Content proof2/mixed frozen history remains byte-exact',async state=>{
 const f=await mixedSelfEcho({accepted:true,newer:true});await f.notes.apply(scope,f.sequence);await f.proven.advance(scope)
 if(state==='unsealed'){}else{const i=(await f.writer.list(scope,'p'))[0]!;await f.writer.seal(scope,'p',i.event_id);if(state==='accepted')await f.accept(f.db.outbox[1],f.sequence+2)}
 ;(f.db.cursors[0] as any).ack_cursor=(f.db.cursors[0] as any).proven_prefix
 await contentRow(f,f.sequence+1,{id:'own-barrier',change:e=>{e.device_id=scope.deviceId}})
 const data=stores(f),old=structuredClone(data);validateBrowserV8State([scope],data);expect(data).toEqual(old)
})
it.each(names)('corrupt v8 %s row is rejected without modifying input',async name=>{const f=await mixedSelfEcho({newer:true});const data=stores(f),index=names.indexOf(name);expect(data[index]!.length).toBeGreaterThan(0);(data[index]![0] as any).record_version=99;const old=structuredClone(data);expect(()=>validateBrowserV8State([scope],data)).toThrow();expect(data).toEqual(old)})
it('initial Legacy cohort and encrypted source preserved',async()=>{const f=await fixture();await f.capture.capture(scope,f.registered);const data=stores(f),old=structuredClone(data);validateBrowserV8State([scope],data);expect(data).toEqual(old)})

it.each([false,true])('populated peer Content proof1 / peer conflict1 preserved ID1=%s',async compressed=>{const f=await contentConflictSetup(false,'html',compressed);await f.content.apply(scope,4);await f.proven.advance(scope);const data=stores(f),old=structuredClone(data);validateBrowserV8State([scope],data);expect(data).toEqual(old)})
it('v8 refuses prematurely injected new formats; no retroactive authority',async()=>{const f=await contentAuthorityFixture();const data=stores(f),old=structuredClone(data);expect(()=>validateBrowserV8State([scope],data)).toThrow();expect(data).toEqual(old)})
it('keyless migration does not claim hash/AEAD authentication; corrupted crypto is blocked after unlock',async()=>{const f=await mixedSelfEcho();const c=f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='candidate') as any;c.record_digest='0'.repeat(64);const data=stores(f),old=structuredClone(data);validateBrowserV8State([scope],data);expect(data).toEqual(old);await expect(f.proven.prepare(scope)).rejects.toThrow()})
