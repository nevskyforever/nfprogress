// @vitest-environment node
import {describe,it,expect} from 'vitest'
import {createHash} from 'node:crypto'
import {deflateSync} from 'node:zlib'
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import vectors from './__fixtures__/frameCompressionV1.json'
import {decompressBounded,compressForFrame,normalizeAuthenticatedFrame,COMPRESSION_LIMITS,COMPRESSION_POLICY} from './frameCompression'
import {unframeProjectMetadata} from './projectMetadataCodec'
import {unframeDocumentEvent} from './documentCodec'
import {asAccountMasterKey,encryptObjectBytes,decryptObjectBytes} from '@/crypto'
const bytes=(hex:string)=>Uint8Array.from(Buffer.from(hex,'hex'))
const input=(v:typeof vectors.vectors[number])=>new TextEncoder().encode(v.prefix+v.unit.repeat(v.repeat)+v.suffix)
const joinBytes=(...parts:Uint8Array[])=>Uint8Array.from(Buffer.concat(parts))
const limit=COMPRESSION_LIMITS.bytes
function compressedFrame(data:Uint8Array,codec=10,declared=data.length){const payload=deflateSync(data),frame=new Uint8Array(payload.length+20);frame.set(new TextEncoder().encode('WORTA-C1'));frame.set([1,codec,1,1],8);const v=new DataView(frame.buffer);v.setUint32(12,declared);v.setUint32(16,payload.length);frame.set(payload,20);return frame}
describe('C18.7 bounded authenticated frame compression',()=>{
 for(const v of vectors.vectors)it('shared fixed TS and Rust streams: '+v.name,async()=>{
  const original=input(v);expect(original.length).toBe(v.declared);expect(createHash('sha256').update(original).digest('hex')).toBe(v.sha256)
  for(const hex of [v.ts_hex,v.rust_hex])expect(Buffer.compare(Buffer.from(decompressBounded(1,bytes(hex),original.length,limit)),Buffer.from(original))).toBe(0)
  expect(compressForFrame(original,v.codec).algorithm).toBe(v.policy)
  expect(Buffer.compare(Buffer.from(decompressBounded(1,bytes(v.ts_hex),original.length,limit)),Buffer.from(decompressBounded(1,bytes(v.rust_hex),original.length,limit)))).toBe(0)
  for (const frameHex of [v.frame_hex,v.rust_frame_hex]) {
  const frame=bytes(frameHex);expect(new DataView(frame.buffer).getUint32(16)).toBe(frame.length-20)
  const normalized=normalizeAuthenticatedFrame(frame,[v.codec],[v.version],limit);expect(normalized[11]).toBe(0)
  if(v.codec===1)expect(unframeProjectMetadata(frame).metadata?.name).toBe(unframeProjectMetadata(normalized).metadata?.name)
  else expect(await unframeDocumentEvent(frame)).toEqual(await unframeDocumentEvent(normalized))
  }
 })
 it('bounds input/output/ratio before allocation and rejects empty compressed output',()=>{
  expect(()=>decompressBounded(2,new Uint8Array(),0,limit)).toThrow('compression_unsupported')
  expect(()=>decompressBounded(1,new Uint8Array(COMPRESSION_LIMITS.inputBytes+1),1,limit)).toThrow('compression_input_limit')
  expect(()=>decompressBounded(1,new Uint8Array(6),limit+1,limit)).toThrow('compression_output_limit')
  expect(()=>decompressBounded(1,new Uint8Array(6),100000,limit)).toThrow('compression_resource_limit')
  const bomb=deflateSync(new Uint8Array(100000));expect(()=>decompressBounded(1,bomb,100000,limit)).toThrow('compression_resource_limit')
  expect(()=>decompressBounded(1,bomb,100,limit)).toThrow('compression_length_mismatch')
  expect(()=>decompressBounded(1,deflateSync(new Uint8Array()),0,limit)).toThrow('compression_resource_limit')
 })
 it('requires exact length and complete single stream with checksum',()=>{
  const original=new TextEncoder().encode('Живая рукопись '.repeat(100)),compressed=deflateSync(original)
  for(const n of [original.length-1,original.length+1])expect(()=>decompressBounded(1,compressed,n,limit)).toThrow('compression_length_mismatch')
  for(let i=0;i<compressed.length;i++)expect(()=>decompressBounded(1,compressed.subarray(0,i),original.length,limit)).toThrow()
  for(const bad of [joinBytes(compressed,Uint8Array.of(0)),joinBytes(compressed,compressed),Uint8Array.of(0,0,0,0,0,0),Uint8Array.of(0x88,0x1c,0,0,0,0)])expect(()=>decompressBounded(1,bad,original.length,limit)).toThrow('compression_invalid_stream')
  const corrupt=Uint8Array.from(compressed);corrupt[corrupt.length-1]=corrupt[corrupt.length-1]!^1;expect(()=>decompressBounded(1,corrupt,original.length,limit)).toThrow('compression_invalid_stream')
  const dict=deflateSync(original,{dictionary:Buffer.from('secret dictionary')});expect(()=>decompressBounded(1,dict,original.length,limit)).toThrow('compression_invalid_stream')
 })
 it('revalidates entity canonical structure and nesting after decompression',async()=>{
  await expect(unframeDocumentEvent(compressedFrame(new TextEncoder().encode('{"version":1,"unknown":true}')))).rejects.toThrow('document_unsupported_structure')
  const deep='['.repeat(170)+'0'+']'.repeat(170);await expect(unframeDocumentEvent(compressedFrame(new TextEncoder().encode(deep)))).rejects.toThrow('document_resource_limit')
  const valid=bytes(vectors.vectors[0]!.frame_hex);valid[11]=2;expect(()=>unframeProjectMetadata(valid)).toThrow('compression_unsupported')
 })
 it('freezes deterministic policy and keeps unsupported assets/tiny/oversized expansion at ID0',()=>{
  expect(COMPRESSION_POLICY).toEqual({minimumBytes:1024,minimumSaving:128,minimumPercent:10,level:6})
  const data=new Uint8Array(100000).fill(65);expect(compressForFrame(data,10).algorithm).toBe(0)
  expect(compressForFrame(data,14).algorithm).toBe(0)
  expect(compressForFrame(new Uint8Array(1023),10).algorithm).toBe(0)
  expect(()=>decompressBounded(0,new Uint8Array(1),2,limit)).toThrow('compression_length_mismatch')
 })
 it('preserves sealed frame/ciphertext on restart and exact lost-response retry without recompression',async()=>{
  const v=vectors.vectors[1]!,frame=bytes(v.frame_hex),amk=asAccountMasterKey(new Uint8Array(32).fill(7)),context={userId:'123e4567-e89b-42d3-a456-426614174000',projectId:'P1',entityId:'document-stable-id',entityType:'document'}
  const sealed=await encryptObjectBytes(amk,context,frame),dir=mkdtempSync(join(tmpdir(),'c187-sealed-'))
  try{writeFileSync(join(dir,'sealed.json'),JSON.stringify({frame:[...frame],nonce:[...sealed.nonce],ciphertext:[...sealed.ciphertext]}));const recovered=JSON.parse(readFileSync(join(dir,'sealed.json'),'utf8'));const retry={...sealed,nonce:Uint8Array.from(recovered.nonce),ciphertext:Uint8Array.from(recovered.ciphertext)};expect(retry.ciphertext).toEqual(sealed.ciphertext);expect(await decryptObjectBytes(amk,context,retry)).toEqual(frame);expect(normalizeAuthenticatedFrame(frame,[10],[1],limit).subarray(20)).toEqual(input(v));expect(recovered.frame).toEqual([...frame])}finally{rmSync(dir,{recursive:true})}
 })
})
