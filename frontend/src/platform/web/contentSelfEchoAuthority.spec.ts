// @vitest-environment node
import {it,expect} from 'vitest'
import {scope} from './bootstrap.testFixture'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {validateContentNoteProof} from './contentNoteRecords'
import {validateNoteHistoryRecord} from './noteHistoryRecords'
import {validateBrowserUploadPair} from './syncDurability'

it.each([false,true])('own codec8 ID1=%s without outbound authority cannot write or cross prefix',async compressed=>{
 const f=await routeSetup(),runtime=new BrowserContentNoteApplyRuntime(f.notes)
 await contentRow(f,2,{compressed,change:e=>{e.device_id=scope.deviceId}})
 const before=structuredClone(f.db)
 await expect(runtime.apply(scope,2)).rejects.toMatchObject({code:'unsupported_local_source'})
 expect(f.db).toEqual(before)
 await contentRow(f,3,{id:'later-peer',compressed});expect(await runtime.apply(scope,3)).toBe('applied')
 expect((await f.proven.advance(scope))).toMatchObject({candidate_proven_prefix:1,first_blocking_sequence:2})
 expect(f.db.inbox[1]).toMatchObject({state:'received'})
 expect(f.db.outbox).toEqual([]);expect(f.db.receipts).toEqual([])
})

// Deliberate negative fixtures: generic storage accepts supplied wire, but that
// does not create a production Content writer, local candidate or authorship.
it.each(['sealed','accepted','wrong-sequence','wrong-wire'] as const)('fabricated %s Content outbox is never sufficient self-echo authority',async kind=>{
 const f=await routeSetup(),c=await contentRow(f,2,{change:e=>{e.device_id=scope.deviceId}})
 const wire=JSON.parse(c.row.wire_item),{device_id:_device,server_sequence:_seq,...event}=wire.event
 const raw=JSON.stringify({protocol_version:3,encrypted_sync_version:3,device_id:scope.deviceId,items:[{event,object:wire.object}]})
 const row=(await f.sync.enqueue(scope,[raw]))[0]!.item
 if(kind!=='sealed')await f.sync.commitUploadAcceptance(scope,row,{protocol_version:3,encrypted_sync_version:3,current_cursor:3,results:[{event_id:row.event_id,server_sequence:2,duplicate:false}]})
 if(kind==='wrong-sequence')(f.db.receipts[0] as {server_sequence:number}).server_sequence=3
 if(kind==='wrong-wire'){
  const out=f.db.outbox[0] as {raw_body:string},body=JSON.parse(out.raw_body)
  body.items[0].object.ciphertext=(body.items[0].object.ciphertext[0]==='A'?'B':'A')+body.items[0].object.ciphertext.slice(1);out.raw_body=JSON.stringify(body)
 }
 if(kind==='accepted')expect(validateBrowserUploadPair(f.db.outbox[0],f.db.receipts[0],scope)).toMatchObject({state:'accepted',protocol_version:3})
 const before=structuredClone(f.db)
 await expect(new BrowserContentNoteApplyRuntime(f.notes).apply(scope,2)).rejects.toMatchObject({code:'unsupported_local_source'})
 expect(f.db).toEqual(before)
 expect((await f.proven.advance(scope)).candidate_proven_prefix).toBe(1)
})

it.each([false,true])('a peer candidate cannot authorize an own codec8 event ID1=%s',async compressed=>{
 const f=await routeSetup(),runtime=new BrowserContentNoteApplyRuntime(f.notes);await contentRow(f,2,{compressed})
 await runtime.apply(scope,2)
 // Receive another event for the peer note under an authenticated own-device wrapper;
 // retaining a real peer candidate is explicitly not proof of local authorship.
 await contentRow(f,3,{compressed,change:e=>{e.device_id=scope.deviceId}})
 const before=structuredClone(f.db)
 await expect(runtime.apply(scope,3)).rejects.toMatchObject({code:'unsupported_local_source'});expect(f.db).toEqual(before)
 expect((await f.proven.advance(scope)).candidate_proven_prefix).toBe(2)
})

it.each(['44444444-4444-4444-8444-444444444444','55555555-5555-4555-8555-555555555555'])('same-account Content from device %s remains peer, never self-echo',async device=>{
 const f=await routeSetup(),c=await contentRow(f,2,{compressed:true,change:e=>{e.device_id=device}})
 expect(c.e.account_id).toBe(scope.canonicalUserId)
 expect(await new BrowserContentNoteApplyRuntime(f.notes).apply(scope,2)).toBe('applied')
 const row=f.db.inbox[1] as any,proof=validateContentNoteProof(row.content_note_proof,scope)
 expect(proof).toMatchObject({outcome:'applied',reference:{device_id:device}})
 const candidate=f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='candidate'&&r.event_id===c.row.event_id) as any
 expect(validateNoteHistoryRecord(candidate,scope)).toMatchObject({record_version:2,origin:'peer',source_device_id:device})
 expect(()=>validateContentNoteProof({...proof,reference:{...proof.reference,device_id:scope.deviceId}},scope)).toThrow()
 expect(()=>validateContentNoteProof({...proof,outcome:'self_echo_applied'},scope)).toThrow()
 expect(()=>validateContentNoteProof({...proof,source_revision:null,local_note_digest:null},scope)).toThrow()
 expect(()=>validateNoteHistoryRecord({...candidate,source_device_id:scope.deviceId},scope)).toThrow()
 expect(()=>validateNoteHistoryRecord({...candidate,origin:'local_sealed',source_device_id:scope.deviceId,mutation_generation:1},scope)).toThrow()
 expect((await f.proven.advance(scope)).candidate_proven_prefix).toBe(2)
})
