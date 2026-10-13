import { BrowserPersistenceError } from './persistence'
import { validateBrowserInboxRecord, immutableWireIdentity, type BrowserSyncScope, type BrowserSyncCheckpoint } from './syncDurability'
import { validateBrowserMetadataHead } from './metadataApplyRecords'
import { validateBrowserProjectBinding, type BrowserProjectBinding } from './projectBindings'

export type BrowserAckPrerequisiteCode = 'registry_reconciliation_required' | 'bootstrap_completion_unavailable' | 'pull_required' | 'protected_apply_required' | 'unsupported_family_proof' | 'ack_proof_unavailable'
export interface BrowserAckInventory {
  note_received_only: number; note_applied: number; note_self_echo: number; received_only: number; metadata_authority_only: number; missing_next_sequence: boolean
  unsupported_families: string[]; first_unproven_sequence: number | null; proven_prefix: 0
}
export interface BrowserAckPrerequisites {
  ready: false; ack_eligible: false; code: BrowserAckPrerequisiteCode; required_cursor: number
  pull_cursor: number; ack_cursor: 0; proven_prefix: 0; inventory: BrowserAckInventory
}
function corrupt(): never { throw new BrowserPersistenceError('corrupt_record') }
/** Exact durable record inventory. Metadata authority is NOT a general native apply/ACK ledger. */
export function inspectBrowserAckInventory(scope: BrowserSyncScope, cursor: BrowserSyncCheckpoint, inbound: unknown[], heads: unknown[], bindings: BrowserProjectBinding[]): BrowserAckInventory {
  if (cursor.ack_cursor !== 0 || cursor.proven_prefix !== 0 || !Number.isSafeInteger(cursor.pull_cursor) || cursor.pull_cursor < 0) corrupt()
  const rows = inbound.map(v => validateBrowserInboxRecord(v,scope)), sequences = new Set<number>(), events = new Set<string>()
  const owners = heads.map(v => validateBrowserMetadataHead(v,scope))
  if (new Set(owners.map(h=>h.owner_id)).size !== owners.length) corrupt()
  const inventory: BrowserAckInventory = {note_received_only:0,note_applied:0,note_self_echo:0,received_only:0,metadata_authority_only:0,missing_next_sequence:cursor.pull_cursor>0&&!rows.some(r=>r.server_sequence===1),unsupported_families:[],first_unproven_sequence:cursor.pull_cursor>0?1:null,proven_prefix:0}
  const families = new Set<string>()
  for (const r of rows) {
    if (r.server_sequence > cursor.pull_cursor || sequences.has(r.server_sequence) || events.has(r.event_id)) corrupt()
    sequences.add(r.server_sequence);events.add(r.event_id)
    const event = JSON.parse(r.wire_item).event
    if (r.state === 'received') { inventory.received_only++; if(event.entity_type==='note'&&['upsert','delete'].includes(event.operation))inventory.note_received_only++ }
    else if(r.state==='note_proven'){const binding=bindings.find(b=>b.project_id===r.note_proof.header.project_id);if(!binding)corrupt();const lineage=validateBrowserProjectBinding(binding,scope);if(lineage.bootstrap_id!==r.note_proof.bootstrap_id||lineage.remote_state!=='active'||!(lineage.mode==='import_remote'&&lineage.phase==='captured'||lineage.mode==='upload_existing'&&lineage.phase==='completing'))corrupt();if(r.note_proof.outcome==='applied')inventory.note_applied++;else inventory.note_self_echo++}
    else {
      const proof = r.applied_proof, head = owners.find(h=>h.owner_id===proof.project_id), binding = bindings.find(b=>b.project_id===proof.project_id)
      if (!head || !binding) corrupt()
      const lineage = validateBrowserProjectBinding(binding,scope)
      if (lineage.mode !== 'import_remote' || lineage.phase !== 'captured' || lineage.remote_state !== 'active' || head.bootstrap_id!==lineage.bootstrap_id || !head.history.some(p=>immutableWireIdentity(p)===immutableWireIdentity(proof))) corrupt()
      inventory.metadata_authority_only++
    }
    if (event.entity_type !== 'project_metadata' && r.state!=='note_proven') families.add(event.entity_type)
  }
  for (const h of owners) for (const p of h.history) if (!rows.some(r=>r.state==='applied' && r.event_id===p.event_id && immutableWireIdentity(r.applied_proof)===immutableWireIdentity(p))) corrupt()
  inventory.unsupported_families=[...families].sort()
  // No positive candidate: cross-family aggregation is outside this slice; Metadata
  // and unsupported families still lack native ledgers. Note outcomes alone are not ACK.
  return inventory
}
export function browserAckPrerequisites(binding: BrowserProjectBinding, cursor: BrowserSyncCheckpoint, inventory: BrowserAckInventory, registryCurrent: boolean): BrowserAckPrerequisites {
  const required_cursor=Math.max(binding.remote_high_water??0,binding.initial_max_server_sequence??0)
  let code:BrowserAckPrerequisiteCode='registry_reconciliation_required'
  if(registryCurrent){
    if(binding.remote_state!=='active'||binding.mode==='upload_existing'&&binding.phase!=='completing')code='bootstrap_completion_unavailable'
    else if(cursor.pull_cursor<required_cursor)code='pull_required'
    else if(inventory.missing_next_sequence)code='protected_apply_required'
    else if(inventory.unsupported_families.length)code='unsupported_family_proof'
    else if(inventory.received_only||inventory.metadata_authority_only)code='protected_apply_required'
    else code='ack_proof_unavailable'
  }
  return {ready:false,ack_eligible:false,code,required_cursor,pull_cursor:cursor.pull_cursor,ack_cursor:0,proven_prefix:0,inventory}
}
