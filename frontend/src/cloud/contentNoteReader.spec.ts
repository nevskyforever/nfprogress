// @vitest-environment node
import {describe,it,expect,vi} from 'vitest'
import fixture from './__fixtures__/contentNoteCodecV1.json'
import {ContentNoteReader,type ContentNoteInboxItem} from './contentNoteReader'
import {frameContentNote,openContentNote,type ContentNoteEvent} from './contentNoteCodec'
import {asAccountMasterKey,encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {NormalUserAuthRuntime} from '@/auth/userAuth'
const event=()=>structuredClone(fixture.examples[0]!.event) as ContentNoteEvent
const USER=event().account_id,DEVICE='123e4567-e89b-42d3-a456-426614174001'
const amk=asAccountMasterKey(new Uint8Array(32))
async function received(bytes=frameContentNote(event())):Promise<ContentNoteInboxItem>{
 const e=event(),h=e.event.header
 const o=await encryptObjectBytes(amk,{userId:USER,projectId:h.project_id,entityId:h.entity_id,entityType:'note'},bytes)
 return {event_id:h.event_id,server_sequence:9,source_device_id:e.device_id,project_id:h.project_id,entity_id:h.entity_id,entity_type:'note',operation:'event',revision:h.revision,updated_at:h.updated_at,deleted_at:null,envelope:{...o,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}}
}
async function setup(){
 const auth=new NormalUserAuthRuntime({login:vi.fn().mockResolvedValue({access_token:'token',refresh_token:'refresh',access_expires_in:60}),refresh:vi.fn(),logout:vi.fn(),me:vi.fn().mockResolvedValue({id:USER,username:'u',email:'u@example.test',email_verified:true,role:'user',status:'active',created_at:'2026-10-02T00:00:00Z'})})
 await auth.login('u','p');const context=auth.requireContext()
 const bindings={ensureForCurrentUser:vi.fn(async()=>({context}))},identity={read:vi.fn(async()=>({local_account_id:'a',device_id:DEVICE}))}
 const lease={canonicalUserId:USER,authEpoch:context.authEpoch,isCurrent:()=>true,use:(f:(k:typeof amk)=>Promise<unknown>)=>f(amk)}
 const repo={received:vi.fn().mockResolvedValue([]),apply:vi.fn().mockResolvedValue('applied'),block:vi.fn().mockResolvedValue(undefined)}
 const reader=new ContentNoteReader(auth,bindings as never,identity as never,{leaseForAccount:()=>lease} as never,repo)
 return {auth,reader,lease,repo}
}
describe('production C18 Note reader with unchanged C11 crypto',()=>{
 it('decrypts real ciphertext, forwards exact frame and clears temporary buffers',async()=>{
  const {reader,repo}=await setup(),row=await received();let copied:number[]=[]
  repo.received.mockResolvedValueOnce([row]).mockResolvedValueOnce([])
  repo.apply.mockImplementation(async command=>{copied=[...command.plaintext];return 'applied'})
  expect(await reader.readOnce('a',DEVICE,1,2)).toEqual({blocked:[],hasRemainingWork:false,listed:1})
  expect(copied).toEqual([...frameContentNote(event())]);expect(repo.block).not.toHaveBeenCalled()
  expect(repo.apply.mock.calls[0]![0].plaintext.every((b:number)=>b===0)).toBe(true)
 })
 it('retains unsupported authenticated frames through native classification without fallback',async()=>{
  const {reader,repo}=await setup(),frame=frameContentNote(event());frame[9]=99
  repo.received.mockResolvedValueOnce([await received(frame)]);repo.apply.mockResolvedValue('content_note_codec_unsupported')
  expect((await reader.readOnce('a',DEVICE)).blocked).toEqual(['content_note_codec_unsupported'])
  expect(repo.apply).toHaveBeenCalledTimes(1);expect(repo.block).not.toHaveBeenCalled()
 })
 it('AEAD wrong project/entity/account and altered ciphertext never reach apply',async()=>{
  for(const change of ['project','entity','cipher']){
   const {reader,repo}=await setup(),row=await received()
   if(change==='project')row.project_id='foreign';if(change==='entity')row.entity_id='foreign'
   if(change==='cipher')row.envelope.ciphertext=row.envelope.ciphertext.slice(0,-2)+'AA'
   repo.received.mockResolvedValueOnce([row]);expect((await reader.readOnce('a',DEVICE)).blocked).toEqual(['decrypt_failed'])
   expect(repo.apply).not.toHaveBeenCalled();expect(repo.block).toHaveBeenCalledTimes(1)
  }
  const e=event(),frame=frameContentNote(e),h=e.event.header
  const envelope=await encryptObjectBytes(amk,{userId:USER,projectId:h.project_id,entityId:h.entity_id,entityType:'note'},frame)
  const context={account_id:USER,project_id:h.project_id,entity_id:h.entity_id,event_id:h.event_id,device_id:e.device_id,revision:h.revision,updated_at:h.updated_at}
  for(const changes of [{account_id:DEVICE},{event_id:DEVICE},{device_id:DEVICE},{revision:2}])await expect(openContentNote(amk,{...context,...changes},envelope)).rejects.toThrow()
 })
 it('bounded keyset revisits retained dependency blockers fairly and enforces lease scope',async()=>{
  const {reader,repo,lease}=await setup(),row=await received()
  repo.received.mockImplementation(async (_s,_l,after)=>after===0?[row]:after===9?[{...row,server_sequence:10}]:[])
  repo.apply.mockResolvedValue('orphan')
  for(let i=0;i<4;i++)await reader.readOnce('a',DEVICE,1,1)
  expect(repo.received.mock.calls.map(c=>c[2])).toEqual([0,9,10,0])
  lease.canonicalUserId=DEVICE;await expect(reader.readOnce('a',DEVICE)).rejects.toThrow()
  expect(repo.block).not.toHaveBeenCalled()
 })
 it('revoked key lease and logout prevent native apply/block mutations',async()=>{
  const h=await setup(),row=await received();h.repo.received.mockResolvedValueOnce([row])
  h.lease.use=f=>{h.lease.isCurrent=()=>false;return f(amk)}
  await expect(h.reader.readOnce('a',DEVICE)).rejects.toThrow()
  expect(h.repo.apply).not.toHaveBeenCalled();expect(h.repo.block).not.toHaveBeenCalled()
  const other=await setup();other.repo.received.mockImplementationOnce(async()=>{await other.auth.logout();return [row]})
  await expect(other.reader.readOnce('a',DEVICE)).rejects.toThrow()
  expect(other.repo.apply).not.toHaveBeenCalled();expect(other.repo.block).not.toHaveBeenCalled()
 })
 it('legacy routes reject before decryption',async()=>{
  const {reader,repo}=await setup(),row=await received()
  repo.received.mockResolvedValueOnce([{...row,operation:'upsert'}])
  await expect(reader.readOnce('a',DEVICE)).rejects.toThrow('content_note_scope_mismatch')
  expect(repo.apply).not.toHaveBeenCalled()
 })
})
