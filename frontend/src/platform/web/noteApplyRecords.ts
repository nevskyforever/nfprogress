import type { V3Descriptor } from '@/api/encryptedSyncV3'
import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import type { NoteSyncHeader } from '@/cloud/noteSyncCodec'
import { BrowserPersistenceError } from './persistence'
import type { BrowserSyncScope } from './syncDurability'
import { localExact, localId, localSafe } from './localAuthorityRecords'
export interface BrowserNoteProof {
  record_version: 1; owner_kind: 'legacy_note'; outcome: 'applied' | 'self_echo_applied'
  account_id: string; bootstrap_id: string; protocol_version: 2 | 3; reference: V3Descriptor
  header: NoteSyncHeader; mutation: 'create' | 'update' | 'delete'; wire_digest: string; outcome_digest: string
  source_revision: number | null; local_note_digest: string | null
}
const hash=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v)
function corrupt():never{throw new BrowserPersistenceError('corrupt_record')}
export function validateBrowserNoteProof(value:unknown,scope:BrowserSyncScope):BrowserNoteProof {
  if(!localExact(value,['record_version','owner_kind','outcome','account_id','bootstrap_id','protocol_version','reference','header','mutation','wire_digest','outcome_digest','source_revision','local_note_digest']))corrupt()
  const p=value as unknown as BrowserNoteProof,h=p.header,r=p.reference
  if(p.record_version!==1||p.owner_kind!=='legacy_note'||!['applied','self_echo_applied'].includes(p.outcome)||p.account_id!==scope.accountId||![2,3].includes(p.protocol_version)||!hash(p.wire_digest)||!hash(p.outcome_digest)||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(p.bootstrap_id))corrupt()
  if(!localExact(h,['event_id','parent_event_id','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||!localExact(r,['event_id','device_id','server_sequence','project_id','entity_id','entity_type','operation','revision','updated_at','deleted_at'])||h.entity_type!=='note'||r.entity_type!=='note'||!['create','update','delete'].includes(p.mutation)||!localSafe(h.revision,1))corrupt()
  localId(h.project_id);localId(h.entity_id)
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(h.event_id)||!(h.parent_event_id===null||/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(h.parent_event_id))||h.parent_event_id===h.event_id||(h.revision===1)!==(h.parent_event_id===null)||(p.mutation==='create')!==(h.revision===1&&h.operation==='upsert')||(p.mutation==='delete')!==(h.operation==='delete'))corrupt()
  if(h.event_id!==r.event_id||h.project_id!==r.project_id||h.entity_id!==r.entity_id||h.operation!==r.operation||h.revision!==r.revision||!localSafe(r.server_sequence,1))corrupt()
  try{if(canonicalizeSyncTimestamp(h.updated_at)!==canonicalizeSyncTimestamp(r.updated_at)||(h.deleted_at===null)!==(r.deleted_at===null)||h.deleted_at!==null&&canonicalizeSyncTimestamp(h.deleted_at)!==canonicalizeSyncTimestamp(r.deleted_at!))corrupt()}catch{corrupt()}
  if((h.operation==='delete')!==(h.deleted_at!==null))corrupt()
  if(p.outcome==='self_echo_applied'){if(r.device_id!==scope.deviceId||p.source_revision!==null||p.local_note_digest!==null)corrupt()}
  else if(r.device_id===scope.deviceId||!localSafe(p.source_revision,1)||!hash(p.local_note_digest))corrupt()
  return p
}

export interface BrowserNoteConflictProof {
 record_version:1;owner_kind:'legacy_note';outcome:'conflict_preserved';account_id:string;bootstrap_id:string
 protocol_version:2|3;reference:V3Descriptor;header:NoteSyncHeader;mutation:'update'|'delete'
 wire_digest:string;outcome_digest:string;group_id:string;conflict_generation:number
}
export function validateBrowserNoteConflictProof(value:unknown,scope:BrowserSyncScope):BrowserNoteConflictProof {
 if(!localExact(value,['record_version','owner_kind','outcome','account_id','bootstrap_id','protocol_version','reference','header','mutation','wire_digest','outcome_digest','group_id','conflict_generation']))corrupt()
 const p=value as unknown as BrowserNoteConflictProof
 if(p.outcome!=='conflict_preserved'||!['update','delete'].includes(p.mutation)||!localSafe(p.conflict_generation,1)||!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(p.group_id)||p.header?.parent_event_id===null||!localSafe(p.header?.revision,2))corrupt()
 // Detached validator view only; never persisted or treated as an applied projection.
 const {group_id:_group,conflict_generation:_generation,...body}=p
 validateBrowserNoteProof({...body,outcome:'applied',source_revision:1,local_note_digest:'0'.repeat(64)},scope)
 return p
}
