// @vitest-environment node
import{describe,expect,it}from'vitest'
import{fixture,scope}from'./bootstrap.testFixture'
import{imported,received}from'./legacyNoteApply.testFixture'
import{validateBrowserV7State}from'./noteIntentMigration'
import{WEB_DATABASE_VERSION}from'./persistence'
const names=['outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory']
const rows=(f:Awaited<ReturnType<typeof fixture>>)=>names.map(s=>structuredClone(f.db[s]!))
describe('C21.1.16 exact v7→v8 migration',()=>{
 it('v8 one dedicated store, valid empty v7 unchanged and zero inferred intents',()=>{expect(WEB_DATABASE_VERSION).toBe(8);const data=names.map(()=>[]),old=structuredClone(data);validateBrowserV7State([scope],data);expect(data).toEqual(old)})
 it('initial candidates/source anchors and all old data preserved exactly',async()=>{const f=await fixture();await f.capture.capture(scope,f.registered);const data=rows(f),old=structuredClone(data);validateBrowserV7State([scope],data);expect(data).toEqual(old)})
 it('peer applied+conflict4/full group history migrate without synthesized intents',async()=>{const f=await imported(),root=await received(f,1);await f.notes.apply(scope,1);await received(f,2,2,root.event_id);await f.notes.apply(scope,2);await received(f,3,2,root.event_id,'delete');await f.notes.apply(scope,3);const data=rows(f),old=structuredClone(data);validateBrowserV7State([scope],data);expect(data).toEqual(old)})
 it.each([0,1,2,3,4,6,7,8])('corrupt v7 store%s refuses upgrade',async i=>{const f=await fixture();await f.capture.capture(scope,f.registered);await f.accept(f.db.outbox[0],1);if(i===1){const x=await received(f,2);expect(x).toBeDefined()}const data=rows(f);(data[i]![0] as any).record_version=99;expect(()=>validateBrowserV7State([scope],data)).toThrow()})
 it('candidate wrong lineage or missing parent fails structural validation',async()=>{const f=await fixture();await f.capture.capture(scope,f.registered);const data=rows(f);(data[8]![0] as any).bootstrap_id=crypto.randomUUID();expect(()=>validateBrowserV7State([scope],data)).toThrow()})
 it('v7 cannot contain future local_sealed candidate or extra store data',async()=>{const f=await fixture();await f.capture.capture(scope,f.registered);const data=rows(f);(data[8]!.find((r:any)=>r.record_kind==='candidate') as any).origin='local_sealed';expect(()=>validateBrowserV7State([scope],data)).toThrow();expect(()=>validateBrowserV7State([scope],[...rows(f),[]])).toThrow()})
})
