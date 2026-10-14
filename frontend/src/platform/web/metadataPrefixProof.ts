import type { AccountMasterKey } from '@/crypto'
import { decodeBase64Url } from '@/api/base64url'
import { immutableWireIdentity, validateBrowserInboxRecord, type BrowserSyncScope } from './syncDurability'
import { validateBrowserMetadataHead } from './metadataApplyRecords'
import { validateBrowserProjectBinding } from './projectBindings'
import { metadataProofFor } from './importedMetadataApply'
import { openBrowserCanonicalObject } from './canonicalReaders'
import type { ProjectMetadataEvent } from '@/cloud/projectMetadataCodec'
import type { BrowserPrefixInventory } from './provenPrefixRecords'
import { BrowserPersistenceError } from './persistence'
export interface VerifiedMetadataPrefix { readonly verifiedMetadataPrefix: unique symbol }
const plans = new WeakMap<object, { scope: string; anchors: string; sequences: Set<number>; current: () => boolean }>()
const same = (a: unknown, b: unknown) => immutableWireIdentity(a) === immutableWireIdentity(b)
const anchors = (v: BrowserPrefixInventory) => immutableWireIdentity({ rows: v.rows.filter(r=>JSON.parse((r as {wire_item:string}).wire_item).event.entity_type==='project_metadata'), owners:v.owners, bindings:v.bindings, out:v.out, receipts:v.receipts })
export function verifiedMetadataSequences(token: VerifiedMetadataPrefix | undefined, scope: BrowserSyncScope, v: BrowserPrefixInventory): ReadonlySet<number> {
  if (!token) return new Set()
  const p=plans.get(token)
  if(!p||!p.current()||p.scope!==immutableWireIdentity(scope)||p.anchors!==anchors(v))throw new BrowserPersistenceError('stale_authority')
  return new Set(p.sequences)
}
/** Crypto outside transactions. Certificate contains exact non-secret anchors, never plaintext/key. */
export async function prepareMetadataPrefix(scope:BrowserSyncScope,v:BrowserPrefixInventory,amk:AccountMasterKey,current:()=>boolean,force=false):Promise<VerifiedMetadataPrefix>{
 const rows=v.rows.map(r=>validateBrowserInboxRecord(r,scope)),bindings=v.bindings.map(b=>validateBrowserProjectBinding(b,scope)),sequences=new Set<number>()
 for(const rawHead of v.owners){
  if(['stage','stage_order'].includes((rawHead as {owner_kind:string}).owner_kind))continue
  const head=validateBrowserMetadataHead(rawHead,scope),binding=bindings.find(b=>b.project_id===head.owner_id)
  if(!binding||binding.mode!=='import_remote'||binding.phase!=='captured'||binding.remote_state!=='active'||binding.bootstrap_id!==head.bootstrap_id)continue
  if(v.out.some(r=>JSON.parse((r as {raw_body:string}).raw_body).items.some((i:{event:{entity_type:string;project_id:string}})=>i.event.entity_type==='project_metadata'&&i.event.project_id===head.owner_id)))continue
  const ordered=[...head.history].sort((a,b)=>a.server_sequence-b.server_sequence)
  // Successful bounded apply produces one ordinary clean chain, never a preserved conflict/resolution.
  if(ordered.some((p,i)=>p.source_device_id===scope.deviceId||!['create','update','delete'].includes(p.operation)||i===0&&(p.operation!=='create'||p.revision!==1||p.generation!==1||p.parent_event_ids.length!==0)||i>0&&(!same(p.parent_event_ids,[ordered[i-1]!.event_id])||p.revision!==ordered[i-1]!.revision+1||p.generation<=ordered[i-1]!.generation||p.server_sequence<=ordered[i-1]!.server_sequence))||!same(head.tip_event_ids,[ordered.at(-1)!.event_id]))continue
  const decrypt=force||ordered.some(p=>p.server_sequence>v.cursor.proven_prefix)
  let valid=true
  for(const proof of ordered){
   const row=rows.find(r=>r.event_id===proof.event_id)
   if(!row||row.state!=='applied'||!same(row.applied_proof,proof)||row.server_sequence!==proof.server_sequence){valid=false;break}
   const wire=JSON.parse(row.wire_item)
   let nonce:Uint8Array|undefined,ciphertext:Uint8Array|undefined,identity:Uint8Array<ArrayBuffer>|undefined,digest:Uint8Array|undefined
   try{
    identity=new TextEncoder().encode(immutableWireIdentity({protocol_version:row.protocol_version,event:wire.event,object:wire.object}));digest=new Uint8Array(await crypto.subtle.digest('SHA-256',identity))
    const hash=Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('')
    if(hash!==proof.wire_digest)throw new TypeError('metadata_wire_digest')
    if(decrypt){
     nonce=decodeBase64Url(wire.object.nonce);ciphertext=decodeBase64Url(wire.object.ciphertext)
     const event=await openBrowserCanonicalObject(amk,{accountId:scope.canonicalUserId,projectId:head.owner_id,entityId:head.owner_id,entityType:'project_metadata',eventId:proof.event_id},{...wire.object,nonce,ciphertext}) as ProjectMetadataEvent
     const reproduced=metadataProofFor(scope,wire.event,event,hash,row.protocol_version)
     if(!same(reproduced,proof))throw new TypeError('metadata_proof_mismatch')
    }
   }catch{valid=false;break}finally{nonce?.fill(0);ciphertext?.fill(0);identity?.fill(0);digest?.fill(0)}
  }
  if(!current())throw new BrowserPersistenceError('closed')
  if(valid)ordered.forEach(p=>sequences.add(p.server_sequence))
 }
 if(!current())throw new BrowserPersistenceError('closed')
 const token=Object.freeze({}) as VerifiedMetadataPrefix
 plans.set(token,{scope:immutableWireIdentity(scope),anchors:anchors(v),sequences,current});return token
}
