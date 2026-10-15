// @vitest-environment node
import {describe,it,expect} from 'vitest'
import {scope,amk,at,note,project} from './bootstrap.testFixture'
import {contentStageSetup,stageContent} from './contentStage.testFixture'
import {routeSetup,contentRow} from './noteTransport.testFixture'
import {BrowserContentNoteApplyRuntime} from './contentNoteApply'
import {validateLocalNote,validateContentLocalNote,validatePersistedLocalNote} from './localAuthorityRecords'
import {noteSyncEligibility} from '@/cloud/noteSyncCodec'
import {received} from './legacyNoteApply.testFixture'
import {openHistoryCandidate,candidateDigest} from './noteHistory'
import {noteProofDigest} from './legacyNoteApply'
import {verifyStoredContentNoteProof} from './contentNoteProof'
import {prepareNotePrerequisite,prepareNoteTransportCommit} from './noteTransportPrerequisite'
import {validateNoteHistorySet} from './noteHistoryRecords'
import {encryptObjectBytes,decryptObjectBytes} from '@/crypto'
import {decodeBase64Url,encodeBase64Url} from '@/api/base64url'
import {canonical} from '@/cloud/projectMetadataCodec'
const text='  PRIVATE_PLAIN <b>literal & text</b>\r\n\n\tРусский 😀\u0000  '
const source=(stage:string|null=null)=>({state:'live' as const,note:{...note('content-note'),stage_id:stage,content_format:'plain' as const,metadata:{},content:text}})
it.each([null,'s'])('Content-only plain source stage=%s is validated exactly; Legacy remains ineligible',stage=>{const n=source(stage);expect(validateContentLocalNote(n,'p')).toEqual(n);expect(validatePersistedLocalNote(n,'p')).toEqual(n);expect(()=>validateLocalNote(n,'p')).toThrow();expect(noteSyncEligibility({note:n.note} as never).eligible).toBe(false)})
it.each(['mindmap','map','node','future','metadata','limit','extra'] as const)('plain %s cannot exploit persisted-route selection',kind=>{const n=source() as any;if(kind==='mindmap')n.note.source_type='mindmap';if(kind==='map')n.note.source_map_id='map';if(kind==='node')n.note.source_node_id='node';if(kind==='future')n.note.content_format='markdown';if(kind==='metadata')n.note.metadata={foreign:true};if(kind==='limit')n.note.content='x'.repeat(300001);if(kind==='extra')n.note.future=true;expect(()=>validatePersistedLocalNote(n,'p')).toThrow();expect(()=>validateContentLocalNote(n,'p')).toThrow()})
for(const stage of [false,true])describe(stage?'Stage plain':'project plain',()=>{
 const setup=async()=>{if(stage)return contentStageSetup();const f=await routeSetup();return {...f,content:new BrowserContentNoteApplyRuntime(f.notes)}}
 const incoming=async(f:Awaited<ReturnType<typeof setup>>,seq:number,options:Parameters<typeof contentRow>[2]={})=>{
  const change=options.change,opts={...options,change:(e:Parameters<NonNullable<typeof change>>[0])=>{(e.event as any).note.content_format='plain';if(e.event.version===1&&'content' in e.event.note)e.event.note.content=text;change?.(e)}}
  return stage?stageContent(f as Awaited<ReturnType<typeof contentStageSetup>>,seq,opts):contentRow(f as Awaited<ReturnType<typeof routeSetup>>,seq,opts)
 }
 const start=stage?3:2
 const read=async(f:Awaited<ReturnType<typeof setup>>)=>f.local.withDecryptedSnapshot(scope,(await f.local.readSnapshot(scope,'p')).token,async v=>v.notes.find(n=>n.note.id==='content-note')!)
 const candidate=(f:Awaited<ReturnType<typeof setup>>)=>f.db.legacyNoteHistory!.find((r:any)=>r.record_kind==='candidate') as any
 it.each([false,true])('ID1=%s exact plain live+update+tombstone+replay, format1 and proof reopen',async compressed=>{
  const f=await setup(),root=await incoming(f,start,{compressed});await f.content.apply(scope,start)
  expect(await read(f)).toMatchObject({state:'live',note:{content:text,content_format:'plain',stage_id:stage?'s':null}})
  const c=candidate(f);expect(c).toMatchObject({record_version:2,transport_kind:'content_note_v1'});expect(c.wire_item).toBe(root.row.wire_item)
  const {envelope}=c.projection,n=decodeBase64Url(envelope.nonce),cipher=decodeBase64Url(envelope.ciphertext);let b:Uint8Array|undefined
  try{b=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},{...envelope,nonce:n,ciphertext:cipher});expect(JSON.parse(new TextDecoder().decode(b))).toMatchObject({local_format:1,source:{note:{content_format:'plain',content:text}}})}finally{n.fill(0);cipher.fill(0);b?.fill(0)}
  const child=await incoming(f,start+1,{compressed,mutation:'update',parent:root.row.event_id});await f.content.apply(scope,start+1);expect((await read(f)).note).toMatchObject({content:text,content_format:'plain'})
  await incoming(f,start+2,{compressed,mutation:'delete',revision:3,parent:child.row.event_id});await f.content.apply(scope,start+2)
  expect(await read(f)).toMatchObject({state:'tombstone',note:{content_format:'plain',stage_id:stage?'s':null,source_type:'project',source_map_id:null,source_node_id:null,deleted_at:at}})
  const old=structuredClone(f.db);for(let seq=start;seq<=start+2;seq++){expect(await f.content.apply(scope,seq)).toBe('already_applied');expect(f.db.inbox[seq-1]).toMatchObject({record_version:7,state:'content_note_proven'});await verifyStoredContentNoteProof(scope,amk,f.db.inbox[seq-1] as never,validateNoteHistorySet(scope,f.db.legacyNoteHistory!))}
  expect(f.db).toEqual(old);expect((await f.proven.advance(scope)).candidate_proven_prefix).toBe(start+2);expect(JSON.stringify(f.db)).not.toContain('PRIVATE_PLAIN')
 })
 it.each(['initialize','create','update','delete','writer','capture'] as const)('Legacy %s cannot produce or mutate plain',async kind=>{
  const f=await setup();await incoming(f,start);await f.content.apply(scope,start);const snapshot=await f.local.readSnapshot(scope,'p')
  if(kind==='capture'){f.db.projectBindings=[];const b=await f.projects.prepare(scope,{project_id:'p',mode:'upload_existing'}),reg=await f.projects.confirmRegistration(scope,b,{remote_state:'initializing',remote_high_water:0}),old=structuredClone(f.db);await expect(f.capture.capture(scope,reg)).rejects.toThrow();expect(f.db).toEqual(old);return}
  const old=structuredClone(f.db),run=kind==='initialize'?()=>f.local.initializeProject(scope,{project:project('other'),notes:[{state:'live',note:{...source().note,project_id:'other'}}]}):kind==='create'?()=>f.local.createNote(scope,snapshot.token,{...source().note,id:'other-note'}):kind==='delete'?()=>f.local.tombstoneNote(scope,snapshot.token,'content-note',at):kind==='writer'?async()=>f.writer.local.updateNote(scope,(await f.writer.local.readSnapshot(scope,'p')).token,'content-note',{content:'forbidden'},at):()=>f.local.updateNote(scope,snapshot.token,'content-note',{content:'forbidden'},at)
  await expect(Promise.resolve().then(run)).rejects.toThrow();expect(f.db).toEqual(old)
 })
 it('Legacy encrypted plain wire stays unsupported',async()=>{const f=await setup();await received(f,start,1,null,'upsert',p=>{p.note.content_format='plain';p.note.metadata={}});const old=structuredClone(f.db);await expect(f.notes.apply(scope,start)).rejects.toThrow();expect(f.db).toEqual(old)})
 it('Legacy HTML child cannot strip a Content-only plain route',async()=>{const f=await setup(),root=await incoming(f,start);await f.content.apply(scope,start);await received(f,start+1,2,root.row.event_id,'upsert',p=>{p.note.metadata={}},'content-note');const old=structuredClone(f.db);await expect(f.notes.apply(scope,start+1)).rejects.toMatchObject({code:'unsupported_local_source'});expect(f.db).toEqual(old)})
 it.each(['html','plain'] as const)('%s parent cannot switch format, including after delete',async initial=>{
  const f=await setup(),root=await incoming(f,start,{change:e=>{(e.event as any).note.content_format=initial}});await f.content.apply(scope,start)
  await incoming(f,start+1,{mutation:'update',parent:root.row.event_id,change:e=>{(e.event as any).note.content_format=initial==='html'?'plain':'html'}});const old=structuredClone(f.db);await expect(f.content.apply(scope,start+1)).rejects.toMatchObject({code:'unsupported_local_source'});expect(f.db).toEqual(old)
  f.db.inbox.pop();const tomb=await incoming(f,start+1,{mutation:'delete',parent:root.row.event_id,change:e=>{(e.event as any).note.content_format=initial}});await f.content.apply(scope,start+1)
  await incoming(f,start+2,{mutation:'update',revision:3,parent:tomb.row.event_id,change:e=>{(e.event as any).note.content_format=initial==='html'?'plain':'html'}});const old2=structuredClone(f.db);await expect(f.content.apply(scope,start+2)).rejects.toThrow();expect(f.db).toEqual(old2)
 })
 it.each(['plain','html'] as const)('changed %s projection format with recomputed public digest fails original-wire proof',async initial=>{
  const f=await setup();await incoming(f,start,{change:e=>{(e.event as any).note.content_format=initial}});await f.content.apply(scope,start);const c=candidate(f),env=c.projection.envelope,n=decodeBase64Url(env.nonce),cipher=decodeBase64Url(env.ciphertext);let bytes:Uint8Array|undefined
  try{bytes=await decryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},{...env,nonce:n,ciphertext:cipher});const p=JSON.parse(new TextDecoder().decode(bytes));p.source.note.content_format=initial==='html'?'plain':'html';const raw=new TextEncoder().encode(canonical(p));try{const enc=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'content-note',entityType:'note'},raw);c.projection.envelope={...env,nonce:encodeBase64Url(enc.nonce),ciphertext:encodeBase64Url(enc.ciphertext)};enc.nonce.fill(0);enc.ciphertext.fill(0)}finally{raw.fill(0)}}finally{n.fill(0);cipher.fill(0);bytes?.fill(0)}
  c.projection_digest=await noteProofDigest(c.projection);c.record_digest=await candidateDigest(c);await expect(openHistoryCandidate(scope,c,amk)).rejects.toThrow();await expect(f.proven.advance(scope)).rejects.toThrow()
 })
 it.each(['html','plain'] as const)('logical %s format cannot change after authenticated prerequisite',async initial=>{const f=await setup(),row=await incoming(f,start,{change:e=>{(e.event as any).note.content_format=initial}}),binding=f.db.projectBindings[0] as any,p=await prepareNotePrerequisite(scope,row.row as never,binding,amk,()=>true,f.transaction);await f.content.apply(scope,start);const changed=structuredClone(p.plaintext);changed.note.content_format=initial==='html'?'plain':'html';await expect(prepareNoteTransportCommit(p.certificate,changed,candidate(f).projection)).rejects.toThrow()})
 it('unsupported plain source caps prefix before later safe Legacy',async()=>{const f=await setup();await incoming(f,start,{frameChange:frame=>{const raw=new TextDecoder().decode(frame.subarray(20));frame.set(new TextEncoder().encode(raw.replace('"source_type":"project"','"source_type":"mindmap"')),20)}});const old=structuredClone(f.db);await expect(f.content.apply(scope,start)).rejects.toThrow();expect(f.db).toEqual(old);await received(f,start+1);await f.notes.apply(scope,start+1);expect((await f.proven.advance(scope)).candidate_proven_prefix).toBe(start-1)})
 it('tampered durable AEAD payload fails reopen instead of gaining admission',async()=>{const f=await setup();await incoming(f,start);await f.content.apply(scope,start);const row=f.db.localNotes![0] as any;row.envelope.ciphertext=(row.envelope.ciphertext[0]==='A'?'B':'A')+row.envelope.ciphertext.slice(1);await expect(f.local.readSnapshot(scope,'p')).rejects.toMatchObject({code:'corrupt_record'})})
})
