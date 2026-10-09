// @vitest-environment node
import {describe,it,expect,vi} from 'vitest'
import {compressCanonicalFrame,selectWriterFrame,normalizeAuthenticatedFrame,COMPRESSION_LIMITS} from './frameCompression'
import vectors from './__fixtures__/frameCompressionV1.json'
import {unframeDocumentEvent,frameDocumentEvent} from './documentCodec'
import {unframeProjectMetadata,frameProjectMetadata} from './projectMetadataCodec'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {apiRequest} from '@/api/client'
const compressionFailure=vi.hoisted(()=>({enabled:false}))
vi.mock('pako',async original=>{const actual=await original<typeof import('pako')>();return {...actual,deflate:(...args:Parameters<typeof actual.deflate>)=>{if(compressionFailure.enabled)throw new Error('library_failure');return actual.deflate(...args)}}})
vi.mock('@/api/client',()=>({apiRequest:vi.fn()}))
const from=(hex:string)=>Uint8Array.from(Buffer.from(hex,'hex'))
describe('C18.7.02 immutable writer admission',()=>{
 it('same canonical bytes deterministically select identical fresh frames; absent/false gate preserves exact ID0',async()=>{
  for(const vector of vectors.vectors.filter(v=>v.declared<1024*1024)){
   const old=normalizeAuthenticatedFrame(from(vector.frame_hex),[vector.codec],[vector.version],COMPRESSION_LIMITS.bytes)
   const first=await selectWriterFrame(old,async()=>true),second=await selectWriterFrame(old,async()=>true)
   expect(first).toEqual(second);expect(first[11]).toBe(vector.policy)
   expect(await selectWriterFrame(old,async()=>false)).toBe(old)
   expect(normalizeAuthenticatedFrame(first,[vector.codec],[vector.version],COMPRESSION_LIMITS.bytes)).toEqual(old)
   if(vector.codec===10)expect(await frameDocumentEvent(await unframeDocumentEvent(first))).toEqual(old)
   else expect(frameProjectMetadata(unframeProjectMetadata(first))).toEqual(old)
  }
 })
 it('mixed metadata/Document ID0-ID1-ID0 cycles leave historical bytes intact',async()=>{
  for(const vector of vectors.vectors.slice(0,2)){
   const old=normalizeAuthenticatedFrame(from(vector.frame_hex),[vector.codec],[vector.version],COMPRESSION_LIMITS.bytes),snapshot=old.slice()
   for(const ready of [false,true,true,false,true,false]){
    const frame=await selectWriterFrame(old,async()=>ready)
    expect(frame[11]).toBe(ready?vector.policy:0)
    expect(normalizeAuthenticatedFrame(frame,[vector.codec],[vector.version],COMPRESSION_LIMITS.bytes)).toEqual(snapshot)
   }
   expect(old).toEqual(snapshot)
  }
 })
 it('small/invalid/denied candidates cannot activate ID1',async()=>{
  const vector=vectors.vectors[4]!,old=normalizeAuthenticatedFrame(from(vector.frame_hex),[1],[1],COMPRESSION_LIMITS.bytes),authorize=vi.fn(async()=>true)
  expect(await selectWriterFrame(old,authorize)).toBe(old);expect(authorize).not.toHaveBeenCalled()
  const wrong=old.slice();wrong[9]=14
  expect(()=>compressCanonicalFrame(wrong)).toThrow('compression_invalid_stream')
 })
 it('library failure before sealing keeps the validated ID0 candidate; malformed persisted frames never fall back',async()=>{
  const v=vectors.vectors[1]!,old=normalizeAuthenticatedFrame(from(v.frame_hex),[10],[1],COMPRESSION_LIMITS.bytes)
  compressionFailure.enabled=true
  try { expect(await selectWriterFrame(old,async()=>true)).toBe(old) }
  finally { compressionFailure.enabled=false }
  const malformed=old.slice();malformed[11]=2
  await expect(selectWriterFrame(malformed,async()=>true)).rejects.toThrow('compression_invalid_stream')
 })
 it('API accepts only explicit coherent aggregate state; capability declaration is explicit true',async()=>{
  for(const bad of [{ready:1,missing_devices:0},{ready:true,missing_devices:1},{ready:true,missing_devices:-1},{ready:true},{ready:true,missing_devices:0,extra:1}]){
   vi.mocked(apiRequest).mockResolvedValueOnce(bad)
   await expect(encryptedSyncV3Api.compressionWriter('t','d')).rejects.toThrow('invalid_encrypted_sync_v3')
  }
  vi.mocked(apiRequest).mockResolvedValueOnce({ready:true,missing_devices:0})
  expect(await encryptedSyncV3Api.compressionWriter('t','d')).toEqual({ready:true,missing_devices:0})
  await encryptedSyncV3Api.compressionReaderCapabilities('t','d')
  expect(apiRequest).toHaveBeenLastCalledWith(expect.any(String),expect.objectContaining({body:{device_id:'d',compression_id1:true}}))
 })
})
