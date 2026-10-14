import metadata from '@/cloud/__fixtures__/projectMetadataV2.json'
import stage from '@/cloud/__fixtures__/stageCodecV1.json'
import catalog from '@/cloud/__fixtures__/accountCatalogV1.json'
import note from '@/cloud/__fixtures__/contentNoteCodecV1.json'
import map from '@/cloud/__fixtures__/mapCodecV1.json'
import document from '@/cloud/__fixtures__/documentCodecV1.json'
import progress from '@/cloud/__fixtures__/progressCodecV1.json'
import game from '@/cloud/__fixtures__/gameCodecV1.json'
import { canonical } from '@/cloud/projectMetadataCodec'
import { deflate } from 'pako'
import { encryptObjectBytes, asAccountMasterKey } from '@/crypto'
import { encryptAccountObject } from '@/crypto/accountObjectCrypto'
import { openBrowserCanonicalObject, type BrowserCanonicalContext } from './canonicalReaders'
export const readerCases = () => {
  const folder: any = structuredClone(catalog), structural: any = structuredClone(stage.event)
  const order = { ...structural, header: { ...structural.header, entity_type: 'stage_order', entity_id: 'stage_order' }, stage: null, stage_ids: ['S1'], stage_heads: { S1: [structural.header.metadata_event_id] } }
  const membership = { ...folder, header: { ...folder.header, entity_type: 'folder_membership', entity_id: 'C1' }, payload: { folder_id: 'F1' }, dependencies: { folders: { F1: [folder.header.event_id] }, projects: { C1: { bootstrap_id: folder.header.event_id, metadata_event_id: folder.header.device_id } }, memberships: {} } }
  const cases: Array<{id:number;version:number;event:any}> = [
    {id:1,version:2,event:structuredClone(metadata.find(e=>e.event.version===2)!.event)}, {id:2,version:1,event:structural}, {id:3,version:1,event:order}, {id:4,version:1,event:folder},
    {id:5,version:1,event:{...folder,header:{...folder.header,entity_type:'folder_order',entity_id:'folder_order'},payload:{ids:['F1']},dependencies:{folders:{F1:[folder.header.event_id]},projects:{},memberships:{}}}},
    {id:6,version:1,event:membership}, {id:7,version:1,event:{...folder,header:{...folder.header,entity_type:'project_order',entity_id:'project_order'},payload:{ids:['C1']},dependencies:{folders:{},projects:membership.dependencies.projects,memberships:{C1:[folder.header.event_id]}}}},
    {id:8,version:1,event:structuredClone(note.examples[0]!.event)}, {id:9,version:1,event:structuredClone(map.examples.find(e=>e.event.mutation==='upsert')!.event)},
    {id:10,version:1,event:structuredClone(document.examples[0]!.event)}, {id:11,version:1,event:structuredClone(progress.examples[0]!.event)},
    {id:12,version:1,event:structuredClone(game.examples.find(e=>e.event.header.scope==='project')!.event)}, {id:13,version:1,event:structuredClone(game.examples.find(e=>e.event.header.scope==='account')!.event)},
  ]
  const m = structuredClone(cases[0]!.event); m.version=1; delete m.metadata.cover_reference; cases.push({id:1,version:1,event:m})
  for (const id of [2,3]) { const s=structuredClone(cases.find(c=>c.id===id)!.event);s.version=2;s.header.operation='update';s.header.revision=2;s.header.generation=2;s.header.parent_event_ids=[s.header.metadata_event_id];cases.push({id,version:2,event:s}) }
  return cases
}
export function readerFrame(c:{id:number;version:number;event:unknown}, compressed=false) {
  const bytes=new TextEncoder().encode(canonical(c.event)),payload=compressed?deflate(bytes):bytes,f=new Uint8Array(20+payload.length)
  f.set(new TextEncoder().encode('WORTA-C1'));f.set([1,c.id,c.version,compressed?1:0],8);const v=new DataView(f.buffer);v.setUint32(12,bytes.length);v.setUint32(16,payload.length);f.set(payload,20);return f
}
export function readerContext(c:{id:number;event:any}):BrowserCanonicalContext {
  const h=c.id===8?c.event.event.header:c.event.header
  return { accountId:c.id===8?c.event.account_id:h.account_id,projectId:[4,5,6,7,13].includes(c.id)?null:h.project_id,entityId:h.entity_id,eventId:h.event_id,entityType:['','project_metadata','stage','stage_order','folder','folder_order','folder_membership','project_order','note','map','document','progress','project_game','account_game'][c.id]! }
}
export async function encryptedReaderFrame(context:BrowserCanonicalContext,frame:Uint8Array) {
  const key=asAccountMasterKey(new Uint8Array(32).fill(29))
  try { return context.projectId===null ? await encryptAccountObject(key,{userId:context.accountId,scope:'account',entityId:context.entityId,entityType:context.entityType},frame) : await encryptObjectBytes(key,{userId:context.accountId,projectId:context.projectId,entityId:context.entityId,entityType:context.entityType},frame) } finally { key.fill(0) }
}
export async function readFixture(c:{id:number;version:number;event:any},frame:Uint8Array) {const key=asAccountMasterKey(new Uint8Array(32).fill(29)),context=readerContext(c),sealed=await encryptedReaderFrame(context,frame);try{return await openBrowserCanonicalObject(key,context,sealed)}finally{key.fill(0);sealed.nonce.fill(0);sealed.ciphertext.fill(0)}}
