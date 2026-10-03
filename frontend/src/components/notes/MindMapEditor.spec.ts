import {mount,flushPromises} from '@vue/test-utils'
import {createPinia} from 'pinia'
import {describe,it,expect,vi} from 'vitest'
import MindMapEditor from './MindMapEditor.vue'
import {mindMapFixture} from '@/test/noteFixtures'
describe('editor lifetime map CAS',()=>{
 it('keeps the originally rendered heads across a background refresh and advances them only after save',async()=>{
  vi.useFakeTimers()
  const original={owner:{heads:['A']}},fresh={owner:{heads:['B']}},next={owner:{heads:['C']}}
  const map=mindMapFixture({expected_heads:original});const persist=vi.fn(async()=>({...map,expected_heads:next}))
  const wrapper=mount(MindMapEditor,{props:{map,persist,importXMind:vi.fn()},global:{plugins:[createPinia()],stubs:{IonIcon:true,IonSpinner:true}}})
  const frame=wrapper.find('iframe');let events:Array<{type:string;payload?:string}>=[{type:'ready'}];const takeEvents=()=>{const out=JSON.stringify(events);events=[];return out}
  Object.defineProperty(frame.element,'contentWindow',{value:{nfprogressMindMap:{initialize:vi.fn(),getDataString:()=>null,takeEvents},addEventListener:vi.fn(),removeEventListener:vi.fn()},configurable:true})
  await frame.trigger('load');await wrapper.setProps({map:{...map,expected_heads:fresh}})
  events=[{type:'save',payload:JSON.stringify({nodeData:{id:'root',topic:'First edit',children:[]}})}];await vi.advanceTimersByTimeAsync(150);await flushPromises()
  expect(persist).toHaveBeenLastCalledWith(expect.anything(),{projectId:map.project_id,stageId:map.stage_id},original)
  events=[{type:'save',payload:JSON.stringify({nodeData:{id:'root',topic:'Second edit',children:[]}})}];await vi.advanceTimersByTimeAsync(150);await flushPromises()
  expect(persist).toHaveBeenLastCalledWith(expect.anything(),expect.anything(),next)
  wrapper.unmount();vi.useRealTimers()
 })
})
