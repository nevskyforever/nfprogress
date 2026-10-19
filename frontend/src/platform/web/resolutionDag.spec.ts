// @vitest-environment node
import {it,expect} from 'vitest'
import {scope,amk} from './bootstrap.testFixture'
import {resolutionFixture} from './resolution.testFixture'
import {received} from './legacyNoteApply.testFixture'
import {makeHistoryCandidate,openHistoryCandidate} from './noteHistory'
import {openRetainedNote,noteProofDigest} from './legacyNoteApply'
import {frameContentNote} from '@/cloud/contentNoteCodec'
import {encryptObjectBytes} from '@/crypto'
import {encodeBase64Url} from '@/api/base64url'
import {inspectResolutionDag} from './resolutionDag'
it('64 genuine original-AEAD leaves: structural DAG consumes every parent, no apply/ACK claim',async()=>{
 const f=await resolutionFixture(),root=f.inventory.history.find((r:any)=>r.record_kind==='candidate'&&r.header.revision===1) as any
 const leaves=[...f.parents]
 // Each additional leaf has real original AEAD; only ordinary leaf readers are used.
 // There are deliberately no fabricated conflict/apply/ACK proofs for these leaves.
 for(let i=2;i<64;i++){
  const row=await received(f.f,10+i,2,root.event_id,'upsert',p=>{p.note.metadata={}},'content-note')
  const wire=JSON.parse(row.wire_item),{device_id,server_sequence:_seq,...event}=wire.event
  const plaintext=await openRetainedNote(scope,amk,row as never)
  leaves.push(await makeHistoryCandidate(scope,f.f.b,3,device_id,{event,object:wire.object},plaintext,'peer',null))
 }
 for(const leaf of leaves)await openHistoryCandidate(scope,leaf,amk)
 const ids=leaves.map(c=>c.event_id).sort(),r=structuredClone(f.r),content=structuredClone(f.content)
 if(content.event.version!==2)throw Error('resolution fixture required')
 content.event.header.parent_event_id=ids[0]!;content.event.header.additional_parent_event_ids=ids.slice(1);content.event.resolution.resolved_event_ids=ids
 r.parent_event_ids=ids;r.header=content.event.header;r.payload_digest=await noteProofDigest(content.event)
 const frame=frameContentNote(content),object=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},frame),wire=JSON.parse(r.wire_item)
 try{
  wire.object={crypto_version:1,aad_version:1,nonce:encodeBase64Url(object.nonce),ciphertext:encodeBase64Url(object.ciphertext)};r.wire_item=JSON.stringify(wire)
  const history=[root,...leaves,r],dag=inspectResolutionDag(scope,history)
  expect(dag.resolve('p','content-note',r.bootstrap_id,r.event_id).parents).toHaveLength(64)
  expect(dag.frontier('p','content-note',r.bootstrap_id)).toEqual([r.event_id])
  expect(()=>inspectResolutionDag(scope,history.filter(c=>c!==leaves[63]))).toThrow()
  expect(()=>inspectResolutionDag(scope,[...history,{...leaves[0],project_id:'foreign'}])).toThrow()
 }finally{frame.fill(0);object.nonce.fill(0);object.ciphertext.fill(0)}
},15000)
