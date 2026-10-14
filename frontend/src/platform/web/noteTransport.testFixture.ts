import { metadataSetup, metadataRow, applyMetadata } from './metadataPrefix.testFixture'
import { scope,amk,at,note } from './bootstrap.testFixture'
import { createNoteSyncPlaintext } from '@/cloud/encryptedSyncProtocol'
import { frameContentNote,type ContentNoteEvent } from '@/cloud/contentNoteCodec'
import { readerFrame } from './canonicalReaders.testFixture'
import { encryptObjectBytes } from '@/crypto'
import { encodeBase64Url } from '@/api/base64url'
export async function routeSetup(){const f=await metadataSetup(),m=await metadataRow(f,1);await applyMetadata(f,m);return{...f,m}}
export async function contentRow(f:Awaited<ReturnType<typeof routeSetup>>,seq=2,options:{mutation?:'create'|'update'|'delete';parent?:string;id?:string;eventId?:string;compressed?:boolean;change?:(e:ContentNoteEvent)=>void}={}){
 const mutation=options.mutation??'create',id=options.id??'content-note',revision=mutation==='create'?1:2
 const header={event_id:options.eventId??crypto.randomUUID(),project_id:'p',entity_id:id,entity_type:'note' as const,operation:mutation==='delete'?'delete' as const:'upsert' as const,revision,updated_at:at,deleted_at:mutation==='delete'?at:null}
 const {revision:_rev,...n}=note(id);n.metadata={};n.content='PRIVATE_CONTENT_ROUTE'.repeat(40)
 const {plaintext}=createNoteSyncPlaintext(header,mutation==='create'?null:options.parent??crypto.randomUUID(),mutation==='delete'?{id,project_id:'p',stage_id:null,source_type:'project',source_map_id:null,source_node_id:null,content_format:'html',deleted_at:at}:n)
 const e:ContentNoteEvent={version:1,account_id:scope.canonicalUserId,device_id:'44444444-4444-4444-8444-444444444444',dependencies:{bootstrap_id:f.b.bootstrap_id,metadata_event_id:f.m.event.header.event_id,stage_event_ids:[]},event:plaintext};options.change?.(e)
 const frame=options.compressed?readerFrame({id:8,version:1,event:e},true):frameContentNote(e),o=await encryptObjectBytes(amk,{userId:scope.canonicalUserId,projectId:'p',entityId:id,entityType:'note'},frame)
 const reference={...header,operation:'event',deleted_at:null,device_id:e.device_id,server_sequence:seq},row={record_version:1,account_id:scope.accountId,device_id:scope.deviceId,event_id:header.event_id,server_sequence:seq,protocol_version:3,state:'received',wire_item:JSON.stringify({event:reference,object:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(o.nonce),ciphertext:encodeBase64Url(o.ciphertext)}})}
 f.db.inbox.push(row);f.db.cursors=[{...(f.db.cursors[0] as object),pull_cursor:seq}];frame.fill(0);o.nonce.fill(0);o.ciphertext.fill(0);return{row,e,reference}
}
