// @vitest-environment node
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {invoke} from '@tauri-apps/api/core'
import {GameSyncRuntime} from './gameSyncRuntime'
import {frameGameEvent,type GameEvent} from './gameCodec'
import fixture from './__fixtures__/gameCodecV1.json'
import {NormalUserAuthRuntime} from '@/auth/userAuth'
import {encryptedSyncV2Api} from '@/api/encryptedSyncV2'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {syncApi} from '@/api/sync'
import {asAccountMasterKey,decryptObjectBytes,encryptObjectBytes} from '@/crypto'
import {decryptAccountObject,encryptAccountObject} from '@/crypto/accountObjectCrypto'
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}))
const USER=fixture.examples[0]!.event.header.account_id,DEVICE=fixture.examples[0]!.event.header.device_id
const amk=asAccountMasterKey(new Uint8Array(32))
const genesis=(scope:'project'|'account')=>structuredClone(fixture.examples.find(e=>e.event.header.scope===scope&&e.event.action.kind==='genesis')!.event) as GameEvent
async function setup(){
  const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-02T00:00:00Z'})})
  await auth.login('u','p');const context=auth.requireContext()
  const lease={canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(f:(k:typeof amk)=>Promise<unknown>)=>f(amk)}
  const runtime=new GameSyncRuntime(auth,{ensureForCurrentUser:vi.fn(async()=>({context}))} as never,{read:vi.fn(async()=>({local_account_id:'a',device_id:DEVICE}))} as never,{leaseForAccount:()=>lease} as never)
  vi.spyOn(syncApi,'registerDevice').mockResolvedValue({protocol_version:1,device_id:DEVICE,last_ack_cursor:0})
  vi.spyOn(encryptedSyncV2Api,'capabilities').mockResolvedValue({supported_transport_version:2,writer_transport_version:3,cutover_epoch:2} as never)
  for(const method of ['noteReaderCapabilities','mapReaderCapabilities','documentReaderCapabilities','progressReaderCapabilities','gameReaderCapabilities'] as const)vi.spyOn(encryptedSyncV3Api,method).mockResolvedValue(undefined)
  const gate=vi.spyOn(encryptedSyncV3Api,'gameReaderGate').mockResolvedValue({ready:true,missing_devices:0})
  return {runtime,gate}
}
beforeEach(()=>{vi.restoreAllMocks();vi.mocked(invoke).mockReset()})
describe('paired Game production runtime',()=>{
  it('declares both readers without capture and blocks publication for a third device',async()=>{
    const {runtime,gate}=await setup();vi.mocked(invoke).mockResolvedValue({owners:[]})
    await runtime.declareGameSupport('a',DEVICE)
    expect(encryptedSyncV3Api.gameReaderCapabilities).toHaveBeenCalledWith('token',DEVICE)
    expect(vi.mocked(invoke).mock.calls.every(c=>(c[1] as {request:{action:string}}).request.action==='view')).toBe(true)
    gate.mockResolvedValue({ready:false,missing_devices:1})
    await expect(runtime.beginGame('a',DEVICE)).rejects.toThrow('game_readers_not_ready')
    await expect(runtime.sealGame('a',DEVICE)).rejects.toThrow('game_readers_not_ready')
    await expect(runtime.uploadGame('a',DEVICE)).rejects.toThrow('game_readers_not_ready')
    expect(vi.mocked(invoke).mock.calls.some(c=>(c[1] as {request:{action:string}}).request.action==='begin')).toBe(false)
    gate.mockResolvedValue({ready:true,missing_devices:0});await runtime.beginGame('a',DEVICE)
    expect(invoke).toHaveBeenCalledWith('game_sync_command',expect.objectContaining({request:expect.objectContaining({action:'begin'})}))
  })
  it.each(['project','account'] as const)('seals %s with its production crypto domain and retries exact bytes',async scope=>{
    const {runtime}=await setup();const event=genesis(scope),frame=[...frameGameEvent(event)],h=event.header
    let sealed:{nonce:number[];ciphertext:number[]}|undefined
    vi.mocked(invoke).mockImplementation(async(_command,args)=>{const r=(args as {request:{action:string;nonce:number[];ciphertext:number[]}}).request;if(r.action==='pending')return [{event,frame,nonce:sealed?.nonce??null,ciphertext:sealed?.ciphertext??null}];if(r.action==='seal')sealed={nonce:r.nonce,ciphertext:r.ciphertext}})
    expect(await runtime.sealGame('a',DEVICE)).toBe(1)
    const envelope={nonce:Uint8Array.from(sealed!.nonce),ciphertext:Uint8Array.from(sealed!.ciphertext)}
    const decoded=h.scope==='project'
      ?await decryptObjectBytes(amk,{userId:USER,projectId:h.project_id,entityType:'project_game',entityId:h.entity_id},{...envelope,crypto_version:1,aad_version:1})
      :await decryptAccountObject(amk,{userId:USER,scope:'account',entityType:'account_game',entityId:h.entity_id},{...envelope,crypto_version:2,aad_version:2})
    expect([...decoded]).toEqual(frame)
    const push=vi.spyOn(encryptedSyncV3Api,scope==='project'?'pushGame':'pushAccount').mockRejectedValueOnce(new Error('lost_response')).mockResolvedValueOnce({protocol_version:3,encrypted_sync_version:3,results:[{event_id:h.event_id,server_sequence:5,duplicate:true}],current_cursor:5})
    await expect(runtime.uploadGame('a',DEVICE)).rejects.toThrow('lost_response');await runtime.uploadGame('a',DEVICE)
    expect(push.mock.calls[0]).toEqual(push.mock.calls[1])
    expect(push.mock.calls[0]![2][0]!.object.crypto_version).toBe(scope==='project'?1:2)
    expect(invoke).toHaveBeenCalledWith('game_sync_command',expect.objectContaining({request:expect.objectContaining({action:'receipt',server_sequence:5,duplicate:true})}))
  })
  it('decrypts and authenticates both reader domains without routing Game to catalogs',async()=>{
    const {runtime}=await setup();const rows:Array<Record<string,string|number|number[]|null>>=[]
    for(const scope of ['project','account'] as const){const e=genesis(scope),h=e.header,frame=frameGameEvent(e)
      const sealed=h.scope==='project'?await encryptObjectBytes(amk,{userId:USER,projectId:h.project_id,entityType:'project_game',entityId:h.entity_id},frame):await encryptAccountObject(amk,{userId:USER,scope:'account',entityType:'account_game',entityId:h.entity_id},frame)
      rows.push({event_id:h.event_id,source_device_id:h.device_id,entity_id:h.entity_id,project_id:h.scope==='project'?h.project_id:null,revision:h.revision,updated_at:h.updated_at,scope,nonce:[...sealed.nonce],ciphertext:[...sealed.ciphertext],server_sequence:rows.length+1})
    }
    let listed=false
    vi.mocked(invoke).mockImplementation(async(_c,args)=>{const r=(args as {request:{action:string}}).request;if(r.action==='received'){if(listed)return [];listed=true;return rows}if(r.action==='apply')return 'applied'})
    const result=await runtime.readGameOnce('a',DEVICE);expect(result.applied).toBe(2);expect(result.blocked).toEqual([])
    const calls=vi.mocked(invoke).mock.calls.filter(c=>(c[1] as {request:{action:string}}).request.action==='apply')
    expect(calls.map(c=>(c[1] as {request:{project:boolean}}).request.project)).toEqual([true,false])
  })
  it('retains corrupt ciphertext and continues reading eligible later rows',async()=>{
    const {runtime}=await setup();let pass=0
    const row={event_id:genesis('account').header.event_id,scope:'account',entity_id:genesis('account').header.entity_id,nonce:Array(24).fill(0),ciphertext:Array(32).fill(0),server_sequence:1}
    vi.mocked(invoke).mockImplementation(async(_c,args)=>{const r=(args as {request:{action:string}}).request;if(r.action==='received')return pass++===0?[row]:[]})
    const result=await runtime.readGameOnce('a',DEVICE,1,2);expect(result.blocked).toEqual(['decrypt_failed']);expect(pass).toBe(2)
    expect(invoke).toHaveBeenCalledWith('game_sync_command',expect.objectContaining({request:{action:'block',event_id:row.event_id,nonce:row.nonce,ciphertext:row.ciphertext,code:'decrypt_failed'}}))
    expect(vi.mocked(invoke).mock.calls.some(c=>(c[1] as {request:{action:string}}).request.action==='apply')).toBe(false)
  })
  it('does not advertise a reader when Game is still owned by the legacy store',async()=>{
    const {runtime}=await setup();vi.mocked(invoke).mockRejectedValue('game_codec_not_activated')
    expect(await runtime.gameReaderAvailable('a',DEVICE)).toBe(false)
    await expect(runtime.declareGameSupport('a',DEVICE)).rejects.toBe('game_codec_not_activated')
    expect(encryptedSyncV3Api.gameReaderCapabilities).not.toHaveBeenCalled()
  })
})
