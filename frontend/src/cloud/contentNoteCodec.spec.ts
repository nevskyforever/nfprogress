import {describe,it,expect} from 'vitest'
import fixture from './__fixtures__/contentNoteCodecV1.json'
import {frameContentNote,unframeContentNote,type ContentNoteEvent} from './contentNoteCodec'
import {decodeNoteSyncPlaintext} from './noteSyncCodec'
import {decodeNoteSyncResolutionV2} from './noteSyncResolutionV2Codec'
import {unframeStructuralEvent} from './stageCodec'
import {unframeProjectMetadata} from './projectMetadataCodec'
import {unframeCatalogEvent} from './accountCatalogCodec'
const hex=(bytes:Uint8Array)=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')
const base=()=>structuredClone(fixture.examples[0]!.event) as ContentNoteEvent
const unchecked=(e:unknown)=>{const payload=new TextEncoder().encode(JSON.stringify(e,Object.keys(e as object).sort()));return payload}
describe('C18 framed Note contract',()=>{
  for(const example of fixture.examples) it(example.name+' cross-language canonical bytes',()=>{
    const e=example.event as ContentNoteEvent,frame=frameContentNote(e)
    expect(hex(frame)).toBe(example.frame_hex)
    expect(new TextDecoder().decode(frame.subarray(20))).toBe(example.canonical_json)
    expect(hex(frame.subarray(20))).toBe(example.canonical_utf8_hex)
    expect(unframeContentNote(frame)).toEqual(e)
    for(const reader of [decodeNoteSyncPlaintext,decodeNoteSyncResolutionV2,unframeStructuralEvent,unframeProjectMetadata,unframeCatalogEvent]) expect(()=>reader(frame)).toThrow()
  })
  it('no cross-reader/version/compression fallback',()=>{
    const good=frameContentNote(base())
    for(const [index,value] of [[8,2],[9,1],[9,2],[9,3],[9,4],[9,5],[9,6],[9,7],[10,2],[11,1],[12,255]]){const bad=good.slice();bad[index!]=value!;expect(()=>unframeContentNote(bad)).toThrow()}
    expect(()=>unframeContentNote(unchecked({version:1}))).toThrow()
  })
  it('map ownership, formats, extension metadata and exact dependency scope are closed',()=>{
    const bad=base();if(bad.event.version!==1)throw Error()
    bad.event.note.source_type='mindmap';expect(()=>frameContentNote(bad)).toThrow('content_note_map_owned')
    const extra=base();if(extra.event.version!==1||!('metadata'in extra.event.note))throw Error()
    extra.event.note.metadata={local_path:'/private'};expect(()=>frameContentNote(extra)).toThrow('content_note_unsupported_source')
    const wrong=base();wrong.dependencies.stage_event_ids=['123e4567-e89b-42d3-a456-000000000800'];expect(()=>frameContentNote(wrong)).toThrow()
  })
  it('content, counts, JSON depth and Unicode are bounded',()=>{
    const bad=base();if(bad.event.version!==1||!('content'in bad.event.note))throw Error()
    bad.event.note.content='x'.repeat(7*1024*1024+1);expect(()=>frameContentNote(bad)).toThrow('content_note_resource_limit')
    bad.event.note.content='\ud800';expect(()=>frameContentNote(bad)).toThrow()
    bad.event.note.content='x';bad.event.note.tags=Array(4097).fill('t');expect(()=>frameContentNote(bad)).toThrow('content_note_resource_limit')
  })
})
