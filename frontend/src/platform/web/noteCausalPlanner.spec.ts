// @vitest-environment node
import {describe,expect,it} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {imported,received} from './legacyNoteApply.testFixture'
import {validateNoteHistoryRecord} from './noteHistoryRecords'
import {validateBrowserInboxRecord} from './syncDurability'

describe('shared Note causal/candidate/proof planning through genuine owner',()=>{
 it('advances one immutable candidate and head per accepted create/update/delete',async()=>{
  const f=await imported()
  let parent:string|null=null
  for(const [revision,operation] of [[1,'upsert'],[2,'upsert'],[3,'delete']] as const){
   const row=await received(f,revision,revision,parent,operation)
   expect(await f.notes.apply(scope,revision)).toBe('applied')
   const history=(f.db.legacyNoteHistory??[]).map(value=>validateNoteHistoryRecord(value,scope))
   expect(history.filter(value=>value.record_kind==='candidate')).toHaveLength(revision)
   expect(history.find(value=>value.record_kind==='head')).toMatchObject({linear_head_event_id:row.event_id,head_revision:revision})
   expect(validateBrowserInboxRecord(f.db.inbox[revision-1],scope)).toMatchObject({state:'note_proven',note_proof:{outcome:'applied',header:{revision}}})
   parent=row.event_id
  }
  const saved=structuredClone(f.db)
  expect(await f.notes.apply(scope,3)).toBe('already_applied')
  expect(f.db).toEqual(saved)
 })

 it('rejects an orphan without publishing source, candidate, head or proof',async()=>{
  const f=await imported()
  await received(f,1,2,crypto.randomUUID())
  const saved=structuredClone(f.db)
  await expect(f.notes.apply(scope,1)).rejects.toMatchObject({code:'note_orphan'})
  expect(f.db).toEqual(saved)
 })

 it('a caller supplied virtual inventory cannot grant a durable commit',async()=>{
  const f=await imported()
  await received(f,1)
  const saved=structuredClone(f.db)
  await expect(f.notes.commit({virtual_inventory:structuredClone(saved)} as never)).rejects.toMatchObject({code:'stale_source'})
  expect(f.db).toEqual(saved)
 })
})
