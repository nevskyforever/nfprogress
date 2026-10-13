import {imported,received} from './legacyNoteApply.testFixture'
import {scope,at} from './bootstrap.testFixture'
export async function unsealedConflict(local='update',remote='upsert'){
 const f=await imported(),root=await received(f,1);await f.notes.apply(scope,1)
 const t=(await f.writer.local.readSnapshot(scope,'p')).token
 if(local==='delete')await f.writer.local.tombstoneNote(scope,t,'remote-note',at);else await f.writer.local.updateNote(scope,t,'remote-note',{content:'PRIVATE_LOCAL_FROZEN'},at)
 const i=(await f.writer.list(scope,'p'))[0]!,peer=await received(f,2,2,root.event_id,remote,v=>{if('content'in v.note)v.note.content='PRIVATE_REMOTE_FROZEN'})
 return{...f,root,i,peer}
}
export const frozen=(f:Awaited<ReturnType<typeof unsealedConflict>>)=>f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='local_version') as any
export const group=(f:Awaited<ReturnType<typeof unsealedConflict>>)=>f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='group') as any
export const openLocal=(f:Awaited<ReturnType<typeof unsealedConflict>>)=>f.noteHistory.withDecryptedLocalVersion(scope,'p','remote-note',frozen(f).version_id,async p=>p)
