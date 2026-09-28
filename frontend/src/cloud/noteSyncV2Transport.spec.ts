import { describe, expect, it, vi } from 'vitest'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { NoteSyncInboxRepository } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type { NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { DurableNoteSyncV2Inbox, NoteSyncV2AckAdapter, NoteSyncV2TransportError } from './noteSyncV2Transport'

const USER='123e4567-e89b-42d3-a456-426614174099'
const DEVICE='123e4567-e89b-42d3-a456-426614174001'
const EVENT='123e4567-e89b-42d3-a456-426614174002'
function fixture(){
 const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-01-01T00:00:00Z'})})
 const binding=new AuthoritativeAccountBinding(auth,{ensure:vi.fn().mockResolvedValue('validated')})
 const identity={read:vi.fn().mockResolvedValue({local_account_id:'local',device_id:DEVICE}),provision:vi.fn()}
 const api={capabilities:vi.fn().mockResolvedValue({supported_transport_version:2,writer_transport_version:2,cutover_epoch:1}),pull:vi.fn(),ack:vi.fn().mockResolvedValue(undefined)}
 const inbox={readPullState:vi.fn().mockResolvedValue({pull_cursor:4,ack_cursor:2}),commitInboundPage:vi.fn().mockResolvedValue({committed_cursor:7,new_events:3,replayed_events:0,has_more:false})}
 const ack={prepare:vi.fn().mockResolvedValue({current_ack_cursor:2,candidate_cursor:4}),commit:vi.fn().mockResolvedValue('advanced')}
 return {auth,binding,identity,api,inbox,ack}
}
const item=(sequence:number,operation:'upsert'|'delete'|'resolution')=>({event:{event_id:EVENT.slice(0,-1)+sequence,device_id:DEVICE,server_sequence:sequence,project_id:'p',entity_id:'n',entity_type:'note' as const,operation,revision:operation==='resolution'?2:1,updated_at:'2026-01-01T00:00:00Z',deleted_at:operation==='delete'?'2026-01-02T00:00:00Z':null},object:{crypto_version:1 as const,aad_version:1 as const,nonce:new Uint8Array(24),ciphertext:new Uint8Array(16)}})
const page=()=>({protocol_version:2 as const,encrypted_sync_version:2 as const,items:[item(5,'upsert'),item(6,'delete'),item(7,'resolution')],next_cursor:7,has_more:false})

describe('dormant v2 durable adapters',()=>{
 it('reads native cursor and commits one validated mixed page',async()=>{
  const f=fixture();await f.auth.login('u','p');f.api.pull.mockResolvedValue(page())
  const adapter=new DurableNoteSyncV2Inbox(f.auth,f.binding,f.identity,f.inbox as unknown as NoteSyncInboxRepository,f.api)
  await expect(adapter.pullOnce('local',DEVICE)).resolves.toMatchObject({committed_cursor:7})
  expect(f.api.pull).toHaveBeenCalledWith('token',DEVICE,4)
  expect(f.inbox.commitInboundPage).toHaveBeenCalledWith(expect.objectContaining({since:4,nextCursor:7,items:page().items}),USER)
  f.inbox.commitInboundPage.mockResolvedValueOnce({committed_cursor:7,new_events:0,replayed_events:3,has_more:false})
  await expect(adapter.pullOnce('local',DEVICE)).resolves.toMatchObject({replayed_events:3})
  expect(f.api.pull).toHaveBeenLastCalledWith('token',DEVICE,4)
 })
 it('leaves native cursor untouched on lost pull, mode 1, stale auth, or wrong identity',async()=>{
  const f=fixture();await f.auth.login('u','p')
  const adapter=new DurableNoteSyncV2Inbox(f.auth,f.binding,f.identity,f.inbox as unknown as NoteSyncInboxRepository,f.api)
  f.api.pull.mockRejectedValueOnce(new Error('timeout'))
  await expect(adapter.pullOnce('local',DEVICE)).rejects.toThrow('timeout')
  f.api.capabilities.mockResolvedValueOnce({supported_transport_version:2,writer_transport_version:1,cutover_epoch:0})
  await expect(adapter.pullOnce('local',DEVICE)).rejects.toBeInstanceOf(NoteSyncV2TransportError)
  f.api.pull.mockImplementationOnce(async()=>{await f.auth.logout();return page()})
  await expect(adapter.pullOnce('local',DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
  expect(f.inbox.commitInboundPage).not.toHaveBeenCalled()
  await f.auth.login('u','p');f.identity.read.mockResolvedValueOnce({local_account_id:'other',device_id:DEVICE})
  await expect(adapter.pullOnce('local',DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
 })
 it('does not commit a malformed actual HTTP pull response',async()=>{
  const f=fixture();await f.auth.login('u','p')
  const adapter=new DurableNoteSyncV2Inbox(f.auth,f.binding,f.identity,f.inbox as unknown as NoteSyncInboxRepository,
   {...f.api,pull:encryptedSyncV2Api.pull})
  const fetchMock=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(new Response(JSON.stringify({
   protocol_version:2,encrypted_sync_version:2,items:[{event:{...item(5,'resolution').event,operation:'future'},object:null}],
   next_cursor:5,has_more:false,
  }),{status:200}))
  try{
   await expect(adapter.pullOnce('local',DEVICE)).rejects.toThrow()
   expect(f.inbox.commitInboundPage).not.toHaveBeenCalled()
  }finally{fetchMock.mockRestore()}
 })
 it('uses native contiguous ACK proof, HTTP first, then the native CAS result',async()=>{
  const f=fixture();await f.auth.login('u','p')
  const adapter=new NoteSyncV2AckAdapter(f.auth,f.binding,f.identity,f.ack as unknown as NoteSyncAckRepository,f.api)
  f.ack.prepare.mockResolvedValueOnce({current_ack_cursor:2,candidate_cursor:2})
  await expect(adapter.ackOnce('local',DEVICE)).resolves.toEqual({status:'no_progress',cursor:2})
  expect(f.api.capabilities).not.toHaveBeenCalled();expect(f.api.ack).not.toHaveBeenCalled();expect(f.ack.commit).not.toHaveBeenCalled()
  await expect(adapter.ackOnce('local',DEVICE)).resolves.toEqual({status:'advanced',cursor:4})
  expect(f.api.ack).toHaveBeenCalledWith('token',{protocol_version:2,encrypted_sync_version:2,device_id:DEVICE,cursor:4})
  expect(f.ack.commit).toHaveBeenCalledWith('local',DEVICE,USER,2,4)
  f.ack.commit.mockResolvedValueOnce('stale')
  await expect(adapter.ackOnce('local',DEVICE)).resolves.toEqual({status:'stale',cursor:4})
 })
 it('retries a lost server response and a failed local post-HTTP commit safely',async()=>{
  const f=fixture();await f.auth.login('u','p')
  const adapter=new NoteSyncV2AckAdapter(f.auth,f.binding,f.identity,f.ack as unknown as NoteSyncAckRepository,f.api)
  f.api.ack.mockRejectedValueOnce(new Error('timeout'))
  await expect(adapter.ackOnce('local',DEVICE)).rejects.toThrow('timeout')
  expect(f.ack.commit).not.toHaveBeenCalled()
  f.ack.commit.mockRejectedValueOnce(new Error('sqlite failure'))
  await expect(adapter.ackOnce('local',DEVICE)).rejects.toMatchObject({code:'native_failure'})
  await expect(adapter.ackOnce('local',DEVICE)).resolves.toEqual({status:'advanced',cursor:4})
  expect(f.api.ack).toHaveBeenCalledTimes(3)
 })
 it('rejects a regressive native ACK candidate before HTTP',async()=>{
  const f=fixture();await f.auth.login('u','p')
  f.ack.prepare.mockResolvedValueOnce({current_ack_cursor:4,candidate_cursor:3})
  const adapter=new NoteSyncV2AckAdapter(f.auth,f.binding,f.identity,f.ack as unknown as NoteSyncAckRepository,f.api)
  await expect(adapter.ackOnce('local',DEVICE)).rejects.toThrow('Invalid native ACK candidate')
  expect(f.api.capabilities).not.toHaveBeenCalled();expect(f.api.ack).not.toHaveBeenCalled()
 })
 it('does not commit on stale auth or incompatible mode',async()=>{
  const f=fixture();await f.auth.login('u','p')
  const adapter=new NoteSyncV2AckAdapter(f.auth,f.binding,f.identity,f.ack as unknown as NoteSyncAckRepository,f.api)
  f.api.capabilities.mockResolvedValueOnce({supported_transport_version:2,writer_transport_version:1,cutover_epoch:0})
  await expect(adapter.ackOnce('local',DEVICE)).rejects.toBeInstanceOf(NoteSyncV2TransportError)
  f.api.ack.mockImplementationOnce(async()=>{await f.auth.logout()})
  await expect(adapter.ackOnce('local',DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
  expect(f.ack.commit).not.toHaveBeenCalled()
 })
})
