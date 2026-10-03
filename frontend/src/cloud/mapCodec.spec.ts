// @vitest-environment node
import {describe,it,expect} from 'vitest'
import fixture from './__fixtures__/mapCodecV1.json'
import {frameMapEvent,unframeMapEvent,validateMap,validateMapEvent,mapEntityId,type MapEvent} from './mapCodec'
import {encryptObjectBytes,decryptObjectBytes,asAccountMasterKey} from '@/crypto'
const event=()=>structuredClone(fixture.examples[2]!.event) as MapEvent
const hex=(bytes:Uint8Array)=>Buffer.from(bytes).toString('hex')
describe('codec9 owning maps',()=>{
 it('bounds aggregate UTF-8 before serializing otherwise valid individual topics',()=>{
  const data={nodeData:{id:'root',topic:'root',children:Array.from({length:30},(_,i)=>({id:`large-${i}`,topic:'a'.repeat(300000),children:[]}))}}
  expect(()=>validateMap(data,{})).toThrow('map_resource_limit')
  expect(()=>validateMap({nodeData:{id:'root',topic:'a'.repeat(300000),children:[]}},{})).not.toThrow()
 })
 it('admits existing editor depth 512 and rejects deeper trees and floating parent cycles',async()=>{
  const e=event();let node:Record<string,unknown>={id:'deep-512',topic:'leaf',children:[]}
  for(let depth=511;depth>=0;depth--)node={id:`deep-${depth}`,topic:'node',children:[node]}
  e.map={data:{nodeData:node},annotations:{}}
  const bytes=await frameMapEvent(e);expect(hex(await frameMapEvent(await unframeMapEvent(bytes)))).toBe(hex(bytes))
  e.map.data.nodeData={id:'too-deep',topic:'node',children:[node]}
  await expect(frameMapEvent(e)).rejects.toThrow('map_resource_limit')
  e.map.data={nodeData:{id:'root',topic:'root',children:[]},nfprogressFloatingItems:[
   {id:'a',kind:'node',text:'A',x:1,y:1,parentId:'b'},
   {id:'b',kind:'node',text:'B',x:2,y:2,parentId:'a'}]}
  expect(()=>validateMap(e.map!.data,e.map!.annotations)).toThrow('invalid_map_payload')
 })
 it('matches all independent canonical/frame vectors including fractional coordinates',async()=>{
  for(const v of fixture.examples){const e=v.event as MapEvent;await validateMapEvent(e);const frame=await frameMapEvent(e);expect(hex(frame)).toBe(v.frame_hex);expect(await unframeMapEvent(frame)).toEqual(e)}
 })
 it('preserves native/legacy duplicates only when the same stable logical text agrees',()=>{
  const e=event();e.map!.data.nfprogressFloatingItems=[{id:'note-1',kind:'note',text:'Map Note text',x:10,y:20}]
  expect(validateMap(e.map!.data,e.map!.annotations).size).toBe(1)
  e.map!.data.nfprogressFloatingItems=[{id:'note-1',kind:'note',text:'Different text',x:10,y:20}]
  expect(()=>validateMap(e.map!.data,e.map!.annotations)).toThrow('map_note_link_invalid')
 })
 it('fails closed on unknown data, duplicate identities, missing graph references and annotations',()=>{
  for(const mutate of [(e:MapEvent)=>{e.map!.data.customExtension={text:'preserve source'}},(e:MapEvent)=>{(e.map!.data.nodeData as {children:unknown[]}).children.push({id:'root',topic:'duplicate',children:[]})},(e:MapEvent)=>{e.map!.data.arrows=[{id:'a',from:'root',to:'foreign'}]},(e:MapEvent)=>{delete e.map!.annotations['note-1']}]){const e=event();mutate(e);expect(()=>validateMap(e.map!.data,e.map!.annotations)).toThrow()}
 })
 it('rejects codec/compression/length and exact owner substitution without fallback',async()=>{
  const bytes=await frameMapEvent(event());for(const offset of [9,10,11,12]){const corrupt=bytes.slice();corrupt[offset]=corrupt[offset]!^1;await expect(unframeMapEvent(corrupt)).rejects.toThrow()}
  const e=event();e.header.stage_id='S1';e.header.stage_event_ids=[fixture.examples[1]!.event.header.stage_event_ids[0]!];await expect(validateMapEvent(e)).rejects.toThrow()
  expect(await mapEntityId('S1')).not.toBe(await mapEntityId('S2'))
 })
 it('uses unchanged C11 and rejects project/stage/entity identity substitutions',async()=>{
  const e=event(),amk=asAccountMasterKey(new Uint8Array(32)),identity={userId:e.header.account_id,projectId:e.header.project_id,entityType:'map',entityId:e.header.entity_id}
  const bytes=await frameMapEvent(e),sealed=await encryptObjectBytes(amk,identity,bytes)
  expect(await decryptObjectBytes(amk,identity,sealed)).toEqual(bytes)
  for(const bad of [{...identity,projectId:'P2'},{...identity,entityType:'note'},{...identity,entityType:'stage'},{...identity,entityType:'project_metadata'},{...identity,entityId:await mapEntityId('S1')},{...identity,entityId:await mapEntityId('S2')}])await expect(decryptObjectBytes(amk,bad,sealed)).rejects.toThrow()
 })
})
