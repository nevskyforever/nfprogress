// @vitest-environment node
import {describe,it,expect,vi,afterEach} from 'vitest'
import {NormalUserAuthRuntime} from '@/auth/userAuth'
import {generateAccountMasterKey} from '@/crypto'
import {ApiError} from '@/api/client'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedCoversApi} from '@/api/encryptedCovers'
import {ProjectMetadataMigrationRuntime} from './projectMetadataMigrationRuntime'
import {encryptProjectCover} from './projectCoverCrypto'
import {createCoverReference} from './projectCoverReference'
import {sealProjectMetadataEvent} from './projectMetadataCodec'
import vectors from './__fixtures__/projectMetadataV2.json'
const USER='123e4567-e89b-42d3-a456-426614174099',DEVICE='123e4567-e89b-42d3-a456-426614174003'
afterEach(()=>vi.restoreAllMocks())
async function harness(){
 const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-06T00:00:00.000000Z'})})
 await auth.login('u','p');vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({writer_transport_version:3,supported_transport_version:2,cutover_epoch:2});const context=auth.requireContext(),amk=await generateAccountMasterKey()
 const calls:string[]=[],pending:{value:Record<string,unknown>|null}={value:null}
 const covers={command:vi.fn(async(_scope:unknown,_project:string,action:string,data:Record<string,unknown>)=>{
  calls.push(action)
  if(action==='projects')return pending.value?['project']:[]
  if(action==='pending')return pending.value
  if(action==='seal'){pending.value={...pending.value,...data,state:data.reference?'sealed':'uploaded'};return true}
  if(action==='uploaded'){pending.value={...pending.value,state:'uploaded'};return true}
  return true
 })}
 const native={unsealed:vi.fn(async()=>[]),received:vi.fn(async()=>[]),apply:vi.fn(async()=>'applied')}
 const api={coverReaderCapabilities:vi.fn(async()=>{}),coverReaderGate:vi.fn(async()=>({ready:true,missing_devices:0}))}
 const bindings={ensureForCurrentUser:vi.fn(async()=>({context}))},identity={read:vi.fn(async()=>({local_account_id:'local',device_id:DEVICE}))}
 const keys={leaseForAccount:vi.fn(()=>({canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(f:(key:typeof amk)=>unknown)=>f(amk)}))}
 const runtime=new ProjectMetadataMigrationRuntime(auth,bindings as never,identity as never,keys as never,native as never,{} as never,{} as never,api as never,200,covers as never)
 return{runtime,amk,api,native,covers,pending,calls}
}
describe('cover production runtime',()=>{
 it('background processing never discovers/captures local sources, and old readers block before upload',async()=>{
  const h=await harness(),upload=vi.spyOn(encryptedCoversApi,'upload')
  await h.runtime.processCoverTransfers('local',DEVICE)
  expect(h.calls).toEqual(['projects']);expect(upload).not.toHaveBeenCalled()
  h.pending.value={intent_id:'intent',state:'captured',source_cover:'data:image/jpeg;base64,/9j/2Q=='}
  h.api.coverReaderGate.mockResolvedValue({ready:false,missing_devices:1})
  await h.runtime.processCoverTransfers('local',DEVICE)
  expect(h.calls).not.toContain('seal');expect(h.calls).not.toContain('capture');expect(upload).not.toHaveBeenCalled()
  expect(h.covers.command).toHaveBeenLastCalledWith(expect.anything(),'project','block_intent',expect.objectContaining({code:'cover_readers_not_ready'}),expect.anything())
 })
 it('retains malformed legacy source and never uploads or replaces it with null',async()=>{
  const h=await harness(),source='data:image/png;base64,broken'
  h.pending.value={intent_id:'intent',state:'captured',source_cover:source}
  const upload=vi.spyOn(encryptedCoversApi,'upload')
  await h.runtime.processCoverTransfers('local',DEVICE)
  expect(h.pending.value.source_cover).toBe(source)
  expect(h.calls).not.toContain('seal');expect(h.calls).not.toContain('prepare');expect(upload).not.toHaveBeenCalled()
  expect(h.covers.command).toHaveBeenCalledWith(expect.anything(),'project','block_intent',expect.objectContaining({code:'cover_source_invalid'}),expect.anything())
 })
 it('lost upload response retries exact encrypted candidate and verifies download before metadata prepare',async()=>{
  const h=await harness(),jpeg=Uint8Array.from(Buffer.from('/9j/4AAQSkZJRgABAQAAGQAZAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAAAZAAAAAQAAABkAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAAASgAwAEAAAAAQAAAAQAAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAAQABAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQICAgQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAH/2gAMAwEAAhEDEQA/AP3UooorjND/2Q==','base64')),identity={userId:USER,projectId:'project',blobId:'123e4567-e89b-42d3-a456-426614174004'}
  const envelope=await encryptProjectCover(h.amk,identity,jpeg),reference=await createCoverReference(h.amk,identity,jpeg,envelope)
  h.pending.value={intent_id:'intent',state:'sealed',reference,blob_id:identity.blobId,nonce:[...envelope.nonce],ciphertext:[...envelope.ciphertext]}
  const upload=vi.spyOn(encryptedCoversApi,'upload').mockRejectedValueOnce(new Error('lost response')).mockResolvedValue({blob_id:identity.blobId,project_id:'project',kind:'project_cover',size_bytes:envelope.ciphertext.length,duplicate:true})
  vi.spyOn(encryptedCoversApi,'download').mockResolvedValue(envelope)
  await expect(h.runtime.processCoverTransfers('local',DEVICE)).rejects.toThrow('lost response')
  expect(h.calls).not.toContain('prepare')
  await h.runtime.processCoverTransfers('local',DEVICE)
  expect(upload.mock.calls[0]).toEqual(upload.mock.calls[1])
  expect(h.calls.slice(-3)).toEqual(['material','uploaded','prepare'])
 })
 it.each([[404,'encrypted_blob_unavailable','cover_blob_missing'],[503,'encrypted_blob_unavailable','cover_blob_missing'],[503,'encrypted_blob_corrupt','cover_blob_invalid']])('retains metadata and typed blocker on %s/%s',async(status,code,blocker)=>{
  const h=await harness(),jpeg=Uint8Array.from(Buffer.from('/9j/4AAQSkZJRgABAQAAGQAZAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAAAZAAAAAQAAABkAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAAASgAwAEAAAAAQAAAAQAAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAAQABAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQICAgQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAH/2gAMAwEAAhEDEQA/AP3UooorjND/2Q==','base64')),identity={userId:USER,projectId:'project',blobId:'123e4567-e89b-42d3-a456-426614174004'}
  const envelope=await encryptProjectCover(h.amk,identity,jpeg),reference=await createCoverReference(h.amk,identity,jpeg,envelope)
  const event=structuredClone(vectors.find(v=>v.name==='v2_cover')!.event)
  event.header.account_id=USER;event.header.project_id='project';event.header.entity_id='project';event.metadata!.cover_reference=reference
  const sealed=await sealProjectMetadataEvent(h.amk,event as never)
  const row={project_id:'project',entity_id:'project',event_id:event.header.event_id,source_device_id:event.header.device_id,revision:event.header.revision,updated_at:event.header.updated_at,deleted_at:null,operation:'upsert',server_sequence:1,crypto_version:1,aad_version:1,nonce:[...sealed.nonce],ciphertext:[...sealed.ciphertext]}
  h.native.received.mockResolvedValue([row] as never)
  vi.spyOn(encryptedCoversApi,'download').mockRejectedValue(new ApiError(status as number,code as string,'unavailable'))
  expect((await h.runtime.applyOnce('local',DEVICE)).blocked).toEqual([event.header.event_id])
  expect(h.native.apply).not.toHaveBeenCalled()
  expect(h.covers.command).toHaveBeenCalledWith(expect.anything(),'project','block',expect.objectContaining({code:blocker,reference}),expect.anything())
 })
})
