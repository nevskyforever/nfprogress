// @vitest-environment node
import {describe,it,expect,vi,beforeEach} from 'vitest'
import {invoke} from '@tauri-apps/api/core'
import {MapSyncRuntime,MAP_READER_SUPPORT} from './mapSyncRuntime'
import {NormalUserAuthRuntime} from '@/auth/userAuth'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {syncApi} from '@/api/sync'
import {frameMapEvent,type MapEvent} from './mapCodec'
import fixture from './__fixtures__/mapCodecV1.json'
import {asAccountMasterKey} from '@/crypto'
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}))
const USER=fixture.examples[0]!.event.header.account_id,DEVICE=fixture.examples[0]!.event.header.device_id
async function setup(){
 const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-02T00:00:00Z'})})
 await auth.login('u','p');const context=auth.requireContext()
 const bindings={ensureForCurrentUser:vi.fn(async()=>({context}))},identity={read:vi.fn(async()=>({local_account_id:'a',device_id:DEVICE}))}
 const amk=asAccountMasterKey(new Uint8Array(32))
 const lease={canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(f:(k:typeof amk)=>Promise<unknown>)=>f(amk)}
 const runtime=new MapSyncRuntime(auth,bindings as never,identity as never,{leaseForAccount:()=>lease} as never)
 vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:DEVICE,last_ack_cursor:0})
 vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2} as never)
 vi.spyOn(encryptedSyncV3Api,'noteReaderCapabilities').mockResolvedValue(undefined)
 vi.spyOn(encryptedSyncV3Api,'mapReaderCapabilities').mockResolvedValue(undefined)
 const gate=vi.spyOn(encryptedSyncV3Api,'mapReaderGate').mockResolvedValue({ready:true,missing_devices:0})
 return {runtime,auth,identity,gate}
}
beforeEach(()=>{vi.restoreAllMocks();vi.mocked(invoke).mockReset()})
describe('map authority production orchestration',()=>{
 it('capability readiness is never publication consent',async()=>{
  const {runtime,gate}=await setup();await runtime.declareSupport('a',DEVICE)
  expect(encryptedSyncV3Api.mapReaderCapabilities).toHaveBeenCalledWith('token',DEVICE,MAP_READER_SUPPORT)
  expect(invoke).not.toHaveBeenCalled();gate.mockResolvedValue({ready:false,missing_devices:1})
  await expect(runtime.beginMaps('a',DEVICE,'P')).rejects.toThrow('map_readers_not_ready');expect(invoke).not.toHaveBeenCalled()
  gate.mockResolvedValue({ready:true,missing_devices:0});vi.mocked(invoke).mockResolvedValue({owners:[]})
  await runtime.beginMaps('a',DEVICE,'P');expect(invoke).toHaveBeenCalledWith('map_sync_command',expect.objectContaining({request:expect.objectContaining({action:'begin',project_id:'P'})}))
 })
 it('seals unchanged codec9 frame with C11 and retries exact frozen ciphertext after lost response',async()=>{
  const {runtime}=await setup();const event=structuredClone(fixture.examples[0]!.event) as MapEvent,frame=[...await frameMapEvent(event)]
  let sealed:{nonce:number[];ciphertext:number[]}|undefined
  vi.mocked(invoke).mockImplementation(async(_command,args)=>{const r=(args as {request:{action:string;sealed?:boolean;nonce:number[];ciphertext:number[]}}).request;if(r.action==='pending')return [{event,frame,nonce:sealed?.nonce??null,ciphertext:sealed?.ciphertext??null}];if(r.action==='seal')sealed={nonce:r.nonce,ciphertext:r.ciphertext}})
  expect(await runtime.sealMaps('a',DEVICE)).toBe(1);expect(sealed?.nonce).toHaveLength(24)
  expect(vi.mocked(invoke).mock.calls.some(c=>(c[1] as {request:{action:string}}).request.action==='receipt')).toBe(false)
  const push=vi.spyOn(encryptedSyncV3Api,'pushMaps').mockRejectedValueOnce(new Error('lost_response')).mockResolvedValueOnce({protocol_version:3,encrypted_sync_version:3,results:[{event_id:event.header.event_id,server_sequence:5,duplicate:true}],current_cursor:5})
  await expect(runtime.uploadMaps('a',DEVICE)).rejects.toThrow('lost_response');expect(await runtime.uploadMaps('a',DEVICE)).toBe(1)
  expect(push.mock.calls[0]).toEqual(push.mock.calls[1]);expect(push.mock.calls[0]![2][0]!.object.crypto_version).toBe(1)
 })
 it('blocked first page does not starve later map owners',async()=>{
  const {runtime}=await setup();const after:number[]=[]
  vi.mocked(invoke).mockImplementation(async(_command,args)=>{const r=(args as {request:{action:string;after:number}}).request;if(r.action==='received'){after.push(r.after);return r.after===0?[{event_id:'bad',server_sequence:9,project_id:'P',entity_id:'project-map',nonce:Array(24).fill(0),ciphertext:Array(32).fill(0)}]:[]}})
  const result=await runtime.readOnce('a',DEVICE,1,2);expect(result.blocked).toEqual(['decrypt_failed']);expect(after).toEqual([0,9])
 })
})
