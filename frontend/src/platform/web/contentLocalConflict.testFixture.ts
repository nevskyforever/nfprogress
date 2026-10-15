import {routeSetup,contentRow} from './noteTransport.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {scope,at} from './bootstrap.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
export async function contentLocalConflict(local:'update'|'delete'='update',remote:'update'|'delete'='update',compressed=false){
 const f=await routeSetup(),root=await received(f,2,1,null,'upsert',p=>{p.note.metadata={}},'content-note');await f.notes.apply(scope,2);await f.proven.advance(scope)
 const token=(await f.writer.local.readSnapshot(scope,'p')).token
 if(local==='delete')await f.writer.local.tombstoneNote(scope,token,'content-note',at);else await f.writer.local.updateNote(scope,token,'content-note',{content:'PRIVATE_LOCAL_PENDING'},at)
 const intent=(await f.writer.list(scope,'p'))[0]!,incoming=await contentRow(f,3,{mutation:remote,parent:root.event_id,compressed})
 return {...f,root,intent,incoming,content:new BrowserContentNoteApplyRuntime(f.notes)}
}
export const localVersion=(f:{db:Record<string,unknown[]>})=>f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='local_version') as import('./noteHistoryRecords').BrowserNoteLocalVersion
