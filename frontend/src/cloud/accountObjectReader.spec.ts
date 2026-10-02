// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'
import { AccountObjectReader, authenticateAccountObject, type ReceivedAccountObject } from './accountObjectReader'
import { encryptAccountObject } from '@/crypto/accountObjectCrypto'
import { asAccountMasterKey, encryptObjectBytes } from '@/crypto'
import { openProjectMetadataEvent } from './projectMetadataCodec'
import { openStructuralEvent } from './stageCodec'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
const USER='123e4567-e89b-42d3-a456-426614174000', DEVICE='123e4567-e89b-42d3-a456-426614174001'
const amk=asAccountMasterKey(new Uint8Array(32)),context={userId:USER,scope:'account' as const,entityId:'folder',entityType:'folder'}
async function row():Promise<ReceivedAccountObject>{
  const object=await encryptAccountObject(amk,context,new TextEncoder().encode('{"synthetic":"future payload"}'))
  return {event_id:DEVICE,server_sequence:1,canonical_user_id:USER,scope:'account',entity_id:'folder',entity_type:'folder',...object,nonce:Array.from(object.nonce),ciphertext:Array.from(object.ciphertext)}
}
describe('production account reader readiness',()=>{
  it('authenticates then returns a typed non-apply blocker, including unsupported frame bytes',async()=>{
    const received=await row();expect(await authenticateAccountObject(amk,USER,received)).toBe('account_entity_codec_not_activated')
    for(const changed of [{scope:'project'},{canonical_user_id:DEVICE},{entity_type:'note'},{crypto_version:1},{aad_version:1}]) expect(await authenticateAccountObject(amk,USER,{...received,...changed})).toBe('account_scope_rejected')
    await expect(authenticateAccountObject(amk,USER,{...received,entity_id:'other'})).rejects.toThrow()
    const project=await encryptObjectBytes(amk,{userId:USER,projectId:'account',entityId:'folder',entityType:'folder'},new Uint8Array(16))
    expect(await authenticateAccountObject(amk,USER,{...received,...project,nonce:Array.from(project.nonce),ciphertext:Array.from(project.ciphertext)})).toBe('account_scope_rejected')
  })
  it('cannot enter metadata or Stage readers, even when envelope versions are relabeled',async()=>{
    const r=await row(), object={crypto_version:1 as const,aad_version:1 as const,nonce:new Uint8Array(r.nonce),ciphertext:new Uint8Array(r.ciphertext)}
    await expect(openProjectMetadataEvent(amk,{account_id:USER,project_id:'account',entity_id:'folder',event_id:DEVICE},object)).rejects.toThrow()
    await expect(openStructuralEvent(amk,{account_id:USER,project_id:'account',entity_id:'folder',entity_type:'stage',event_id:DEVICE},object)).rejects.toThrow()
  })
  it('wires bounded ordered native receipt to decrypt and durable blocker with canonical lease checks',async()=>{
    const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-02T00:00:00Z'})})
    await auth.login('u','p');const context=auth.requireContext(),r=await row()
    const bindings={ensureForCurrentUser:vi.fn(async()=>({context}))},identity={read:vi.fn(async()=>({local_account_id:'local',device_id:DEVICE}))}
    const lease={canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(action:(key:typeof amk)=>Promise<unknown>)=>action(amk)}
    const keys={leaseForAccount:vi.fn(()=>lease)}
    const inbox={received:vi.fn().mockResolvedValueOnce([r]).mockResolvedValueOnce([]),block:vi.fn().mockResolvedValue(undefined)}
    const reader=new AccountObjectReader(auth,bindings as never,identity as never,keys as never,inbox)
    expect(await reader.readOnce('local',DEVICE,1,2)).toEqual({blocked:['account_entity_codec_not_activated'],listed:1,hasRemainingWork:false})
    expect(inbox.block).toHaveBeenCalledWith({account_id:'local',canonical_user_id:USER,device_id:DEVICE},r,'account_entity_codec_not_activated')
    lease.canonicalUserId=DEVICE
    await expect(reader.readOnce('local',DEVICE)).rejects.toThrow()
    expect(inbox.received).toHaveBeenCalledTimes(2)
    lease.canonicalUserId=USER
    inbox.received.mockReset().mockImplementation(async (_scope, _limit, after) =>
      after===0?[r]:after===1?[{...r,server_sequence:2}]:[])
    await reader.readOnce('local',DEVICE,1,1)
    await reader.readOnce('local',DEVICE,1,1)
    await reader.readOnce('local',DEVICE,1,1)
    await reader.readOnce('local',DEVICE,1,1)
    expect(inbox.received.mock.calls.map(call=>call[2])).toEqual([0,1,2,0])
  })
})
