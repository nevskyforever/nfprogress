// @vitest-environment node
import {describe,it,expect} from 'vitest'
import {generateAccountMasterKey} from '@/crypto'
import {encryptProjectCover} from './projectCoverCrypto'
import {authenticateCoverReference,createCoverReference,canonicalCoverEnvelope,validateCoverReference,validatePreparedJpeg,sha256} from './projectCoverReference'
import vectors from './__fixtures__/projectMetadataV2.json'
import {frameProjectMetadata,unframeProjectMetadata,encodeProjectMetadataEvent,type ProjectMetadataEvent} from './projectMetadataCodec'
const jpeg=Uint8Array.from(Buffer.from('/9j/4AAQSkZJRgABAQAAGQAZAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAAAZAAAAAQAAABkAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAAASgAwAEAAAAAQAAAAQAAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAAQABAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQICAgQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAH/2gAMAwEAAhEDEQA/AP3UooorjND/2Q==','base64'))
const identity={userId:'123e4567-e89b-42d3-a456-426614174099',projectId:'project',blobId:'123e4567-e89b-42d3-a456-426614174004'}
describe('Metadata v2 exact vectors and cover proof',()=>{
 it('rejects malformed or truncated prepared JPEG while preserving exact valid bytes',()=>{
  expect(()=>validatePreparedJpeg(jpeg)).not.toThrow()
  for(const source of [new Uint8Array([255,216,255,217]),jpeg.subarray(0,jpeg.length-1),new Uint8Array([255,216,255,192,0,255,255,217])])expect(()=>validatePreparedJpeg(source)).toThrow()
 })
 it('preserves historical v1 and matches native uncompressed exact bytes for all v2 forms',()=>{
  for(const v of vectors){const e=v.event as ProjectMetadataEvent
   expect(new TextDecoder().decode(encodeProjectMetadataEvent(e))).toBe(v.canonical)
   expect(Buffer.from(frameProjectMetadata(e)).toString('hex')).toBe(v.frame_hex)
   expect(unframeProjectMetadata(frameProjectMetadata(e))).toEqual(e)
   expect(()=>frameProjectMetadata({...e,metadata:{...e.metadata!,unknown:true}} as ProjectMetadataEvent)).toThrow()
   if(e.version===2)expect(()=>frameProjectMetadata({...e,version:1})).toThrow()
  }
 })
 it('authenticates exact encrypted envelope and every descriptor/context negative',async()=>{
  const amk=await generateAccountMasterKey(),encrypted=await encryptProjectCover(amk,identity,jpeg),ref=await createCoverReference(amk,identity,jpeg,encrypted)
  expect(await authenticateCoverReference(amk,identity,ref,encrypted)).toEqual(jpeg)
  for(const key of ['crypto_version','aad_version','mime_type','plaintext_size','key_fingerprint','envelope_sha256','blob_id'] as const){
   const wrong={...ref,[key]:key==='plaintext_size'?jpeg.length+1:key.includes('version')?2:key==='mime_type'?'image/png':key==='blob_id'?'123e4567-e89b-42d3-a456-426614174009':'0'.repeat(64)}
   await expect(authenticateCoverReference(amk,identity,wrong as typeof ref,encrypted)).rejects.toThrow()
  }
  await expect(authenticateCoverReference(await generateAccountMasterKey(),identity,ref,encrypted)).rejects.toThrow()
  for(const changed of [{...identity,projectId:'P2'},{...identity,userId:'123e4567-e89b-42d3-a456-426614174088'}])await expect(authenticateCoverReference(amk,changed,ref,encrypted)).rejects.toThrow()
  for(const key of ['nonce','ciphertext'] as const){const e={...encrypted,[key]:new Uint8Array(encrypted[key])};e[key][0]!^=1;await expect(authenticateCoverReference(amk,identity,ref,e)).rejects.toThrow();await expect(authenticateCoverReference(amk,identity,{...ref,envelope_sha256:await sha256(canonicalCoverEnvelope(e))},e)).rejects.toThrow()}
  await expect(authenticateCoverReference(amk,identity,ref,{...encrypted,ciphertext:encrypted.ciphertext.subarray(0,19)})).rejects.toThrow()
  expect(()=>canonicalCoverEnvelope({...encrypted,ciphertext:new Uint8Array(2*1024*1024+17)})).toThrow()
  expect(()=>validateCoverReference({...ref,extra:'private'})).toThrow()
  expect(()=>validateCoverReference({...ref,plaintext_size:2*1024*1024+1})).toThrow()
  expect(()=>validateCoverReference({...ref,mime_type:'x'.repeat(256)})).toThrow()
 })
})
