import {BrowserContentNoteIntents} from './contentNoteIntents'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {scope,at,note} from './bootstrap.testFixture'
export {scope,at,note}
export async function contentWriterSetup(peer=false){
 const f=await routeSetup(),content=new BrowserContentNoteApplyRuntime(f.notes)
 if(peer){await contentRow(f,2);await content.apply(scope,2)}
 let active=true
 const writer=new BrowserContentNoteIntents(f.transaction,f.localOwner,()=>active).bind(f.auth,f.bindings as never,f.keys as never)
 return{...f,content,cw:writer,invalidate:()=>{active=false}}
}
export const sourceToken=async(f:{local:{readSnapshot:Function}})=>(await f.local.readSnapshot(scope,'p')).token
export const fresh=(id='new')=>({...note(id),metadata:{},revision:0})
export const update=async(f:Awaited<ReturnType<typeof contentWriterSetup>>,id='content-note',content='PRIVATE_CONTENT_EDIT')=>f.cw.local.updateNote(scope,await sourceToken(f),id,{content},at)
