import {readerFrame} from './canonicalReaders.testFixture'
import type {StructuralEvent} from '@/cloud/stageCodec'
import {stageSetup,stageRow,scope} from './stageApply.testFixture'
import {BrowserStageOrderApply} from './stageOrderApply'
export {scope}
export async function orderSetup(count=1){const f=await stageSetup();const stages=[];for(let i=0;i<count;i++){const e=await stageRow(f,i+2,{change:e=>{e.header.entity_id='s'+i}});await f.stages.apply(scope,i+2);stages.push(e.event)}return{...f,stageEvents:stages,orders:new BrowserStageOrderApply(f.transaction,()=>true).bind(f.auth,f.bindings as never,f.keys as never)}}
export async function orderRow(f:Awaited<ReturnType<typeof orderSetup>>,seq:number,options:Parameters<typeof stageRow>[2]={}){let event!:StructuralEvent;return stageRow(f,seq,{...options,compressed:false,frameTransform:options.compressed?()=>{const frame=readerFrame({id:3,version:event.version,event},true);if(frame[11]!==1)throw Error('expected_ID1');return frame}:options.frameTransform,change:e=>{e.header.entity_type='stage_order';e.header.entity_id='stage_order';e.stage=null;e.stage_ids=f.stageEvents.map(s=>s.header.entity_id).reverse();e.stage_heads=Object.fromEntries(f.stageEvents.map(s=>[s.header.entity_id,[s.header.event_id]]));options.change?.(e);event=e}})}
