import { describe, expect, it, vi } from 'vitest'
import { encodeV2Push, encryptedSyncV2Api, parseV2Capabilities, parseV2PullResponse, parseV2PushResponse, V2MalformedPullResponseError, V2UnsupportedEventError } from './encryptedSyncV2'
import { ApiResponseTooLargeError } from './client'
const id='123e4567-e89b-42d3-a456-426614174001'
const request=()=>({protocol_version:2 as const,encrypted_sync_version:2 as const,device_id:id,items:[{event:{event_id:id,project_id:'p',entity_id:'n',entity_type:'note' as const,operation:'resolution' as const,revision:2,updated_at:'2026-01-01T00:00:00.000000Z',deleted_at:null},object:{crypto_version:1 as const,aad_version:1 as const,nonce:'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',ciphertext:'AAAAAAAAAAAAAAAAAAAAAA'}}]})
describe('encrypted sync v2',()=>{
 it('validates dormant capability and exact opaque resolution wire data',()=>{expect(parseV2Capabilities({supported_transport_version:2,writer_transport_version:2,cutover_epoch:0})).toMatchObject({writer_transport_version:2});expect(JSON.parse(encodeV2Push(request())).items[0].event.operation).toBe('resolution')})
 it('rejects malformed capability, envelope and receipt sets',()=>{expect(()=>parseV2Capabilities({supported_transport_version:2,writer_transport_version:3,cutover_epoch:0})).toThrow();const bad=request();bad.items[0]!.object.nonce='=';expect(()=>encodeV2Push(bad)).toThrow();expect(()=>parseV2PushResponse({protocol_version:2,encrypted_sync_version:2,results:[],current_cursor:0},[id])).toThrow()})
 it('requires one unique receipt per event',()=>{expect(parseV2PushResponse({protocol_version:2,encrypted_sync_version:2,results:[{event_id:id,server_sequence:1,duplicate:true}],current_cursor:1},[id]).results[0]!.duplicate).toBe(true)})
 it('rejects non-canonical identity, duplicate events and invalid backend metadata before HTTP',()=>{const uppercase=request();uppercase.device_id=id.toUpperCase();expect(()=>encodeV2Push(uppercase)).toThrow();const duplicate=request();duplicate.items.push(duplicate.items[0]!);expect(()=>encodeV2Push(duplicate)).toThrow();const invalidTimestamp=request();invalidTimestamp.items[0]!.event.updated_at='not-a-timestamp';expect(()=>encodeV2Push(invalidTimestamp)).toThrow();const oversizedProject=request();oversizedProject.items[0]!.event.project_id='p'.repeat(513);expect(()=>encodeV2Push(oversizedProject)).toThrow()})
 it('rejects foreign or non-canonical receipts and duplicate server sequences',()=>{const other='123e4567-e89b-42d3-a456-426614174002';expect(()=>parseV2PushResponse({protocol_version:2,encrypted_sync_version:2,results:[{event_id:other,server_sequence:1,duplicate:false}],current_cursor:1},[id])).toThrow();expect(()=>parseV2PushResponse({protocol_version:2,encrypted_sync_version:2,results:[{event_id:id.toUpperCase(),server_sequence:1,duplicate:false}],current_cursor:1},[id])).toThrow();expect(()=>parseV2PushResponse({protocol_version:2,encrypted_sync_version:2,results:[{event_id:id,server_sequence:1,duplicate:false},{event_id:other,server_sequence:1,duplicate:false}],current_cursor:1},[id,other])).toThrow()})
})

const wireObject=()=>({crypto_version:1,aad_version:1,nonce:'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',ciphertext:'AAAAAAAAAAAAAAAAAAAAAA'})
const wireEvent=(n:number,operation:'upsert'|'delete'|'resolution'='upsert')=>({
 event_id:`123e4567-e89b-42d3-a456-42661417400${n}`,device_id:id,server_sequence:n,
 project_id:'project',entity_id:'note',entity_type:'note',operation,revision:operation==='resolution'?2:1,
 updated_at:'2026-01-01T00:00:00Z',deleted_at:operation==='delete'?'2026-01-02T00:00:00Z':null,
})
const wirePage=(items:unknown[]=[],since=0)=>({protocol_version:2,encrypted_sync_version:2,items,next_cursor:items.length?(items.at(-1) as {event:{server_sequence:number}}).event.server_sequence:since,has_more:false})
const wireItem=(n:number,operation:'upsert'|'delete'|'resolution'='upsert')=>({event:wireEvent(n,operation),object:wireObject()})

describe('strict encrypted v2 pull and ACK',()=>{
 it('accepts empty and mixed historical pages without decrypting or changing tombstones',()=>{
  expect(parseV2PullResponse(wirePage(),0,200)).toMatchObject({next_cursor:0,items:[]})
  const items=[wireItem(1),wireItem(2,'delete'),wireItem(3,'resolution')]
  const parsed=parseV2PullResponse(wirePage(items),0,200)
  expect(parsed.items.map(x=>[x.event.operation,x.event.deleted_at])).toEqual([
   ['upsert',null],['delete','2026-01-02T00:00:00Z'],['resolution',null],
  ])
  expect(parsed.items[0]!.object.ciphertext).toEqual(new Uint8Array(16))
 })
 it('rejects order, identities, event types, timestamps and pagination errors',()=>{
  const valid=wirePage([wireItem(1),wireItem(2)])
  const mutations:unknown[]=[
   {...valid,protocol_version:1},{...valid,encrypted_sync_version:1},
   {...valid,items:[wireItem(2),wireItem(1)]},
   {...valid,items:[wireItem(1),wireItem(1)]},
   {...valid,items:[wireItem(1),{...wireItem(2),event:{...wireEvent(2),server_sequence:1}}]},
   {...valid,items:[{...wireItem(1),event:{...wireEvent(1),event_id:'invalid'}}]},
   {...valid,items:[{...wireItem(1),event:{...wireEvent(1),updated_at:'invalid'}}]},
   {...valid,items:[{...wireItem(1,'delete'),event:{...wireEvent(1,'delete'),deleted_at:null}}]},
   {...valid,items:[{...wireItem(1,'resolution'),event:{...wireEvent(1,'resolution'),deleted_at:'2026-01-02T00:00:00Z'}}]},
   {...valid,items:[{...wireItem(1),event:{...wireEvent(1),operation:'event'}}]},
   {...valid,items:[{...wireItem(1),event:{...wireEvent(1),entity_type:'future'}}]},
   {...valid,items:[{...wireItem(1),object:null}]},
   {...valid,next_cursor:3},{...valid,has_more:'true'},
   {...wirePage(),has_more:true},
  ]
  for(const value of mutations)expect(()=>parseV2PullResponse(value,0,200)).toThrow()
  expect(()=>parseV2PullResponse(wirePage([{...wireItem(1),object:null}]),0,200)).toThrow(V2UnsupportedEventError)
  expect(()=>parseV2PullResponse(valid,-1,200)).toThrow(RangeError)
  expect(()=>parseV2PullResponse(valid,0,501)).toThrow(RangeError)
  expect(()=>parseV2PullResponse(valid,0,1)).toThrow()
 })
 it('rejects malformed crypto envelopes and ciphertext bounds',()=>{
  for(const object of [
   {...wireObject(),crypto_version:2},{...wireObject(),aad_version:2},
   {...wireObject(),nonce:'='},{...wireObject(),ciphertext:'='},
   {...wireObject(),nonce:'AA'}, {...wireObject(),ciphertext:'AA'},
   {...wireObject(),ciphertext:'A'.repeat(11_184_836)},
  ])expect(()=>parseV2PullResponse(wirePage([{event:wireEvent(1),object}]),0,200)).toThrow()
 })
 it('rejects aggregate ciphertext over the shared batch limit',()=>{
  const ciphertext='A'.repeat(11_184_820)
  expect(()=>parseV2PullResponse(wirePage([
   {event:wireEvent(1),object:{...wireObject(),ciphertext}},
   {event:wireEvent(2),object:{...wireObject(),ciphertext}},
  ]),0,200)).toThrow()
 },30_000)
 it('bounds HTTP pull body and sends exact v2 ACK with a 204 response',async()=>{
  const fetchMock=vi.spyOn(globalThis,'fetch')
  try{
   fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(wirePage()),{status:200}))
   await expect(encryptedSyncV2Api.pull('token',id,0)).resolves.toMatchObject({next_cursor:0})
   expect(String(fetchMock.mock.calls[0]![0])).toContain('protocol_version=2')
   fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({...wirePage(),protocol_version:1}),{status:200}))
   await expect(encryptedSyncV2Api.pull('token',id,0)).rejects.toBeInstanceOf(V2MalformedPullResponseError)
   fetchMock.mockResolvedValueOnce(new Response('{}',{status:200,headers:{'Content-Length':'33554433'}}))
   await expect(encryptedSyncV2Api.pull('token',id,0)).rejects.toBeInstanceOf(ApiResponseTooLargeError)
   fetchMock.mockResolvedValueOnce(new Response(null,{status:204}))
   await expect(encryptedSyncV2Api.ack('token',{protocol_version:2,encrypted_sync_version:2,device_id:id,cursor:3})).resolves.toBeUndefined()
   expect(JSON.parse(String(fetchMock.mock.calls[3]![1]?.body))).toEqual({protocol_version:2,encrypted_sync_version:2,device_id:id,cursor:3})
   await expect(encryptedSyncV2Api.ack('token',{protocol_version:2,encrypted_sync_version:2,device_id:id,cursor:-1})).rejects.toThrow()
   expect(fetchMock).toHaveBeenCalledTimes(4)
   fetchMock.mockResolvedValueOnce(new Response('{}',{status:200}))
   await expect(encryptedSyncV2Api.ack('token',{protocol_version:2,encrypted_sync_version:2,device_id:id,cursor:3})).rejects.toThrow()
  }finally{fetchMock.mockRestore()}
 })
})
