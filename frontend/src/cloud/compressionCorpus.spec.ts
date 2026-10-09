// @vitest-environment node
import {it,expect} from 'vitest'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {frameProjectMetadata} from './projectMetadataCodec'
import {frameStructuralEvent} from './stageCodec'
import {frameCatalogEvent} from './accountCatalogCodec'
import {frameContentNote} from './contentNoteCodec'
import {frameMapEvent} from './mapCodec'
import {frameDocumentEvent} from './documentCodec'
import {frameProgressEvent} from './progressCodec'
import {frameGameEvent} from './gameCodec'
it('benchmarks validated canonical entity bytes, with separately labelled non-entity policy probes',async()=>{
 const corpus=JSON.parse(execFileSync(process.execPath,[fileURLToPath(new URL('../../../scripts/compression/corpus.mjs',import.meta.url))],{maxBuffer:32*1024*1024}).toString()) as Array<{name:string;canonical:string}>
 const codecs=new Set<number>()
 for(const c of corpus){if(c.name.includes('probe-not-entity'))continue;const e=JSON.parse(c.canonical);let frame:Uint8Array
  if(c.name.startsWith('projectMetadata')||c.name.startsWith('metadata'))frame=frameProjectMetadata(e)
  else if(c.name.startsWith('stage'))frame=frameStructuralEvent(e)
  else if(c.name.startsWith('accountCatalog')||c.name.startsWith('catalog'))frame=frameCatalogEvent(e)
  else if(c.name.startsWith('contentNote')||c.name.startsWith('note-'))frame=frameContentNote(e)
  else if(c.name.startsWith('map')||c.name.startsWith('large-map'))frame=await frameMapEvent(e)
  else if(c.name.startsWith('document'))frame=await frameDocumentEvent(e)
  else if(c.name.startsWith('progress'))frame=await frameProgressEvent(e)
  else frame=frameGameEvent(e)
  codecs.add(frame[9]!);expect(frame[11]).toBe(0);expect(Buffer.from(frame.subarray(20)).toString()).toBe(c.canonical)
 }
 expect([...codecs].sort((a,b)=>a-b)).toEqual([1,2,3,4,5,8,9,10,11,12,13])
},30000)
