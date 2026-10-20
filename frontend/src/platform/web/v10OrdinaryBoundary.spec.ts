// @vitest-environment node
import {afterEach,it,expect,vi} from 'vitest'
import {ordinaryBoundaryFixture} from './v10OrdinaryBoundary.testFixture'
import {scope,note,project} from './bootstrap.testFixture'
afterEach(()=>vi.restoreAllMocks())

for(const protocol of [2,3] as const)for(const strategy of ['choose_version','manual_merge','delete','keep_both'] as const)it(`STOP source contract protocol${protocol}/${strategy}: real AEAD is not independent ordinary authority`,async()=>{
 const f=await ordinaryBoundaryFixture(strategy,protocol,protocol===3),before=f.before()
 expect(await f.history()).toMatchObject({resolutions:1})
 const snapshot=await f.f.local.readSnapshot(scope,'p'),n=note('unqualified-local-probe');n.revision=0
 // The actual old source writer ALSO rejects the complete future history.
 await expect(f.f.local.createNote(scope,snapshot.token,n)).rejects.toMatchObject({code:'corrupt_record'})
 expect(f.before()).toEqual(before)
 // Negative AEAD fixture ONLY, not an applied/proven/remote-authority specimen.
 await f.sourceProbe(true)
 const changed=f.before();expect((changed.localProjects![0] as any).source_revision).toBe((before.localProjects![0] as any).source_revision+1)
 expect(changed.localNotes!.length).toBe(before.localNotes!.length+1)
 await f.f.local.withDecryptedSnapshot(scope,(await f.f.local.readSnapshot(scope,'p')).token,async opened=>expect(opened.notes.some(n=>n.note.id==='unqualified-local-probe')).toBe(true))
 expect(changed.legacyNoteHistory).toEqual(before.legacyNoteHistory);expect(changed.inbox).toEqual(before.inbox)
 expect(await f.history(false)).toMatchObject({resolutions:1}) // Original historical AEAD/proofs still authenticate.
 await expect(f.history()).rejects.toMatchObject({code:'corrupt_record'})
 await expect(f.h.history(scope)).rejects.toMatchObject({code:'corrupt_record'})
 await expect(f.g.prepare(scope)).rejects.toMatchObject({code:'corrupt_record'})
 await expect(f.runtime.run(scope)).rejects.toThrow();expect(f.before()).toEqual(changed)
})
it('STOP revision contract also rejects genuine AEAD revision drift with unchanged membership/project fields',async()=>{
 const f=await ordinaryBoundaryFixture(),before=f.before()
 await f.sourceProbe(false)
 const changed=f.before();expect(changed.localNotes).toEqual(before.localNotes)
 expect((changed.localProjects![0] as any).source_revision).toBe((before.localProjects![0] as any).source_revision+1)
 expect(await f.history(false)).toMatchObject({resolutions:1});await expect(f.history()).rejects.toThrow();await expect(f.g.prepare(scope)).rejects.toThrow();expect(f.before()).toEqual(changed)
})
it('old source-only owner rejects even unrelated project initialization once future history exists',async()=>{
 const f=await ordinaryBoundaryFixture(),before=f.before()
 await expect(f.f.local.initializeProject(scope,{project:project('later-project'),notes:[]})).rejects.toMatchObject({code:'corrupt_record'})
 expect(f.before()).toEqual(before)
})
for(const project of ['p','q'])for(const protocol of [2,3] as const)for(const compressed of protocol===2?[false]:[false,true])it(`complete mixed inventory blocks old ordinary owner ${project}/protocol${protocol}/ID${compressed?1:0}`,async()=>{
 const f=await ordinaryBoundaryFixture('keep_both',3,false,false,project==='q');if(project==='q')await f.otherProject()
 const incoming=await f.incomingNote(protocol,compressed,project),before=f.before(),reader=protocol===2?f.legacy:f.content
 expect(await f.history()).toMatchObject({resolutions:1})
 await expect(reader.prepare(scope,incoming.sequence)).rejects.toMatchObject({code:'corrupt_record'})
 expect(await f.runtime.run(scope)).toMatchObject({applied:[],blocker:{sequence:incoming.sequence,kind:'unsupported_route'}})
 await f.j.replayInboundPage(scope,incoming.since,incoming.page);if(project==='q')(before.cursors[0] as any).proven_prefix=incoming.sequence-1;expect(f.before()).toEqual(before)
})
for(const order of [false,true])for(const compressed of [false,true])it(`complete mixed inventory blocks old ${order?'StageOrder':'Stage'} owner ID${compressed?1:0}`,async()=>{
 const f=await ordinaryBoundaryFixture(),incoming=await f.incomingStage(order,compressed),before=f.before()
 expect(await f.history()).toMatchObject({resolutions:1})
 await expect((order?f.order:f.stage).prepare(scope,incoming.sequence)).rejects.toMatchObject({code:'corrupt_record'})
 expect(await f.runtime.run(scope)).toMatchObject({applied:[],blocker:{sequence:incoming.sequence,kind:'unsupported_route'}});expect(f.before()).toEqual(before)
})
for(const compressed of [false,true])it(`Metadata is an existing accepted exact-reference owner, NOT the global parser blocker ID${compressed?1:0}`,async()=>{
 const f=await ordinaryBoundaryFixture(),incoming=await f.incomingMetadata('p',compressed),before=f.before()
 expect(await f.runtime.run(scope)).toMatchObject({applied:[],blocker:{sequence:incoming.sequence,kind:'unsupported_route'}});expect(f.before()).toEqual(before)
 // Isolated owner contract probe at the FIRST pending event. No K route enabled.
 expect(await f.metadata.apply(scope,incoming.event as never,f.f.auth,f.f.bindings as never,f.f.keys as never)).toBe('applied')
 const after=f.before();expect(after.localNotes).toEqual(before.localNotes);expect(after.localProjects).toEqual(before.localProjects)
 expect(after.legacyNoteHistory).toEqual(before.legacyNoteHistory)
 expect(await f.history()).toMatchObject({resolutions:1})
 expect(await f.g.calculate(await f.g.prepare(scope))).toMatchObject({candidate_proven_prefix:incoming.sequence,ackAuthorized:false})
 await f.j.replayInboundPage(scope,incoming.since,incoming.page)
 expect((f.f.db.cursors[0] as any).ack_cursor).toBe(0)
})
