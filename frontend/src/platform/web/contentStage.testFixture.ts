import {scope} from './bootstrap.testFixture'
import {stageSetup,stageRow} from './stageApply.testFixture'
import {contentRow,routeSetup} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
export async function contentStageSetup(){const f=await stageSetup(),a=await stageRow(f,2);await f.stages.apply(scope,2);return{...f,a,m:{event:f.metadataEvent},content:new BrowserContentNoteApplyRuntime(f.notes)}}
export async function stageContent(f:Awaited<ReturnType<typeof contentStageSetup>>,seq=3,options:Parameters<typeof contentRow>[2] & {stage?:string|null;refs?:string[]}={}){
 const {stage='s',refs=[f.a.event.header.event_id],change,...rest}=options
 return contentRow(f as unknown as Awaited<ReturnType<typeof routeSetup>>,seq,{...rest,change:e=>{(e.event as any).note.stage_id=stage;e.dependencies.stage_event_ids=stage===null?[]:refs;change?.(e)}})
}
