import {scope,at} from './bootstrap.testFixture'
import {contentLocalConflict,localVersion} from './contentLocalConflict.testFixture'
import {contentRow} from './noteTransport.testFixture'
export async function postSeal(accepted=false,mutation:'update'|'delete'='update',compressed=false){
 const f=await contentLocalConflict();await f.content.apply(scope,3);await f.proven.advance(scope)
 const frozen=structuredClone(localVersion(f)),first=structuredClone(f.db.inbox[2]),group=structuredClone(f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='group')) as any
 await f.writer.local.updateNote(scope,(await f.writer.local.readSnapshot(scope,'p')).token,'content-note',{content:'PRIVATE_POST_CONFLICT_COALESCED'},at)
 await f.writer.seal(scope,'p',f.intent.event_id);if(accepted)await f.accept(f.db.outbox[0],20)
 const r2=await contentRow(f,4,{mutation,parent:f.root.event_id,compressed})
 return {...f,frozen,first,group,r2}
}
export const working=(f:{db:Record<string,unknown[]>})=>structuredClone({local:f.db.localNotes,project:f.db.localProjects,intents:f.db.legacyNoteIntents,out:f.db.outbox,receipts:f.db.receipts})
