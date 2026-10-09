import { compressionBlocker } from './frameCompression'
import {invoke} from '@tauri-apps/api/core'
import {encryptedSyncV3Api} from '@/api/encryptedSyncV3'
import {encryptObjectBytes,decryptObjectBytes} from '@/crypto'
import {encryptAccountObject,decryptAccountObject} from '@/crypto/accountObjectCrypto'
import {KeyNotProvisionedError} from '@/auth/keyContext'
import {StaleAuthContextError} from '@/auth/userAuth'
import type {MetadataScope} from '@/infrastructure/sqlite/projectMetadataMigrationRepository'
import {ProgressSyncRuntime} from './progressSyncRuntime'
import {unframeGameEvent,type GameEvent} from './gameCodec'
import {canonicalizeSyncTimestamp} from './syncTimestamp'

export interface GameOwnerView {owner_key:string;state:string;blocker:string|null;blockers:string[];tips:string[];versions:Array<{event_id:string;snapshot:unknown}>;local:unknown}
export interface GameDecision {owner_key:string;expected_tips:string[];expected_local:unknown;selected_event_id:string}
export interface GameCompensation {target_action_id:string;expected_tips:string[];expected_local:unknown}
export interface GameAuthorityView {owners:GameOwnerView[];rewards:Array<{event_id:string;date:string;reward:{coins:string;experience:string}}>;blockers:string[]}
export interface GameApplyResult {listed:number;applied:number;conflicts:number;blocked:string[];hasRemainingWork:boolean}
interface Pending {event:GameEvent;frame:number[];nonce:number[]|null;ciphertext:number[]|null}
interface Incoming {event_id:string;server_sequence:number;source_device_id:string;project_id:string|null;entity_id:string;revision:number;updated_at:string;nonce:number[];ciphertext:number[];scope:'project'|'account'}
const native=<T>(scope:MetadataScope,request:unknown)=>invoke<T>('game_sync_command',{scope,request})
const now=()=>canonicalizeSyncTimestamp(new Date().toISOString())
export class GameSyncError extends Error {constructor(readonly code:string){super(code)}}

/** Both cryptographic readers are one capability. Background work never captures
 * legacy Game data; only beginGame is consent to publication. */
export class GameSyncRuntime extends ProgressSyncRuntime {
  async gameReaderAvailable(account:string,device:string):Promise<boolean>{
    try{await this.viewGame(account,device);return true}
    catch(error){if(error==='game_codec_not_activated'||error instanceof Error&&error.message==='game_codec_not_activated')return false;throw error}
  }
  async viewGame(account:string,device:string):Promise<GameAuthorityView>{
    const {scope,context}=await this.scope(account,device)
    const value=await native<GameAuthorityView>(scope,{action:'view'});this.assertCurrent(context);return value
  }
  async declareGameSupport(account:string,device:string):Promise<void>{
    // A client with legacy Python ownership cannot advertise this native reader.
    await this.viewGame(account,device)
    await this.declareSupport(account,device)
    const {context}=await this.scope(account,device)
    await this.auth.authorized(t=>encryptedSyncV3Api.gameReaderCapabilities(t,device));this.assertCurrent(context)
  }
  private async gameGate(account:string,device:string){
    await this.requireMode3(account,device)
    const current=await this.scope(account,device)
    const result=await this.auth.authorized(t=>encryptedSyncV3Api.gameReaderGate(t));this.assertCurrent(current.context)
    if(!result.value.ready)throw new GameSyncError('game_readers_not_ready')
    return current
  }
  async beginGame(account:string,device:string):Promise<GameAuthorityView>{
    await this.declareGameSupport(account,device)
    const {scope,context}=await this.gameGate(account,device)
    const value=await native<GameAuthorityView>(scope,{action:'begin',now:now()});this.assertCurrent(context);return value
  }
  async rebuildGame(account:string,device:string,owner_key:string):Promise<void>{
    const {scope,context}=await this.scope(account,device)
    await native(scope,{action:'rebuild',owner_key});this.assertCurrent(context)
  }
  async chooseGame(account:string,device:string,decision:GameDecision):Promise<void>{
    const {scope,context}=await this.gameGate(account,device)
    await native(scope,{action:'decide',...decision,now:now()});this.assertCurrent(context)
  }
  async compensateGame(account:string,device:string,decision:GameCompensation):Promise<void>{
    const {scope,context}=await this.gameGate(account,device)
    await native(scope,{action:'compensate',...decision,now:now()});this.assertCurrent(context)
  }
  async sealGame(account:string,device:string):Promise<number>{
    const {scope,context}=await this.gameGate(account,device)
    const rows=await native<Pending[]>(scope,{action:'pending',sealed:false});this.assertCurrent(context)
    for(const row of rows){
      const original=Uint8Array.from(row.frame);let frame:Uint8Array=original
      try {
        const e=unframeGameEvent(frame,row.event.header.scope),h=e.header
        if(h.account_id!==context.userId||h.device_id!==device)throw new GameSyncError('game_scope_mismatch')
        const lease=this.keys.leaseForAccount(account);if(!lease)throw new KeyNotProvisionedError()
        await lease.use(async amk=>{
          frame=await this.compressionFrame(account,device,original)
          const sealed=h.scope==='project'
            ?await encryptObjectBytes(amk,{userId:h.account_id,projectId:h.project_id,entityType:'project_game',entityId:h.entity_id},frame)
            :await encryptAccountObject(amk,{userId:h.account_id,scope:'account',entityType:'account_game',entityId:h.entity_id},frame)
          this.assertCurrent(context)
          await native(scope,{action:'seal',event_id:h.event_id,frame:Array.from(frame),nonce:Array.from(sealed.nonce),ciphertext:Array.from(sealed.ciphertext)});this.assertCurrent(context)
        })
      }finally{frame.fill(0);original.fill(0)}
    }
    return rows.length
  }
  async uploadGame(account:string,device:string):Promise<number>{
    const {scope,context}=await this.gameGate(account,device)
    const rows=await native<Pending[]>(scope,{action:'pending',sealed:true});this.assertCurrent(context)
    for(const row of rows){
      const h=row.event.header
      if(h.account_id!==context.userId||h.device_id!==device||!row.nonce||!row.ciphertext)throw new GameSyncError('game_scope_mismatch')
      // Recheck the paired gate before EACH request, including its account half.
      await this.gameGate(account,device);this.assertCurrent(context)
      const nonce=Uint8Array.from(row.nonce),ciphertext=Uint8Array.from(row.ciphertext)
      const response=h.scope==='project'
        ?await this.auth.authorized(t=>encryptedSyncV3Api.pushGame(t,device,[{event:{event_id:h.event_id,project_id:h.project_id,entity_id:h.entity_id,entity_type:'project_game',operation:'event',revision:h.revision,updated_at:h.updated_at,deleted_at:null},object:{crypto_version:1,aad_version:1,nonce,ciphertext}}]))
        :await this.auth.authorized(t=>encryptedSyncV3Api.pushAccount(t,device,[{event:{event_id:h.event_id,canonical_user_id:h.account_id,scope:'account',entity_id:h.entity_id,entity_type:'account_game',operation:'upsert',revision:h.revision,updated_at:h.updated_at,deleted_at:null},object:{crypto_version:2,aad_version:2,nonce,ciphertext}}]))
      this.assertCurrent(context)
      const r=response.value.results[0]
      if(response.value.results.length!==1||r?.event_id!==h.event_id)throw new GameSyncError('game_exact_replay_mismatch')
      await native(scope,{action:'receipt',event_id:h.event_id,server_sequence:r.server_sequence,duplicate:r.duplicate,now:now()});this.assertCurrent(context)
    }
    return rows.length
  }
  async readGameOnce(account:string,device:string,limit=8,passes=4):Promise<GameApplyResult>{
    await this.requireMode3(account,device)
    if(!Number.isInteger(limit)||limit<1||limit>32||!Number.isInteger(passes)||passes<1||passes>8)throw new RangeError('game_resource_limit')
    const {scope,context}=await this.scope(account,device)
    let listed=0,applied=0,conflicts=0,hasRemainingWork=false;const blocked:string[]=[]
    for(let pass=0;pass<passes;pass++){
      const rows=await native<Incoming[]>(scope,{action:'received',limit});this.assertCurrent(context)
      if(!rows.length)break
      listed+=rows.length;hasRemainingWork=rows.length===limit
      for(const row of rows){let frame:Uint8Array|undefined,applying=false
        try{
          const lease=this.keys.leaseForAccount(account);if(!lease)throw new KeyNotProvisionedError()
          const outcome=await lease.use(async amk=>{
            frame=row.scope==='project'
              ?await decryptObjectBytes(amk,{userId:context.userId,projectId:row.project_id!,entityType:'project_game',entityId:row.entity_id},{crypto_version:1,aad_version:1,nonce:Uint8Array.from(row.nonce),ciphertext:Uint8Array.from(row.ciphertext)})
              :await decryptAccountObject(amk,{userId:context.userId,scope:'account',entityType:'account_game',entityId:row.entity_id},{crypto_version:2,aad_version:2,nonce:Uint8Array.from(row.nonce),ciphertext:Uint8Array.from(row.ciphertext)})
            this.assertCurrent(context)
            const e=unframeGameEvent(frame,row.scope),h=e.header
            if(h.account_id!==context.userId||h.device_id!==row.source_device_id||h.event_id!==row.event_id||h.entity_id!==row.entity_id||h.revision!==row.revision||h.updated_at!==row.updated_at||h.scope==='project'&&h.project_id!==row.project_id)throw new GameSyncError('game_scope_mismatch')
            applying=true
            const result=await native<string>(scope,{action:'apply',project:row.scope==='project',frame:Array.from(frame),nonce:row.nonce,ciphertext:row.ciphertext});this.assertCurrent(context);return result
          })
          if(outcome==='applied')applied++;else if(outcome==='conflict_preserved')conflicts++;else{blocked.push(outcome);hasRemainingWork=true}
        }catch(error){
          if(error instanceof StaleAuthContextError||error instanceof KeyNotProvisionedError||applying)throw error
          this.assertCurrent(context)
          const candidate=error instanceof Error?error.message:''
          const code=compressionBlocker(error) ?? (['game_codec_not_activated','game_resource_limit','game_scope_mismatch'].includes(candidate)?candidate:frame?'invalid_game_payload':'decrypt_failed')
          await native(scope,{action:'block',event_id:row.event_id,nonce:row.nonce,ciphertext:row.ciphertext,code});this.assertCurrent(context)
          blocked.push(code);hasRemainingWork=true
        }finally{frame?.fill(0)}
      }
    }
    return {listed,applied,conflicts,blocked,hasRemainingWork:hasRemainingWork||blocked.length>0}
  }
}
