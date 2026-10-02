import { StaleAuthContextError, type NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { RuntimeKeyContext } from '@/auth/keyContext'
import { invoke } from '@tauri-apps/api/core'
import { decodeBase64Url } from '@/api/base64url'
import { decryptObjectBytes, type ObjectCryptoEnvelope } from '@/crypto'
import { diagnostics } from '@/diagnostics/service'
import { ProjectMetadataMigrationRuntime } from './projectMetadataMigrationRuntime'
import { unframeContentNote, ContentNoteError } from './contentNoteCodec'
import type { VerifiedNoteSyncRemoteApplyCommand } from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import type { MetadataScope } from '@/infrastructure/sqlite/projectMetadataMigrationRepository'

export interface ContentNoteInboxItem {
  event_id:string; server_sequence:number; source_device_id:string; project_id:string; entity_id:string
  entity_type:'note'; operation:'event'; revision:number; updated_at:string; deleted_at:null
  envelope:{crypto_version:1;aad_version:1;nonce:string;ciphertext:string}
}
export interface ContentNoteReaderRepository {
  received(scope:MetadataScope,limit:number,after:number):Promise<ContentNoteInboxItem[]>
  apply(command:VerifiedNoteSyncRemoteApplyCommand):Promise<string>
  block(command:VerifiedNoteSyncRemoteApplyCommand,code:string):Promise<void>
}
const native:ContentNoteReaderRepository={
  received:(s,limit,after)=>invoke('list_received_note_sync_inbox_page',{command:{account_id:s.account_id,canonical_user_id:s.canonical_user_id,device_id:s.device_id,kind:'content',limit,after_server_sequence:after}}),
  apply:command=>invoke('apply_verified_received_content_note',{command}),
  block:(command,code)=>invoke('record_content_note_blocker',{command,code}),
}
/** Reader only: no scan/capture/seal/upload and no new-format writer. */
export class ContentNoteReader extends ProjectMetadataMigrationRuntime {
  private retryPage:{scope:string;after:number}|undefined
  constructor(auth:NormalUserAuthRuntime,bindings:AuthoritativeAccountBinding,identity:CloudIdentityRepository,keys:RuntimeKeyContext,
    private readonly repository:ContentNoteReaderRepository=native) {super(auth,bindings,identity,keys)}
  async readOnce(accountId:string,deviceId:string,limit=8,maxPasses=4):Promise<{blocked:string[];hasRemainingWork:boolean;listed:number}> {
    if (!Number.isSafeInteger(limit)||limit<1||limit>32||!Number.isSafeInteger(maxPasses)||maxPasses<1||maxPasses>8) throw new RangeError('invalid_content_reader_limits')
    const {scope,context}=await this.scope(accountId,deviceId)
    const retryScope=JSON.stringify([accountId,deviceId,context.userId,context.authEpoch])
    let after=this.retryPage?.scope===retryScope?this.retryPage.after:0,listed=0,remaining=false
    const blocked:string[]=[]
    for(let pass=0;pass<maxPasses;pass++) {
      const rows=await this.repository.received(scope,limit,after);this.assertCurrent(context)
      for(const row of rows) {
        if(row.entity_type!=='note'||row.operation!=='event'||row.deleted_at!==null||row.server_sequence<=after) throw new TypeError('content_note_scope_mismatch')
        after=row.server_sequence;listed++
        const envelope:ObjectCryptoEnvelope={crypto_version:row.envelope.crypto_version,aad_version:row.envelope.aad_version,
          nonce:decodeBase64Url(row.envelope.nonce,{expectedLength:24}),ciphertext:decodeBase64Url(row.envelope.ciphertext)}
        const lease=this.keys.leaseForAccount(accountId);if(!lease || !lease.isCurrent() || lease.canonicalUserId!==context.userId || lease.authEpoch!==context.authEpoch) throw new StaleAuthContextError()
        let frame:Uint8Array|undefined
        try {
          await lease.use(async amk=>{
            frame=await decryptObjectBytes(amk,{userId:context.userId,projectId:row.project_id,entityId:row.entity_id,entityType:'note'},envelope)
            this.assertCurrent(context)
            if (!lease.isCurrent()) throw new StaleAuthContextError()
            // Validate independently in TS, then let native durably classify an
            // unsupported authenticated frame without speculative fallback.
            try {unframeContentNote(frame)} catch(error) {if(!(error instanceof ContentNoteError)) throw error}
            diagnostics.record('sync','sync_cycle','started',undefined,{count:1})
            const plaintext=Array.from(frame),nonce=Array.from(envelope.nonce),ciphertext=Array.from(envelope.ciphertext)
            try {
              const status=await this.repository.apply({account_id:accountId,canonical_user_id:context.userId,pulling_device_id:deviceId,
                event_id:row.event_id,server_sequence:row.server_sequence,source_device_id:row.source_device_id,crypto_version:1,aad_version:1,nonce,ciphertext,plaintext})
              this.assertCurrent(context)
              if(!['applied','already_applied'].includes(status)) blocked.push(status)
              diagnostics.record('sync','sync_cycle','apply_result',undefined,{status})
            } finally {plaintext.fill(0);nonce.fill(0);ciphertext.fill(0)}
          })
        } catch(error) {
          if(error instanceof StaleAuthContextError) throw error
          this.assertCurrent(context)
          const code=frame ? 'invalid_note_payload' : 'decrypt_failed'
          await this.repository.block({account_id:accountId,canonical_user_id:context.userId,pulling_device_id:deviceId,event_id:row.event_id,
            server_sequence:row.server_sequence,source_device_id:row.source_device_id,crypto_version:1,aad_version:1,
            nonce:Array.from(envelope.nonce),ciphertext:Array.from(envelope.ciphertext),plaintext:[]},code)
          blocked.push(code);diagnostics.record('sync','sync_cycle','blocker',undefined,{error_code:code})
        } finally {frame?.fill(0);envelope.nonce.fill(0);envelope.ciphertext.fill(0)}
      }
      remaining=rows.length===limit;if(!remaining)break
    }
    this.retryPage={scope:retryScope,after:remaining?after:0}
    return {blocked:[...new Set(blocked)],hasRemainingWork:remaining||blocked.length>0,listed}
  }
}
