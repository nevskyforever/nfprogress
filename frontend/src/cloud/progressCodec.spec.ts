// @vitest-environment node
import {expect,it} from 'vitest'
import fixtures from './__fixtures__/progressCodecV1.json'
import {frameProgressEvent,unframeProgressEvent,progressMicros,type ProgressEvent} from './progressCodec'
import {frameDocumentEvent,type DocumentEvent} from './documentCodec'
import documents from './__fixtures__/documentCodecV1.json'
import {asAccountMasterKey,encryptObjectBytes,decryptObjectBytes} from '@/crypto'
it('matches native canonical frames for Project/Stage/base/rebase/tombstone',async()=>{
  for(const vector of fixtures.examples){const e=vector.event as ProgressEvent;const f=await frameProgressEvent(e);expect(Buffer.from(f).toString('hex')).toBe(vector.frame_hex);expect(await unframeProgressEvent(f)).toEqual(e);for(const n of [8,9,10,11,12,16]){const bad=f.slice();bad[n]=bad[n]!^1;await expect(unframeProgressEvent(bad)).rejects.toThrow()}}
})
it('rejects malformed immutable amounts, dates, fields and operation shape',async()=>{
  for(const amount of ['NaN','1','01.000000','-0.000000','1.0000001','1000000000001.000000'])expect(()=>progressMicros(amount)).toThrow()
  for(const mutate of [(e:ProgressEvent)=>{e.entries[0]!.writing_day='2026-02-30'},(e:ProgressEvent)=>{e.entries[0]!.new_total='-1.000000'},(e:ProgressEvent)=>{e.header.entity_id='another-scope'},(e:ProgressEvent)=>{Object.assign(e.entries[0]!,{source_path:'/private/file'})},(e:ProgressEvent)=>{e.header.parents=['123e4567-e89b-42d3-a456-426614174010']}]){const e=structuredClone(fixtures.examples[0]!.event)as ProgressEvent;mutate(e);await expect(frameProgressEvent(e)).rejects.toThrow()}
})
it('separates Document and Progress readers and C11 identities',async()=>{
  await expect(unframeProgressEvent(await frameDocumentEvent(documents.examples[0]!.event as DocumentEvent))).rejects.toThrow('progress_codec_unsupported')
  const e=fixtures.examples[0]!.event as ProgressEvent,key=asAccountMasterKey(new Uint8Array(32).fill(42)),scope={userId:e.header.account_id,projectId:e.header.project_id,entityType:'progress',entityId:e.header.entity_id};const f=await frameProgressEvent(e),cipher=await encryptObjectBytes(key,scope,f);expect(await decryptObjectBytes(key,scope,cipher)).toEqual(f)
  for(const wrong of [{...scope,entityType:'document'},{...scope,entityId:'stage:foreign'},{...scope,projectId:'foreign'},{...scope,userId:'123e4567-e89b-42d3-a456-426614174099'}])await expect(decryptObjectBytes(key,wrong,cipher)).rejects.toThrow()
})
