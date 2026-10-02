// @vitest-environment node
import {describe,it,expect,vi,beforeEach} from 'vitest'
import {invoke} from '@tauri-apps/api/core'
import {ContentNoteRuntime,NOTE_READER_SUPPORT} from './contentNoteRuntime'
import {NormalUserAuthRuntime} from '@/auth/userAuth'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {syncApi} from '@/api/sync'
import {frameContentNote,type ContentNoteEvent} from './contentNoteCodec'
import fixture from './__fixtures__/contentNoteCodecV1.json'
import {asAccountMasterKey} from '@/crypto'
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}))
const USER=fixture.examples[0]!.event.account_id,DEVICE=fixture.examples[0]!.event.device_id
async function setup(){
 const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-02T00:00:00Z'})})
 await auth.login('u','p');const context=auth.requireContext()
 const bindings={ensureForCurrentUser:vi.fn(async()=>({context}))},identity={read:vi.fn(async()=>({local_account_id:'a',device_id:DEVICE}))}
 const amk=asAccountMasterKey(new Uint8Array(32))
 const lease={canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(f:(k:typeof amk)=>Promise<unknown>)=>f(amk)}
 const runtime=new ContentNoteRuntime(auth,bindings as never,identity as never,{leaseForAccount:()=>lease} as never)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:DEVICE,last_ack_cursor:0})
 vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2} as never)
 vi.spyOn(encryptedSyncV3Api,'noteReaderCapabilities').mockResolvedValue(undefined)
 const gate=vi.spyOn(encryptedSyncV3Api,'noteReaderGate').mockResolvedValue({ready:true,missing_devices:0})
 return {runtime,auth,identity,gate}
}
beforeEach(()=>{vi.restoreAllMocks();vi.mocked(invoke).mockReset()})
describe('explicit production codec8 writer',()=>{
 it('declares only its persisted device and never captures automatically',async()=>{
  const {runtime}=await setup();await runtime.declareSupport('a',DEVICE)
  expect(encryptedSyncV3Api.noteReaderCapabilities).toHaveBeenCalledWith('token',DEVICE,NOTE_READER_SUPPORT)
  expect(invoke).not.toHaveBeenCalled()
  await expect(runtime.declareSupport('a',USER)).rejects.toThrow()
  expect(encryptedSyncV3Api.noteReaderCapabilities).toHaveBeenCalledTimes(1)
 })
 it('missing participating capability blocks explicit capture; readiness alone does not capture',async()=>{
  const {runtime,gate}=await setup();gate.mockResolvedValue({ready:false,missing_devices:1})
  await expect(runtime.beginNotes('a',DEVICE,'P')).rejects.toThrow('content_note_readers_not_ready')
  expect(invoke).not.toHaveBeenCalled();gate.mockResolvedValue({ready:true,missing_devices:0})
  expect(invoke).not.toHaveBeenCalled();vi.mocked(invoke).mockResolvedValue({state:'candidate_captured',activated:false,candidates:[]})
  await runtime.beginNotes('a',DEVICE,'P')
  expect(invoke).toHaveBeenCalledWith('begin_content_note_migration',expect.objectContaining({scope:{account_id:'a',canonical_user_id:USER,device_id:DEVICE},projectId:'P'}))
 })
 it('seals real C11 frame bytes and leaves activation to verified self echo',async()=>{
  const {runtime}=await setup();const event=structuredClone(fixture.examples[0]!.event) as ContentNoteEvent
  const frame=[...frameContentNote(event)]
  vi.mocked(invoke).mockImplementation(async(command)=>command==='list_pending_content_notes'?[{event_id:event.event.header.event_id,frame,nonce:null,ciphertext:null}]:undefined)
  expect(await runtime.sealNotes('a',DEVICE)).toBe(1)
  const seal=vi.mocked(invoke).mock.calls.find(c=>c[0]==='seal_content_note')![1] as {frame:number[];envelope:{crypto_version:number;aad_version:number;nonce:string;ciphertext:string}}
  expect(seal.frame).toEqual(frame);expect(seal.envelope.crypto_version).toBe(1);expect(seal.envelope.aad_version).toBe(1)
  expect(vi.mocked(invoke).mock.calls.every(c=>c[0]!=='receipt_content_note')).toBe(true)
 })
 it('lost upload response retries the same descriptor and encrypted pair',async()=>{
  const {runtime}=await setup();const event=structuredClone(fixture.examples[0]!.event) as ContentNoteEvent
  vi.mocked(invoke).mockImplementation(async(command)=>command==='list_pending_content_notes'?[{event_id:event.event.header.event_id,frame:[...frameContentNote(event)],nonce:Array(24).fill(1),ciphertext:Array(32).fill(2)}]:undefined)
  const push=vi.spyOn(encryptedSyncV3Api,'pushMetadata').mockRejectedValueOnce(new Error('lost_response')).mockResolvedValueOnce({protocol_version:3,encrypted_sync_version:3,results:[{event_id:event.event.header.event_id,server_sequence:5,duplicate:true}],current_cursor:5})
  await expect(runtime.uploadNotes('a',DEVICE)).rejects.toThrow('lost_response')
  expect(vi.mocked(invoke).mock.calls.every(c=>c[0]!=='receipt_content_note')).toBe(true)
  expect(await runtime.uploadNotes('a',DEVICE)).toBe(1)
  expect(push.mock.calls[0]).toEqual(push.mock.calls[1]);expect(push.mock.calls[0]![2][0]!.event.operation).toBe('event')
  expect(invoke).toHaveBeenCalledWith('receipt_content_note',expect.objectContaining({duplicate:true,serverSequence:5}))
 })
})
