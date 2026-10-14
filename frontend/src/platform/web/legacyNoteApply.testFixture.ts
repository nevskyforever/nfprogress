// @vitest-environment node
import { fixture,scope,amk,note,at } from './bootstrap.testFixture'
import { createNoteSyncPlaintext } from '@/cloud/encryptedSyncProtocol'
import { encodeNoteSyncPlaintext } from '@/cloud/noteSyncCodec'
import { encryptObjectBytes } from '@/crypto'
import { encodeBase64Url } from '@/api/base64url'
const peer='55555555-5555-4555-8555-555555555555'
export async function received(f:Awaited<ReturnType<typeof fixture>>,seq:number,revision=1,parent:string|null=null,operation='upsert',change?:(v:any)=>void,id='remote-note'){
 const event={event_id:crypto.randomUUID(),project_id:'p',entity_id:id,entity_type:'note',operation,revision,updated_at:at,deleted_at:operation==='delete'?at:null}
 const {revision:_local,...n}=note(id);const {plaintext}=createNoteSyncPlaintext(event as never,parent,operation==='delete'?{id:n.id,project_id:'p',stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:at}:n);change?.(plaintext)
 const bytes=encodeNoteSyncPlaintext(plaintext);const object=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:'note'},bytes);bytes.fill(0)
 const row={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,event_id:event.event_id,server_sequence:seq,protocol_version:3,state:'received',wire_item:JSON.stringify({event:{...event,device_id:peer,server_sequence:seq},object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(object.nonce),ciphertext:encodeBase64Url(object.ciphertext)}})};object.nonce.fill(0);object.ciphertext.fill(0);f.db.inbox.push(row)
 f.db.cursors=[{record_version:1,account_id:scope.accountId,device_id:scope.deviceId,pull_cursor:seq,ack_cursor:(f.db.cursors[0] as any)?.ack_cursor??0,proven_prefix:(f.db.cursors[0] as any)?.proven_prefix??0,next_local_ordinal:(f.db.cursors[0] as any)?.next_local_ordinal??1}];return row
}
export async function imported(){const f=await fixture([]);f.db.projectBindings=[];const b=await f.projects.importRemote(scope,{project_id:'p',bootstrap_id:crypto.randomUUID(),remote_state:'active',remote_high_water:0});return{...f,b}}
