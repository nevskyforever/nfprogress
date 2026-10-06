// @vitest-environment node
import {expect,it} from 'vitest'
import documents from './__fixtures__/documentCodecV1.json'
import progress from './__fixtures__/progressCodecV1.json'
import metadata from './__fixtures__/projectMetadataV2.json'
import {frameDocumentEvent,type DocumentEvent} from './documentCodec'
import {frameProgressEvent,type ProgressEvent} from './progressCodec'
import {frameProjectMetadata,type ProjectMetadataEvent} from './projectMetadataCodec'
const local=['/Users/C18_SECRET_PATH/book-private.docx','C:\\C18_SECRET_PATH\\book-private.docx','\\\\server\\C18_SECRET_PATH\\private.docx','file:///home/C18_SECRET_PATH/private.docx','/Volumes/C18_SECRET_PATH/private.scriv','SOURCE-ID-C18-LOCAL-ONLY']
it('rejects every local binding field in portable document, metadata and progress records',async()=>{
 for(const sentinel of local){
  for(const key of ['docx_path','external_path','source_id','document_bindings','project_bindings','synch','last_synch','expected_external_hash']){
   const d=structuredClone(documents.examples[0]!.event) as DocumentEvent
   Object.assign(d.document!,{[key]:sentinel});await expect(frameDocumentEvent(d)).rejects.toThrow()
   const m=structuredClone(metadata[0]!.event) as ProjectMetadataEvent
   Object.assign(m.metadata!,{[key]:sentinel});expect(()=>frameProjectMetadata(m)).toThrow()
   const p=structuredClone(progress.examples[0]!.event) as ProgressEvent
   Object.assign(p,{[key]:sentinel});await expect(frameProgressEvent(p)).rejects.toThrow()
  }
 }
})
it('keeps every canonical historical Document mutation and Metadata/Progress vector free of raw binding state',async()=>{
 for(const item of documents.examples){const bytes=await frameDocumentEvent(item.event as DocumentEvent);for(const s of local)expect(new TextDecoder().decode(bytes)).not.toContain(s)}
 for(const item of progress.examples){const bytes=await frameProgressEvent(item.event as ProgressEvent);for(const s of local)expect(new TextDecoder().decode(bytes)).not.toContain(s)}
 for(const item of metadata){const bytes=frameProjectMetadata(item.event as ProjectMetadataEvent);for(const s of local)expect(new TextDecoder().decode(bytes)).not.toContain(s)}
})
