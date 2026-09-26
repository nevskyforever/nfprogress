import { invoke } from '@tauri-apps/api/core'
export interface ResolutionUploadItem { event_id:string,account_id:string,device_id:string,project_id:string,entity_id:string,entity_type:'note',operation:'resolution',revision:number,updated_at:string,envelope:{crypto_version:1,aad_version:1,nonce:string,ciphertext:string} }
export interface ResolutionUploadReceipt { event_id:string,server_sequence:number,duplicate:boolean }
export interface NoteSyncResolutionUploadRepository { list(command:{account_id:string,device_id:string,canonical_user_id:string,limit:number}):Promise<ResolutionUploadItem[]>; commit(command:{account_id:string,device_id:string,canonical_user_id:string,receipts:ResolutionUploadReceipt[]}):Promise<Array<'accepted'|'already_accepted'>> }
export class SQLiteNoteSyncResolutionUploadRepository implements NoteSyncResolutionUploadRepository {
  list(command:{account_id:string,device_id:string,canonical_user_id:string,limit:number}) { return invoke<ResolutionUploadItem[]>('list_sealed_note_resolution_uploads',{command}) }
  commit(command:{account_id:string,device_id:string,canonical_user_id:string,receipts:ResolutionUploadReceipt[]}) { return invoke<Array<'accepted'|'already_accepted'>>('commit_note_resolution_upload_acceptance',{command}) }
}
