import {routeSetup,contentRow} from './noteTransport.testFixture'
import {contentStageSetup,stageContent} from './contentStage.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {received} from './legacyNoteApply.testFixture'
import {scope} from './bootstrap.testFixture'
export async function contentConflictBase(stage=false,format:'html'|'plain'='html',compressed=false){
 const base=stage?await contentStageSetup():await routeSetup(),f={...base,content:new BrowserContentNoteApplyRuntime(base.notes)},start=stage?3:2
 const incoming=(seq:number,options:Parameters<typeof contentRow>[2]={})=>{const change=options.change,opts={compressed,...options,change:(e:Parameters<NonNullable<typeof change>>[0])=>{(e.event as any).note.content_format=format;change?.(e)}};return stage?stageContent(f as Awaited<ReturnType<typeof contentStageSetup>>,seq,opts):contentRow(f as Awaited<ReturnType<typeof routeSetup>>,seq,opts)}
 return {...f,start,incoming}
}
export async function contentConflictSetup(stage=false,format:'html'|'plain'='html',compressed=false,mutation:'update'|'delete'='update',winnerLegacy=false,incomingLegacy=false){
 const f=await contentConflictBase(stage,format,compressed),p=await f.incoming(f.start);await f.content.apply(scope,f.start)
 // Mixed transport remains within frozen Legacy-compatible project HTML.
 const legacy=winnerLegacy?await received(f,f.start+1,2,p.row.event_id,'upsert',v=>{v.note.metadata={}},'content-note'):null
 const content=legacy?null:await f.incoming(f.start+1,{mutation:'update',parent:p.row.event_id})
 if(legacy)await f.notes.apply(scope,f.start+1);else await f.content.apply(scope,f.start+1)
 const sibling=incomingLegacy?await received(f,f.start+2,2,p.row.event_id,mutation==='delete'?'delete':'upsert',v=>{if('metadata'in v.note)v.note.metadata={}},'content-note'):null
 const b=sibling?null:await f.incoming(f.start+2,{mutation,parent:p.row.event_id,change:e=>{e.device_id='55555555-5555-4555-8555-555555555555'}})
 return {...f,parent:p,winner:legacy??content!.row,sibling:sibling??b!.row}
}
export const conflictGroup=(f:{db:Record<string,unknown[]>})=>f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='group') as import('./noteHistoryRecords').BrowserNoteConflictGroup
