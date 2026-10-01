import { invoke } from '@tauri-apps/api/core'
import type { StructuralEvent, StagePortable } from '@/cloud/stageCodec'
import type { MetadataScope, ReceivedMetadataEvent } from './projectMetadataMigrationRepository'
export interface StructuralEntity {
  entity_type: 'stage' | 'stage_order'; entity_id: string; tips: string[]
  branches: StructuralEvent[]; local: StagePortable | string[]; conflict: boolean; causal_tombstone_selected?: boolean
}
export interface StructuralView {
  state: 'structural_local' | 'candidate_captured' | 'publication_pending' | 'published_self_echo_pending' | 'active' | 'conflict' | 'blocked'
  migration_id: string | null; blockers: string[]; entities: StructuralEntity[]; order: string[]
}
export interface StructuralDecision {
  entity_type: 'stage' | 'stage_order'; entity_id: string; expected_tips: string[]
  expected_local: StagePortable | string[]; proposed: StagePortable | string[] | null; selected_event_id: string | null
}
export interface StructuralPending { event: StructuralEvent; nonce: number[] | null; ciphertext: number[] | null }
export interface StructuralReceived extends ReceivedMetadataEvent { entity_type: 'stage' | 'stage_order' }
export class SQLiteStageStructuralRepository {
  authority(scope: MetadataScope, projectId: string): Promise<StructuralView> { return invoke('read_stage_structural_authority', { scope, projectId }) }
  begin(scope: MetadataScope, projectId: string, now: string): Promise<StructuralView> { return invoke('begin_stage_structural_migration', { scope, projectId, now }) }
  decide(scope: MetadataScope, projectId: string, decision: StructuralDecision, now: string): Promise<string> { return invoke('prepare_stage_structural_decision', { scope, projectId, decision, now }) }
  pending(scope: MetadataScope, sealed: boolean): Promise<StructuralPending[]> { return invoke('list_pending_stage_structural', { scope, sealed }) }
  seal(scope: MetadataScope, eventId: string, frame: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array): Promise<void> {
    return invoke('commit_sealed_stage_structural', { scope, eventId, frame: Array.from(frame), nonce: Array.from(nonce), ciphertext: Array.from(ciphertext) })
  }
  receipt(scope: MetadataScope, eventId: string, serverSequence: number, duplicate: boolean, now: string): Promise<void> {
    return invoke('commit_stage_structural_receipt', { scope, eventId, serverSequence, duplicate, now })
  }
  received(scope: MetadataScope, limit: number, after: number): Promise<StructuralReceived[]> { return invoke('list_received_stage_structural', { scope, limit, afterServerSequence: after }) }
  apply(scope: MetadataScope, eventId: string, frame: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array): Promise<string> {
    return invoke('apply_authenticated_stage_structural', { scope, eventId, frame: Array.from(frame), nonce: Array.from(nonce), ciphertext: Array.from(ciphertext) })
  }
  block(scope: MetadataScope, eventId: string, reason: string): Promise<void> { return invoke('record_stage_structural_blocker', { scope, eventId, reason }) }
  retry(scope: MetadataScope): Promise<void> { return invoke('retry_stage_structural', { scope }) }
}
