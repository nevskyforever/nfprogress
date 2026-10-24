// @vitest-environment node
import { beforeAll,it,expect } from 'vitest'
import { scope,amk } from './bootstrap.testFixture'
import { resolutionFixture,refreshResolutionFixture } from './resolution.testFixture'
import { authenticateResolutionHistory,BrowserResolutionHistoryReader } from './resolutionAuthentication'
import { inspectResolutionDag } from './resolutionDag'
import { validateResolution4,validateResolutionHead2,validateGroupTransition2,validateResolutionProof1,validateResolutionInbox10,readFutureHistoryRecord,readFutureInboxRecord,MAX_RESOLUTION_EVIDENCE_BYTES,boundResolutionJson } from './resolutionRecords'
import { validateNoteHistoryRecord,validateNoteHistorySet } from './noteHistoryRecords'
import { validateBrowserInboxRecord } from './syncDurability'
let sample:Awaited<ReturnType<typeof resolutionFixture>>
beforeAll(async()=>{sample=await resolutionFixture()})
function tamperCiphertext(original:string){
 if(!original.length)throw new Error('Empty test ciphertext')
 const tampered=(original[0]==='A'?'B':'A')+original.slice(1)
 expect(tampered).not.toBe(original)
 return tampered
}
it('ciphertext tampering always changes a valid base64url character',()=>{
 for(const original of ['Aabc_012-','zabc_012-']){
  const tampered=tamperCiphertext(original)
  expect(tampered).not.toBe(original)
  expect(tampered).toMatch(/^[A-Za-z0-9_-]+$/)
  expect(tampered.slice(1)).toBe(original.slice(1))
 }
})
it.each(['choose_version','manual_merge','delete','keep_both'] as const)('genuine encrypted %s evidence and original wire authenticate read-only',async strategy=>{
 const f=await resolutionFixture(strategy),old=structuredClone(f.f.db),inventory=structuredClone(f.inventory)
 const result=await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)
 expect(result.resolutions).toBe(1);expect(result.groups[0]!.effective).toBe('resolved')
 expect(f.f.db).toEqual(old);expect(f.inventory).toEqual(inventory)
 if(strategy==='keep_both'){expect(result.dag.resolve('p','retained-note',f.r.bootstrap_id,f.r.event_id).kind).toBe('retained');expect(result.dag.events.get(f.r.event_id)?.record_kind).toBe('resolution')}
})
const leaves={r:validateResolution4,h:validateResolutionHead2,transition:validateGroupTransition2,proof:validateResolutionProof1,row:validateResolutionInbox10}
for(const name of Object.keys(leaves) as (keyof typeof leaves)[])it(`${name} strict field/version/scope dispatch`,()=>{
 const original=sample[name],validate=leaves[name];expect(validate(original,scope)).toEqual(original)
 for(const key of Object.keys(original)){const bad={...original} as any;delete bad[key];expect(()=>validate(bad,scope)).toThrow()}
 for(const patch of [{extra:true},{record_version:999},{account_id:crypto.randomUUID()},{bootstrap_id:'bad'}])expect(()=>validate({...original,...patch},scope)).toThrow()
})
it('v9 validators remain closed to v10 variants; old records round-trip unchanged',()=>{
 expect(()=>validateNoteHistoryRecord(sample.r,scope)).toThrow();expect(()=>validateNoteHistoryRecord(sample.h,scope)).toThrow();expect(()=>validateBrowserInboxRecord(sample.row,scope)).toThrow()
 const old=sample.f.db.legacyNoteHistory!;expect(validateNoteHistorySet(scope,old)).toEqual(old)
 for(const row of old)expect(readFutureHistoryRecord(row,scope)).toEqual(row)
 for(const row of sample.f.db.inbox)expect(readFutureInboxRecord(row,scope)).toEqual(row)
 expect(readFutureHistoryRecord(sample.r,scope)).toEqual(sample.r);expect(readFutureInboxRecord(sample.row,scope)).toEqual(sample.row)
})
it.each(['ciphertext','key','wire','account','device','bootstrap','digest','inner','source','parent-witness','closure','circular-proof'] as const)('authenticated %s rejection',async kind=>{
 const f=await resolutionFixture(),old=structuredClone(f.f.db)
 if(kind==='ciphertext')f.r.evidence_envelope.ciphertext=tamperCiphertext(f.r.evidence_envelope.ciphertext)
 if(kind==='wire'){const w=JSON.parse(f.r.wire_item);w.object.ciphertext=tamperCiphertext(w.object.ciphertext);f.r.wire_item=JSON.stringify(w)}
 if(kind==='digest')f.r.payload_digest='0'.repeat(64)
 if(kind==='bootstrap')f.r.bootstrap_id=crypto.randomUUID()
 if(['inner','source','parent-witness','circular-proof'].includes(kind)){
  if(kind==='inner')f.evidence.kind='wrong_kind' as never
  if(kind==='source')f.evidence.source_after.notes[0]!.note_revision=7
  if(kind==='parent-witness')f.evidence.parents[0]!.snapshot_digest='0'.repeat(64)
  if(kind==='circular-proof')f.evidence.parents[0]!.event_id=f.r.event_id
  await refreshResolutionFixture(f)
 }
 if(kind==='closure')f.transition.from_generation++
 const s={...scope,...(kind==='account'?{accountId:crypto.randomUUID()}:{}),...(kind==='device'?{deviceId:crypto.randomUUID()}: {})}
 await expect(authenticateResolutionHistory(s,f.inventory,kind==='key'?new Uint8Array(32) as typeof amk:amk,()=>true)).rejects.toThrow()
 expect(f.f.db).toEqual(old)
})
it('stale scope cannot verify even with genuine key; invalidation during async crypto aborts',async()=>{
 await expect(authenticateResolutionHistory(scope,sample.inventory,amk,()=>false)).rejects.toMatchObject({code:'closed'})
 let count=0;await expect(authenticateResolutionHistory(scope,sample.inventory,amk,()=>++count<4)).rejects.toMatchObject({code:'closed'})
 const f=sample.f;const reader=new BrowserResolutionHistoryReader(f.auth,f.bindings as never,f.keys as never,()=>true)
 expect((await reader.read(scope,sample.inventory)).readOnly).toBe(true)
 f.lock();await expect(reader.read(scope,sample.inventory)).rejects.toThrow()
})
it('duplicate/contradictory event and closure identities cannot enter DAG',()=>{
 for(const r of [sample.r,sample.transition,sample.h])expect(()=>inspectResolutionDag(scope,[...sample.inventory.history,structuredClone(r)])).toThrow()
})
it('wrong parent/revision/scope/clone references reject without choosing a branch',()=>{
 for(const change of [(r:any)=>r.parent_event_ids.pop(),(r:any)=>r.header.revision++,(r:any)=>r.project_id='foreign',(r:any)=>r.note_id='foreign',(r:any)=>r.header.additional_parent_event_ids=[r.header.parent_event_id]]){
  const r=structuredClone(sample.r);change(r);expect(()=>inspectResolutionDag(scope,sample.inventory.history.map(h=>h===sample.r?r:h))).toThrow()
 }
 const h=structuredClone(sample.h);h.note_id='borrowed';expect(()=>inspectResolutionDag(scope,[...sample.inventory.history,h])).toThrow()
})
it('size limits reject cheaply and cycles reject without recursive serialization',()=>{
 expect(()=>boundResolutionJson({value:'x'.repeat(100)},32)).toThrow()
 const circular:any={};circular.self=circular;expect(()=>boundResolutionJson(circular)).toThrow()
 // Length metadata can be tested without repeatedly allocating a 64 MiB fixture.
 const nonce=structuredClone(sample.r);nonce.evidence_envelope.nonce='A'.repeat(33);expect(()=>validateResolution4(nonce,scope)).toThrow()
 const r=structuredClone(sample.r);r.evidence_envelope.ciphertext={length:Math.ceil((MAX_RESOLUTION_EVIDENCE_BYTES+16)*4/3)+1} as never
 expect(()=>validateResolution4(r,scope)).toThrow()
})

it.each([2,3])('%i genuine published parent branches authenticate, all edges consumed',async count=>{
 const f=await resolutionFixture('choose_version',count),result=await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)
 expect(result.dag.resolve('p','content-note',f.r.bootstrap_id,f.r.event_id).parents).toHaveLength(count)
 expect(result.dag.frontier('p','content-note',f.r.bootstrap_id)).toEqual([f.r.event_id])
},15000)
it('missing parent and cyclic ordinary ancestry reject in the structural pass',()=>{
 const missing=sample.inventory.history.filter((h:any)=>h.event_id!==sample.r.parent_event_ids[0]);expect(()=>inspectResolutionDag(scope,missing)).toThrow()
 const history=structuredClone(sample.inventory.history),root=history.find((h:any)=>h.record_kind==='candidate'&&h.header.revision===1) as any
 root.header.parent_event_id=sample.r.event_id;root.header.revision=4
 const w=JSON.parse(root.wire_item);w.event.revision=4;root.wire_item=JSON.stringify(w)
 expect(()=>inspectResolutionDag(scope,history)).toThrow()
})

it('published local Legacy parent before self-echo uses actual outbox/receipt, not invented inbox proof',async()=>{
 const f=await resolutionFixture('choose_version',2,true),local=f.evidence.parents.find(p=>p.publication_source==='local_accepted')!
 expect(f.f.db.inbox.some((r:any)=>r.event_id===local.event_id)).toBe(false)
 expect((await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).resolutions).toBe(1)
 f.f.db.receipts.length=0;f.inventory.receipts=[]
 await expect(authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).rejects.toThrow()
})
it.each(['legacy','id1'] as const)('%s original retained wire is reopened with its actual frozen decoder',async mode=>{
 const f=await resolutionFixture(),{reframeResolutionFixture}=await import('./resolution.testFixture');await reframeResolutionFixture(f,mode)
 expect((await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).resolutions).toBe(1)
})
it.each(['logout','key','profile','account','device'] as const)('real runtime %s scope invalidation',async kind=>{
 const f=await resolutionFixture();let active=true
 const reader=new BrowserResolutionHistoryReader(f.f.auth,f.f.bindings as never,f.f.keys as never,()=>active)
 if(kind==='logout')await f.f.auth.logout();if(kind==='key')f.f.unavailable();if(kind==='profile')active=false
 const changed={...scope,...(kind==='account'?{accountId:crypto.randomUUID()}:{}),...(kind==='device'?{deviceId:crypto.randomUUID()}: {})}
 await expect(reader.read(changed,f.inventory)).rejects.toThrow()
})
it('new fork after Resolution preserves the authenticated closed group and remains unresolved',async()=>{
 const f=await resolutionFixture(),{received}=await import('./legacyNoteApply.testFixture'),{makeHistoryCandidate}=await import('./noteHistory'),{openRetainedNote}=await import('./legacyNoteApply')
 const children=[]
 for(let i=0;i<2;i++){
  const row=await received(f.f,6+i,4,f.r.event_id,'upsert',p=>{p.note.metadata={}},'content-note'),w=JSON.parse(row.wire_item),{device_id,server_sequence:_seq,...event}=w.event
  const c=await makeHistoryCandidate(scope,f.f.b,3,device_id,{event,object:w.object},await openRetainedNote(scope,amk,row as never),'peer',null);children.push(c);f.inventory.history.push(c);f.inventory.rows.push(row)
 }
 children.sort((a,b)=>a.event_id.localeCompare(b.event_id))
 const group=structuredClone(f.evidence.group_snapshot),id=crypto.randomUUID()
 Object.assign(group,{record_id:id,group_id:id,common_parent_event_id:f.r.event_id,tip_revision:4,conflict_generation:1,tip_event_ids:children.map(c=>c.event_id),members:children.map((c,i)=>({version_id:`${i?'remote':'applied'}:${scope.accountId}:${c.event_id}`,event_id:c.event_id,source:i?'remote':'remote_applied',server_sequence:i?7:6,conflict_generation:1}))})
 f.inventory.history.push(group);f.h.head_revision++;f.h.linear_head_event_id=children[0]!.event_id;f.h.tip_event_ids=children.map(c=>c.event_id);f.h.node_ref={kind:'candidate',event_id:children[0]!.event_id}
 const result=await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)
 expect(result.groups.map(g=>g.effective).sort()).toEqual(['open','resolved'])
})
it('inbox10 shape is never a v9 prefix/ACK qualification',async()=>{
 const {calculateBrowserPrefix}=await import('./provenPrefixRecords')
 expect(()=>calculateBrowserPrefix(scope,sample.inventory)).toThrow()
 const before=structuredClone(sample.f.db.cursors);await authenticateResolutionHistory(scope,sample.inventory,amk,()=>true);expect(sample.f.db.cursors).toEqual(before)
})
it.each(['wire_digest','payload_digest','dependency_digest','record_digest','remote_group_id','local_group_id','source_device_id','event_id','parent_event_ids','server_sequence','remote_generation','local_generation'] as const)('Resolution4 rejects malformed %s',field=>{
 const r=structuredClone(sample.r);(r as any)[field]=['server_sequence','remote_generation','local_generation'].includes(field)?Number.MAX_SAFE_INTEGER+1:field==='parent_event_ids'?[]:'bad'
 expect(()=>validateResolution4(r,scope)).toThrow()
})
it('canonical header time and explicit expected bootstrap are strict',()=>{
 const r=structuredClone(sample.r);r.header.updated_at='2026-10-19';expect(()=>validateResolution4(r,scope)).toThrow()
 for(const name of Object.keys(leaves) as (keyof typeof leaves)[])expect(()=>leaves[name](sample[name],scope,crypto.randomUUID())).toThrow()
})
it('keep_both child may use only the exact retained output anchor',async()=>{
 const f=await resolutionFixture('keep_both'),{received}=await import('./legacyNoteApply.testFixture'),{makeHistoryCandidate}=await import('./noteHistory'),{openRetainedNote}=await import('./legacyNoteApply')
 const row=await received(f.f,6,4,f.r.event_id,'upsert',p=>{p.note.metadata={}},'retained-note'),w=JSON.parse(row.wire_item),{device_id,server_sequence:_s,...event}=w.event
 const child=await makeHistoryCandidate(scope,f.f.b,3,device_id,{event,object:w.object},await openRetainedNote(scope,amk,row as never),'peer',null)
 f.inventory.history.push(child);f.inventory.rows.push(row)
 f.cloneHead!.head_revision++;f.cloneHead!.linear_head_event_id=child.event_id;f.cloneHead!.tip_event_ids=[child.event_id];f.cloneHead!.node_ref={kind:'candidate',event_id:child.event_id}
 const result=await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)
 expect(result.dag.resolve('p','retained-note',f.r.bootstrap_id,child.event_id).parents).toHaveLength(1)
 const wrong=structuredClone(f.h);wrong.note_id='borrowed';wrong.node_ref={kind:'resolution_result',resolution_event_id:f.r.event_id,result_role:'retained',resolution_digest:f.r.record_digest}
 expect(()=>inspectResolutionDag(scope,[...f.inventory.history,wrong])).toThrow()
})
it('matching hashes and a valid evidence envelope cannot legitimize a different encrypted result source',async()=>{
 const f=await resolutionFixture(),{decryptObjectBytes}=await import('@/crypto'),{decodeBase64Url}=await import('@/api/base64url'),{sealResolutionFixture}=await import('./resolution.testFixture')
 const row=f.evidence.source_after.notes[0]!,e=row.envelope,bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:row.note_id,entityType:'note'},{...e,nonce:decodeBase64Url(e.nonce),ciphertext:decodeBase64Url(e.ciphertext)})
 const payload=JSON.parse(new TextDecoder().decode(bytes));bytes.fill(0);payload.source.note.content='UNAUTHORIZED_RESULT'
 row.envelope=await sealResolutionFixture(payload,row.note_id);await refreshResolutionFixture(f)
 await expect(authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).rejects.toThrow()
 const g=await resolutionFixture()
 for(const witness of [g.evidence.source_before,g.evidence.source_after]){const e=witness.project.envelope,b=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'p',entityType:'project_metadata'},{...e,nonce:decodeBase64Url(e.nonce),ciphertext:decodeBase64Url(e.ciphertext)}),p=JSON.parse(new TextDecoder().decode(b));b.fill(0);p.member_ids.push('x'.repeat(513));p.member_ids.sort();witness.project.envelope=await sealResolutionFixture(p,'p','project_metadata')}
 await refreshResolutionFixture(g);await expect(authenticateResolutionHistory(scope,g.inventory,amk,()=>true)).rejects.toThrow()
 const h=await resolutionFixture();h.evidence.head_before.tip_event_ids=[crypto.randomUUID()];await refreshResolutionFixture(h);await expect(authenticateResolutionHistory(scope,h.inventory,amk,()=>true)).rejects.toThrow()
})
it('JSON size budgeting counts UTF-8, escapes, punctuation and scalar lengths exactly',()=>{
 const values=[null,true,false,{a:[1,'é','\n',false]},['x','y'],{}]
 for(const value of values){const length=new TextEncoder().encode(JSON.stringify(value)).length;expect(()=>boundResolutionJson(value,length)).not.toThrow();expect(()=>boundResolutionJson(value,length-1)).toThrow()}
})
it('unattached inbox10 and a second spurious closure cannot piggyback on a verified Resolution',async()=>{
 const f=await resolutionFixture(),t=structuredClone(f.transition),id=crypto.randomUUID();t.record_id=t.group_id=id;f.inventory.history.push(t)
 await expect(authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).rejects.toThrow()
 const g=await resolutionFixture();g.inventory.history=g.inventory.history.filter((r:any)=>r.record_kind!=='resolution'&&r.record_kind!=='group_transition'&&r.record_kind!=='head')
 await expect(authenticateResolutionHistory(scope,g.inventory,amk,()=>true)).rejects.toThrow()
})
it('protocol2 Legacy source retains its accepted metadata instead of being reclassified as Content',async()=>{
 const f=await resolutionFixture('choose_version',2,false,true)
 expect(f.resolution.result.operation==='upsert'&&Object.keys(f.resolution.result.note.metadata).length>0).toBe(true)
 expect((await authenticateResolutionHistory(scope,f.inventory,amk,()=>true)).resolutions).toBe(1)
})
