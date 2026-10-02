import { invoke } from '@tauri-apps/api/core'
import { encryptedSyncV3Api } from '@/api/encryptedSyncV3'
import { syncApi } from '@/api/sync'
import { encodeBase64Url } from '@/api/base64url'
import { encryptObjectBytes } from '@/crypto'
import { KeyNotProvisionedError } from '@/auth/keyContext'
import { ContentNoteReader } from './contentNoteReader'
import { unframeContentNote } from './contentNoteCodec'
import { canonicalizeSyncTimestamp } from './syncTimestamp'
import type { MetadataScope } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'

export interface ContentNoteMigrationView {
  state: 'content_local'|'candidate_captured'|'publication_pending'|'published_self_echo_pending'|'active'|'conflict'|'blocked'
  activated:boolean
  candidates:Array<{note_id:string;title?:string|null;blocker:string|null;event_id:string|null;publication:string|null;outcome:string|null}>
}
export interface ContentNoteConflict {group_id:string;note_id:string;generation:number;local:unknown;versions:Array<{event_id:string;operation:string;revision:number;note:{title?:string;content?:string;deleted_at?:string}}> }
interface Pending {event_id:string;frame:number[];nonce:number[]|null;ciphertext:number[]|null}
export const NOTE_READER_SUPPORT={reader_transport_version:3,frame_version:1,codec8_version:1,compression_zero:true,ordinary_reader_version:1,resolution_reader_version:2} as const

/** Reader support may be advertised automatically. Source capture remains explicit. */
export class ContentNoteRuntime extends ContentNoteReader {
  async declareSupport(accountId:string,deviceId:string):Promise<void>{
    const {scope,context}=await this.scope(accountId,deviceId)
    await this.auth.authorized(token=>syncApi.registerDevice(token,scope.device_id));this.assertCurrent(context)
    await this.auth.authorized(token=>encryptedSyncV3Api.noteReaderCapabilities(token,scope.device_id,NOTE_READER_SUPPORT));this.assertCurrent(context)
  }
  private async gate(accountId:string,deviceId:string):Promise<{scope:MetadataScope}>{
    await this.requireMode3(accountId,deviceId)
    const {scope,context}=await this.scope(accountId,deviceId)
    const response=await this.auth.authorized(token=>encryptedSyncV3Api.noteReaderGate(token));this.assertCurrent(context)
    if(!response.value.ready)throw new Error('content_note_readers_not_ready')
    return {scope}
  }
  async viewNotes(accountId:string,deviceId:string,projectId:string):Promise<ContentNoteMigrationView>{
    const {scope,context}=await this.scope(accountId,deviceId)
    const view=await invoke<ContentNoteMigrationView>('read_content_note_migration',{scope,projectId});this.assertCurrent(context);return view
  }
  async beginNotes(accountId:string,deviceId:string,projectId:string):Promise<ContentNoteMigrationView>{
    await this.declareSupport(accountId,deviceId)
    const {scope}=await this.gate(accountId,deviceId)
    const {context}=await this.scope(accountId,deviceId)
    const view=await invoke<ContentNoteMigrationView>('begin_content_note_migration',{scope,projectId,now:canonicalizeSyncTimestamp(new Date().toISOString())})
    this.assertCurrent(context);return view
  }
  async conflicts(accountId:string,deviceId:string,projectId:string):Promise<ContentNoteConflict[]>{
    const {scope,context}=await this.scope(accountId,deviceId)
    const result=await invoke<ContentNoteConflict[]>('read_content_note_conflicts',{scope,projectId});this.assertCurrent(context);return result
  }
  async choose(accountId:string,deviceId:string,projectId:string,decision:ContentNoteConflict,selected:string):Promise<void>{
    const {scope}=await this.gate(accountId,deviceId),{context}=await this.scope(accountId,deviceId)
    await invoke('choose_content_note_version',{scope,projectId,decision,selected,now:canonicalizeSyncTimestamp(new Date().toISOString())});this.assertCurrent(context)
  }
  async sealNotes(accountId:string,deviceId:string):Promise<number>{
    const {scope}=await this.gate(accountId,deviceId)
    const {context}=await this.scope(accountId,deviceId)
    const pending=await invoke<Pending[]>('list_pending_content_notes',{scope,sealed:false});this.assertCurrent(context)
    for(const item of pending){
      const bytes=new Uint8Array(item.frame),event=unframeContentNote(bytes),h=event.event.header
      if(event.account_id!==scope.canonical_user_id||event.device_id!==scope.device_id||h.event_id!==item.event_id)throw new Error('content_note_scope_mismatch')
      const lease=this.keys.leaseForAccount(accountId);if(!lease)throw new KeyNotProvisionedError()
      try{await lease.use(async amk=>{
        const sealed=await encryptObjectBytes(amk,{userId:event.account_id,projectId:h.project_id,entityType:'note',entityId:h.entity_id},bytes);this.assertCurrent(context)
        await invoke('seal_content_note',{scope,eventId:item.event_id,frame:item.frame,envelope:{crypto_version:1,aad_version:1,nonce:encodeBase64Url(sealed.nonce),ciphertext:encodeBase64Url(sealed.ciphertext)}})
      })}finally{bytes.fill(0)}
    }
    return pending.length
  }
  async uploadNotes(accountId:string,deviceId:string):Promise<number>{
    const {scope}=await this.gate(accountId,deviceId)
    const {context}=await this.scope(accountId,deviceId)
    const pending=await invoke<Pending[]>('list_pending_content_notes',{scope,sealed:true});this.assertCurrent(context)
    for(const item of pending){
      const bytes=new Uint8Array(item.frame),event=unframeContentNote(bytes),h=event.event.header
      if(!item.nonce||!item.ciphertext||event.device_id!==deviceId||event.account_id!==scope.canonical_user_id)throw new Error('content_note_scope_mismatch')
      try{
        const response=await this.auth.authorized(token=>encryptedSyncV3Api.pushMetadata(token,deviceId,[{event:{event_id:h.event_id,project_id:h.project_id,entity_id:h.entity_id,entity_type:'note',operation:'event',revision:h.revision,updated_at:h.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce:new Uint8Array(item.nonce!),ciphertext:new Uint8Array(item.ciphertext!)}}]));this.assertCurrent(context)
        const receipt=response.value.results[0]!
        await invoke('receipt_content_note',{scope,eventId:h.event_id,serverSequence:receipt.server_sequence,duplicate:receipt.duplicate})
      }finally{bytes.fill(0)}
    }
    return pending.length
  }
}
