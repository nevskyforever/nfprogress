import {scope,at} from './bootstrap.testFixture'
import {contentLocalConflict} from './contentLocalConflict.testFixture'
import {contentRow} from './noteTransport.testFixture'
export async function receiveOwn(f:{db:Record<string,unknown[]> & {outbox:unknown[];inbox:unknown[]};sync:{commitInboundPage:Function}},sequence:number,out=f.db.outbox[0] as any){
 const item=JSON.parse(out.raw_body).items[0]
 await f.sync.commitInboundPage(scope,sequence-1,JSON.stringify({protocol_version:out.protocol_version,encrypted_sync_version:out.protocol_version,items:[{event:{...item.event,device_id:scope.deviceId,server_sequence:sequence},object:item.object}],next_cursor:sequence,has_more:false}))
 return f.db.inbox.find((r:any)=>r.server_sequence===sequence) as any
}
export async function mixedSelfEcho(options:{members?:1|2;accepted?:boolean;local?:'update'|'delete';newer?:boolean}={}){
 const f=await contentLocalConflict(options.local??'update','update',true);await f.content.apply(scope,3);await f.proven.advance(scope)
 if(options.local!=='delete')await f.writer.local.updateNote(scope,(await f.writer.local.readSnapshot(scope,'p')).token,'content-note',{content:'PRIVATE_LATER_SEALED'},at)
 await f.writer.seal(scope,'p',f.intent.event_id)
 const members=options.members??1,sequence=members+3
 if(members===2){await contentRow(f,4,{mutation:'delete',parent:f.root.event_id,compressed:true});await f.content.apply(scope,4);await f.proven.advance(scope)}
 if(options.accepted!==false)await f.accept(f.db.outbox[0],sequence)
 if(options.newer)await f.writer.local.updateNote(scope,(await f.writer.local.readSnapshot(scope,'p')).token,'content-note',{content:'PRIVATE_NEWER_WORKING'},at)
 const echo=await receiveOwn(f,sequence)
 return {...f,echo,sequence}
}
export const withoutInbox=(f:{db:Record<string,unknown[]>})=>structuredClone(Object.fromEntries(Object.entries(f.db).filter(([k])=>k!=='inbox')))
