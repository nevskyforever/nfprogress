import type { NoteSyncSealState,NoteSyncSealErrorCode } from '@/cloud/noteSyncIntent'
import { timestamp } from '@/cloud/projectMetadataCodec'
import { BrowserPersistenceError } from './persistence'
import { localExact,localId,localSafe,validateLocalNoteRecord,type LocalNoteRecord,type LocalEnvelope } from './localAuthorityRecords'
import { canonicalNoteUuid,noteHistoryHash } from './noteHistoryRecords'
import type { BrowserSyncScope } from './syncDurability'
export const NOTE_INTENT_STORE='legacyNoteIntents'
export interface BrowserNoteIntent {
 record_version:1;account_id:string;device_id:string;project_id:string;note_id:string;bootstrap_id:string;event_id:string
 operation:'upsert'|'delete';revision:number;parent_event_id:string|null;updated_at:string;deleted_at:string|null
 local_ordinal:number;mutation_generation:number;snapshot:LocalNoteRecord;snapshot_digest:string;intent_envelope:LocalEnvelope
 seal_state:NoteSyncSealState;seal_attempt_count:number;last_error_code:NoteSyncSealErrorCode|null;next_attempt_at:null
}
export function sealFailureState(code:NoteSyncSealErrorCode):NoteSyncSealState {
 if(['key_unavailable','payload_too_large','encrypted_sync_object_too_large','dependency_not_synced','unsupported_content_format'].includes(code))return 'blocked'
 if(code==='runtime_unavailable')return 'retryable_error'
 if(['invalid_note_payload','crypto_context_invalid','invalid_sync_metadata','invalid_envelope','metadata_mismatch'].includes(code))return 'invariant_error'
 throw new BrowserPersistenceError('corrupt_record')
}
export function validateNoteIntent(v:unknown,s:BrowserSyncScope):BrowserNoteIntent{
 const r=v as BrowserNoteIntent,bad=():never=>{throw new BrowserPersistenceError('corrupt_record')}
 if(!localExact(r,['record_version','account_id','device_id','project_id','note_id','bootstrap_id','event_id','operation','revision','parent_event_id','updated_at','deleted_at','local_ordinal','mutation_generation','snapshot','snapshot_digest','intent_envelope','seal_state','seal_attempt_count','last_error_code','next_attempt_at'])||r.record_version!==1||r.account_id!==s.accountId||r.device_id!==s.deviceId||!canonicalNoteUuid(r.bootstrap_id)||!canonicalNoteUuid(r.event_id)||r.event_id[14]!=='4'||!localSafe(r.revision,1)||!localSafe(r.local_ordinal,1)||!localSafe(r.mutation_generation,1)||!localSafe(r.seal_attempt_count)||!noteHistoryHash(r.snapshot_digest)||!timestamp(r.updated_at)||r.next_attempt_at!==null)bad()
 localId(r.project_id);localId(r.note_id)
 if((r.revision===1)!==(r.parent_event_id===null)||r.parent_event_id!==null&&(!canonicalNoteUuid(r.parent_event_id)||r.parent_event_id===r.event_id)||!['upsert','delete'].includes(r.operation)||(r.operation==='delete')!==(r.deleted_at!==null)||r.deleted_at!==null&&r.updated_at!==r.deleted_at)bad()
 if(r.seal_state==='pending'){if(r.seal_attempt_count!==0||r.last_error_code!==null)bad()}else if(!r.last_error_code||r.seal_attempt_count<1||sealFailureState(r.last_error_code)!==r.seal_state)bad()
 validateLocalNoteRecord({...r.snapshot,envelope:r.intent_envelope},s,r.project_id)
 const p=validateLocalNoteRecord(r.snapshot,s,r.project_id);if(p.note_id!==r.note_id||p.deleted!==(r.operation==='delete'))bad()
 return r
}
