import { encodeV2Push, encryptedSyncV2Api, parseV2Capabilities, parseV2PushResponse, validateV2PushItem, type V2PushRequest, type V2ResolutionPushItem } from '@/api/encryptedSyncV2'
import { ApiError } from '@/api/client'
import { MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES, MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES } from '@/api/encryptedSync'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { NoteSyncResolutionUploadRepository, ResolutionUploadItem } from '@/infrastructure/sqlite/noteSyncResolutionUploadRepository'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'

const LIMIT=100
export class NoteSyncResolutionUploadError extends Error { constructor(readonly code:'mode_incompatible'|'malformed_receipt'|'wire_limit',message:string){super(message)} }
function identical(a:ResolutionUploadItem,b:ResolutionUploadItem){return a.event_id===b.event_id&&a.account_id===b.account_id&&a.device_id===b.device_id&&a.project_id===b.project_id&&a.entity_id===b.entity_id&&a.entity_type===b.entity_type&&a.operation===b.operation&&a.revision===b.revision&&a.updated_at===b.updated_at&&a.envelope.crypto_version===b.envelope.crypto_version&&a.envelope.aad_version===b.envelope.aad_version&&a.envelope.nonce===b.envelope.nonce&&a.envelope.ciphertext===b.envelope.ciphertext}
function wireItem(x:ResolutionUploadItem):V2ResolutionPushItem{return {event:{event_id:x.event_id,project_id:x.project_id,entity_id:x.entity_id,entity_type:'note',operation:'resolution',revision:x.revision,updated_at:x.updated_at,deleted_at:null},object:x.envelope}}
function request(device:string,items:readonly ResolutionUploadItem[]):V2PushRequest{return {protocol_version:2,encrypted_sync_version:2,device_id:device,items:items.map(wireItem)}}
function bounded(device:string,items:readonly ResolutionUploadItem[]):ResolutionUploadItem[]{
 const selected:ResolutionUploadItem[]=[]; const eventIds=new Set<string>(); const encoder=new TextEncoder(); const prefix=`{"protocol_version":2,"encrypted_sync_version":2,"device_id":${JSON.stringify(device)},"items":[`; const fixedBytes=encoder.encode(`${prefix}]}`).byteLength; let ciphertextBytes=0; let itemBytes=0
 for(const item of items.slice(0,LIMIT)){
  const wire=wireItem(item); const validated=validateV2PushItem(wire); if(eventIds.has(validated.eventId))throw new TypeError('Duplicate resolution upload event.'); const bytes=encoder.encode(JSON.stringify(wire)).byteLength; const aggregate=ciphertextBytes+validated.ciphertextBytes; const body=fixedBytes+itemBytes+bytes+(selected.length?1:0)
  if(aggregate>MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES||body>MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES){if(!selected.length)throw new RangeError('Resolution upload exceeds encrypted transport limits.');break}
  eventIds.add(validated.eventId); ciphertextBytes=aggregate; itemBytes+=bytes+(selected.length?1:0)
  selected.push(item)
 }
 return selected
}
export class NoteSyncResolutionUploader {
 private static flights=new Map<string,Promise<{uploaded:number,deviceId:string|null}>>()
 constructor(private auth:NormalUserAuthRuntime,private bindings:AuthoritativeAccountBinding,private identity:CloudIdentityRepository,private repository:NoteSyncResolutionUploadRepository,private api=encryptedSyncV2Api){}
 async uploadOnce(account:string):Promise<{uploaded:number,deviceId:string|null}>{
  const bound=await this.bindings.ensureForCurrentUser(account); const identity=await this.identity.read(bound.context.userId); if(!identity||identity.local_account_id!==account||!this.auth.isCurrent(bound.context))throw new StaleAuthContextError(); const capabilities=await this.auth.authorized(token=>this.api.capabilities(token)); if(capabilities.context.userId!==bound.context.userId||!this.auth.isCurrent(bound.context))throw new StaleAuthContextError(); const capability=parseV2Capabilities(capabilities.value); if(capability.supported_transport_version!==2||capability.writer_transport_version!==2)return {uploaded:0,deviceId:null}
  const initial=await this.repository.list({account_id:account,device_id:identity.device_id,canonical_user_id:bound.context.userId,limit:LIMIT}); if(!initial.length)return {uploaded:0,deviceId:null}; if(initial.some(x=>x.account_id!==account||x.device_id!==identity.device_id))throw new TypeError('Invalid resolution upload scope.'); const batch=bounded(identity.device_id,initial); const key=`${account}\0${bound.context.userId}\0${identity.device_id}\0${bound.context.authEpoch}`; const existing=NoteSyncResolutionUploader.flights.get(key);if(existing)return existing
  const flight=this.run(account,bound.context,identity.device_id,batch);NoteSyncResolutionUploader.flights.set(key,flight);try{return await flight}finally{if(NoteSyncResolutionUploader.flights.get(key)===flight)NoteSyncResolutionUploader.flights.delete(key)}
 }
 private async run(account:string,context:AuthContextSnapshot,device:string,batch:ResolutionUploadItem[]){
  const fresh=await this.repository.list({account_id:account,device_id:device,canonical_user_id:context.userId,limit:batch.length}); if(!this.auth.isCurrent(context)||fresh.length!==batch.length||batch.some((item,index)=>!identical(item,fresh[index]!)))throw new StaleAuthContextError()
  try { const wire=request(device,batch); encodeV2Push(wire); const pushed=await this.auth.authorized(token=>this.api.push(token,wire)); if(pushed.context.userId!==context.userId||!this.auth.isCurrent(context))throw new StaleAuthContextError(); const response=parseV2PushResponse(pushed.value,batch.map(item=>item.event_id)); const accepted=await this.repository.commit({account_id:account,device_id:device,canonical_user_id:context.userId,receipts:response.results}); if(!Array.isArray(accepted)||accepted.length!==batch.length||accepted.some(value=>value!=='accepted'&&value!=='already_accepted'))throw new TypeError('Invalid resolution acceptance result.'); return {uploaded:batch.length,deviceId:device} } catch(error){if(error instanceof ApiError&&error.code==='sync_transport_mode_incompatible')throw new NoteSyncResolutionUploadError('mode_incompatible','Server transport mode changed.');throw error}
 }
}
