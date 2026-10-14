import { imported, received } from './legacyNoteApply.testFixture'
import { scope, amk, at } from './bootstrap.testFixture'
import { BrowserImportedMetadataApply } from './importedMetadataApply'
import { frameProjectMetadata, type ProjectMetadataEvent } from '@/cloud/projectMetadataCodec'
import { compressCanonicalFrame } from '@/cloud/frameCompression'
import { encryptObjectBytes } from '@/crypto'
import { encodeBase64Url } from '@/api/base64url'
export { scope }
export async function metadataSetup() {const f=await imported();return{...f,metadata:new BrowserImportedMetadataApply(f.transaction,f.sync)}}
export async function metadataRow(f:Awaited<ReturnType<typeof metadataSetup>>,seq:number,options:{compressed?:boolean;revision?:number;parent?:string;self?:boolean;change?:(e:ProjectMetadataEvent)=>void}={}){
 const revision=options.revision??1,b=f.db.projectBindings[0] as any
 const event:ProjectMetadataEvent={version:options.compressed?2:1,header:{account_id:scope.canonicalUserId,bootstrap_id:b.bootstrap_id,device_id:options.self?scope.deviceId:'44444444-4444-4444-8444-444444444444',project_id:'p',entity_id:'p',event_id:crypto.randomUUID(),operation:revision===1?'create':'update',revision,generation:revision,parent_event_ids:options.parent?[options.parent]:[],updated_at:at},metadata:{name:'PRIVATE_METADATA'.repeat(30),goal:null,infinite:true,unit:'symbols',deadline:null,status:'active',personal_goal:1,auto_freeze:false,streak_enabled:false,work_method:'manual',stages_enabled:false,combine_stage_mindmaps:false},deleted_at:null}
 if(event.version===2)event.metadata!.cover_reference=null;options.change?.(event)
 const original=frameProjectMetadata(event),frame=options.compressed?compressCanonicalFrame(original):original,o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:'p',entityType:'project_metadata'},frame)
 if(options.compressed&&frame[11]!==1)throw Error('expected_ID1_fixture')
 const reference={event_id:event.header.event_id,device_id:event.header.device_id,server_sequence:seq,project_id:'p',entity_id:'p',entity_type:'project_metadata' as const,operation:event.header.operation==='delete'?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:event.deleted_at}
 const row={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,event_id:reference.event_id,server_sequence:seq,protocol_version:3,state:'received',wire_item:JSON.stringify({event:reference,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}})}
 original.fill(0);if(frame!==original)frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0)
 f.db.inbox.push(row);f.db.cursors=[{record_version:1,account_id:scope.accountId,device_id:scope.deviceId,pull_cursor:seq,ack_cursor:(f.db.cursors[0] as any)?.ack_cursor??0,proven_prefix:(f.db.cursors[0] as any)?.proven_prefix??0,next_local_ordinal:1}]
 return{event,reference,row}
}
export const applyMetadata=(f:Awaited<ReturnType<typeof metadataSetup>>,m:Awaited<ReturnType<typeof metadataRow>>)=>f.metadata.apply(scope,m.reference,f.auth,f.bindings as never,f.keys as never)
export async function metadataBetweenNotes(compressed=false,apply=true){const f=await metadataSetup();await received(f,1,1,null,'upsert',undefined,'a');await f.notes.apply(scope,1);const m=await metadataRow(f,2,{compressed});if(apply)await applyMetadata(f,m);await received(f,3,1,null,'upsert',undefined,'b');await f.notes.apply(scope,3);return{...f,m}}
