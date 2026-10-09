// @vitest-environment node
import {describe,it,expect} from 'vitest'
import {deflate} from 'pako'
import {readFileSync} from 'node:fs'
import {asAccountMasterKey,encryptObjectBytes,decryptObjectBytes} from '@/crypto'
import {encryptAccountObject,decryptAccountObject} from '@/crypto/accountObjectCrypto'
import {frameProjectMetadata,unframeProjectMetadata} from './projectMetadataCodec'
import {frameStructuralEvent,unframeStructuralEvent} from './stageCodec'
import {frameCatalogEvent,unframeCatalogEvent,CATALOG_CODEC_IDS} from './accountCatalogCodec'
import {frameContentNote,unframeContentNote} from './contentNoteCodec'
import {frameMapEvent,unframeMapEvent,mapEntityId} from './mapCodec'
import {frameDocumentEvent,unframeDocumentEvent} from './documentCodec'
import {frameProgressEvent,unframeProgressEvent} from './progressCodec'
import {frameGameEvent,unframeGameEvent} from './gameCodec'
import stage from './__fixtures__/stageCodecV1.json'
import catalog from './__fixtures__/accountCatalogV1.json'
import notes from './__fixtures__/contentNoteCodecV1.json'
import maps from './__fixtures__/mapCodecV1.json'
import docs from './__fixtures__/documentCodecV1.json'
import progress from './__fixtures__/progressCodecV1.json'
import game from './__fixtures__/gameCodecV1.json'

describe('C18.5 whole codec and crypto registry',()=>{
 it('frames every actual registry slot and rejects every other reader family',async()=>{
  const h=stage.event.header
  const meta={version:1,header:{account_id:h.account_id,project_id:h.project_id,entity_id:h.project_id,
   device_id:h.device_id,bootstrap_id:h.bootstrap_id,event_id:h.metadata_event_id,revision:1,generation:1,
   operation:'create',parent_event_ids:[],updated_at:h.updated_at},metadata:{name:'Project',goal:null,infinite:true,
   unit:'symbols',status:'active',deadline:null,personal_goal:0,auto_freeze:true,streak_enabled:true,
   work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
  const order=structuredClone(stage.event) as any;order.header.entity_type='stage_order';order.header.entity_id='stage_order'
  order.stage=null;order.stage_ids=[];order.stage_heads={}
  const frames=[frameProjectMetadata(meta as never),frameStructuralEvent(stage.event as never),frameStructuralEvent(order)]
  for(const type of Object.keys(CATALOG_CODEC_IDS)){
   const e=structuredClone(catalog) as any;e.header.entity_type=type
   if(type==='folder_order'||type==='project_order'){e.header.entity_id=type;e.payload={ids:[]};e.dependencies={folders:{},projects:{},memberships:{}}}
   if(type==='folder_membership'){e.header.entity_id='P1';e.payload={folder_id:'F1'};e.dependencies={folders:{F1:[h.event_id]},projects:{P1:{bootstrap_id:h.bootstrap_id,metadata_event_id:h.metadata_event_id}},memberships:{}}}
   frames.push(frameCatalogEvent(e))
  }
  frames.push(frameContentNote(notes.examples[0]!.event as never),await frameMapEvent(maps.examples[0]!.event as never),
   await frameDocumentEvent(docs.examples[0]!.event as never),await frameProgressEvent(progress.examples[0]!.event as never),
   frameGameEvent(game.examples.find(e=>e.event.header.scope==='project')!.event as never),
   frameGameEvent(game.examples.find(e=>e.event.header.scope==='account')!.event as never))
  expect(frames.map(f=>f[9])).toEqual([1,2,3,4,5,6,7,8,9,10,11,12,13])
  const readers:Array<[number[],(f:Uint8Array)=>unknown]>=[[[1],unframeProjectMetadata],[[2,3],unframeStructuralEvent],
   [[4,5,6,7],unframeCatalogEvent],[[8],unframeContentNote],[[9],unframeMapEvent],[[10],unframeDocumentEvent],
   [[11],unframeProgressEvent],[[12],f=>unframeGameEvent(f,'project')],[[13],f=>unframeGameEvent(f,'account')]]
  for(const [accepted,read] of readers)for(const f of frames){
   if(accepted.includes(f[9]!)){
    const payload=deflate(f.subarray(20)),compressed=new Uint8Array(payload.length+20);compressed.set(f.subarray(0,20));compressed[11]=1;new DataView(compressed.buffer).setUint32(16,payload.length);compressed.set(payload,20)
    expect(await read(compressed)).toEqual(await read(f))
   }
   else await expect(Promise.resolve().then(()=>read(f))).rejects.toThrow()
  }
 })
 it('keeps every accepted content/action golden frame byte-identical',async()=>{
  const groups:Array<[typeof game.examples|any[],(e:any)=>Uint8Array|Promise<Uint8Array>]>=[
   [notes.examples,frameContentNote],[maps.examples,frameMapEvent],[docs.examples,frameDocumentEvent],
   [progress.examples,frameProgressEvent],[game.examples,frameGameEvent]]
  for(const [vectors,frame] of groups)for(const v of vectors)
   expect(Buffer.from(await frame(v.event)).toString('hex')).toBe(v.frame_hex)
  expect(readFileSync(new URL('./accountCatalogCodec.ts',import.meta.url),'utf8')).not.toContain('ACCOUNT_ENTITY_TYPES.indexOf')
 })
 it('separates adjacent entity domains, users, projects and Stage identities',async()=>{
  const amk=asAccountMasterKey(new Uint8Array(32).fill(7)),user=stage.event.header.account_id
  const types=['note','map','document','progress','project_game']
  const bytes=new TextEncoder().encode('private bounded test content')
  for(let i=0;i<types.length-1;i++){
   const ctx={userId:user,projectId:'P1',entityId:'owner',entityType:types[i]!}
   const sealed=await encryptObjectBytes(amk,ctx,bytes)
   for(const wrong of [{...ctx,entityType:types[i+1]!},{...ctx,projectId:'P2'},{...ctx,userId:'123e4567-e89b-42d3-a456-426614174098'},{...ctx,entityId:'other'}])
    await expect(decryptObjectBytes(amk,wrong,sealed)).rejects.toThrow()
  }
  const s1=await mapEntityId('S1'),s2=await mapEntityId('S2');expect(s1).not.toBe(s2)
  const project={userId:user,projectId:'P1',entityId:'game:owner',entityType:'project_game'}
  const account={userId:user,scope:'account' as const,entityId:'game:owner',entityType:'account_game'}
  const ps=await encryptObjectBytes(amk,project,bytes),as=await encryptAccountObject(amk,account,bytes)
  await expect(decryptAccountObject(amk,account,{...ps,crypto_version:2,aad_version:2})).rejects.toThrow()
  await expect(decryptObjectBytes(amk,project,{...as,crypto_version:1,aad_version:1})).rejects.toThrow()
  await expect(decryptAccountObject(amk,{...account,entityType:'folder'},as)).rejects.toThrow()
  await expect(decryptAccountObject(amk,{...account,userId:'123e4567-e89b-42d3-a456-426614174098'},as)).rejects.toThrow()
  const sm=await encryptObjectBytes(amk,{...project,entityType:'map',entityId:s1},bytes)
  await expect(decryptObjectBytes(amk,{...project,entityType:'map',entityId:s2},sm)).rejects.toThrow()
 })
})
