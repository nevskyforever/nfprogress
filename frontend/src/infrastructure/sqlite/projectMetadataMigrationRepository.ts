import { canonicalizeSyncTimestamp } from '@/cloud/syncTimestamp'
import { invoke } from '@tauri-apps/api/core'
import { encodeBase64Url } from '@/api/base64url'
import type { V3PullResponse } from '@/api/encryptedSyncV3'
import type { ProjectMetadataEvent } from '@/cloud/projectMetadataCodec'
import type { ProjectMetadata } from '@/cloud/projectMetadataCodec'
import type { CommitInboundPageResult } from './noteSyncInboxRepository'

export interface MetadataScope { account_id: string; canonical_user_id: string; device_id: string }
export interface MetadataMigrationStatus {
  state: 'legacy_local' | 'legacy_candidate_present' | 'blocked_missing_bootstrap' | 'blocked_unsupported'
    | 'genesis_pending' | 'awaiting_remote_confirmation' | 'authenticated_metadata_active' | 'genesis_conflict' | 'apply_blocked'
  candidate_id: string | null; event_id: string | null; blockers: string[]; genesis_tips: number
}
export interface SealedMetadataGenesis {
  event_id: string; project_id: string; revision: number; updated_at: string; nonce: number[]; ciphertext: number[]
}
export interface ReceivedMetadataEvent {
  event_id: string; server_sequence: number; source_device_id: string; project_id: string; entity_id: string
  revision: number; updated_at: string; deleted_at: string | null; operation: 'upsert' | 'delete' | 'resolution'
  crypto_version: number; aad_version: number; nonce: number[]; ciphertext: number[]
}
export interface MetadataAuthorityBranch { event_id: string; revision: number; operation: string; metadata: ProjectMetadata; device_id?: string; local_candidate?: boolean }
export interface MetadataAuthorityView {
  state: 'local_legacy_only' | 'local_candidate_ready' | 'local_matches_authenticated'
    | 'local_differs_from_authenticated' | 'genesis_conflict' | 'metadata_conflict' | 'resolution_pending' | 'active' | 'blocked'
  local: ProjectMetadata | null; authenticated: ProjectMetadata | null; head_event_id: string | null
  branches: MetadataAuthorityBranch[]; pending_event_id: string | null; blockers: string[]
}
export type MetadataDecisionKind = 'keep_local' | 'manual' | 'edit' | 'choose_branch' | 'resolve_manual'

export interface MetadataImportProgress {
  cursor: number; state: 'running' | 'complete' | 'blocked'; blocker: string | null; event_count: number
  metadata: ProjectMetadata | null; head: string | null; tips: string[]
}
export interface MetadataImportPage {
  expected_cursor: number; next_cursor: number; has_more: boolean; page_events: number; page_identity: string
  events: Array<{ server_sequence: number; plaintext: number[] }>
}

export interface ProjectMetadataMigrationRepository {
  readImport(scope: MetadataScope, projectId: string, bootstrapId: string): Promise<MetadataImportProgress>
  commitImportPage(scope: MetadataScope, projectId: string, bootstrapId: string, page: MetadataImportPage): Promise<MetadataImportProgress>
  capture(scope: MetadataScope, projectId: string, now: string): Promise<string>
  status(scope: MetadataScope, projectId: string): Promise<MetadataMigrationStatus>
  prepare(scope: MetadataScope, candidateId: string, now: string): Promise<string>
  unsealed(scope: MetadataScope): Promise<ProjectMetadataEvent[]>
  commitSealed(scope: MetadataScope, eventId: string, nonce: Uint8Array, ciphertext: Uint8Array): Promise<void>
  sealed(scope: MetadataScope): Promise<SealedMetadataGenesis[]>
  commitReceipt(scope: MetadataScope, eventId: string, serverSequence: number, duplicate: boolean, now: string): Promise<void>
  received(scope: MetadataScope, limit: number, after: number): Promise<ReceivedMetadataEvent[]>
  apply(scope: MetadataScope, projectId: string, plaintext: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array, now: string): Promise<'applied' | 'conflict_preserved' | 'orphan'>
  commitV3Page(scope: MetadataScope, since: number, page: V3PullResponse): Promise<CommitInboundPageResult>
  authority(scope: MetadataScope, projectId: string): Promise<MetadataAuthorityView>
  adopt(scope: MetadataScope, projectId: string, expectedHead: string, expectedLocal: ProjectMetadata, now: string): Promise<MetadataAuthorityView>
  prepareChange(scope: MetadataScope, projectId: string, kind: MetadataDecisionKind, selectedEventId: string | null,
    proposed: ProjectMetadata | null, expectedLocal: ProjectMetadata, expectedTips: string[], now: string): Promise<string>
}

const bytes = (value: Uint8Array): number[] => Array.from(value)

export class SQLiteProjectMetadataMigrationRepository implements ProjectMetadataMigrationRepository {
  readImport(scope: MetadataScope, projectId: string, bootstrapId: string): Promise<MetadataImportProgress> {
    return invoke('read_project_metadata_import', { scope, projectId, bootstrapId })
  }
  commitImportPage(scope: MetadataScope, projectId: string, bootstrapId: string, page: MetadataImportPage): Promise<MetadataImportProgress> {
    return invoke('commit_project_metadata_import_page', { scope, projectId, bootstrapId, page })
  }
  authority(scope: MetadataScope, projectId: string): Promise<MetadataAuthorityView> {
    return invoke('read_project_metadata_authority', { scope, projectId })
  }
  adopt(scope: MetadataScope, projectId: string, expectedHead: string, expectedLocal: ProjectMetadata, now: string): Promise<MetadataAuthorityView> {
    return invoke('adopt_authenticated_project_metadata', { scope, projectId, expectedHead, expectedLocal, now })
  }
  prepareChange(scope: MetadataScope, projectId: string, kind: MetadataDecisionKind, selectedEventId: string | null,
    proposed: ProjectMetadata | null, expectedLocal: ProjectMetadata, expectedTips: string[], now: string): Promise<string> {
    return invoke('prepare_project_metadata_change', { scope, projectId, kind, selectedEventId, proposed, expectedLocal, expectedTips, now })
  }
  capture(scope: MetadataScope, projectId: string, now: string): Promise<string> {
    return invoke('capture_project_metadata_candidate', { scope, projectId, now })
  }
  status(scope: MetadataScope, projectId: string): Promise<MetadataMigrationStatus> {
    return invoke('read_project_metadata_migration_status', { scope, projectId })
  }
  prepare(scope: MetadataScope, candidateId: string, now: string): Promise<string> {
    return invoke('prepare_project_metadata_genesis', { scope, candidateId, now })
  }
  unsealed(scope: MetadataScope): Promise<ProjectMetadataEvent[]> {
    return invoke('list_unsealed_project_metadata_genesis', { scope })
  }
  commitSealed(scope: MetadataScope, eventId: string, nonce: Uint8Array, ciphertext: Uint8Array): Promise<void> {
    return invoke('commit_sealed_project_metadata_genesis', { scope, eventId, nonce: bytes(nonce), ciphertext: bytes(ciphertext) })
  }
  sealed(scope: MetadataScope): Promise<SealedMetadataGenesis[]> {
    return invoke('list_sealed_project_metadata_genesis', { scope })
  }
  commitReceipt(scope: MetadataScope, eventId: string, serverSequence: number, duplicate: boolean, now: string): Promise<void> {
    return invoke('commit_project_metadata_upload_receipt', { scope, eventId, serverSequence, duplicate, now })
  }
  received(scope: MetadataScope, limit: number, after: number): Promise<ReceivedMetadataEvent[]> {
    return invoke('list_received_project_metadata', { scope, limit, afterServerSequence: after })
  }
  apply(scope: MetadataScope, projectId: string, plaintext: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array, now: string): Promise<'applied' | 'conflict_preserved' | 'orphan'> {
    return invoke('apply_authenticated_project_metadata', { scope, projectId, plaintext: bytes(plaintext), nonce: bytes(nonce), ciphertext: bytes(ciphertext), now })
  }
  commitV3Page(scope: MetadataScope, since: number, page: V3PullResponse): Promise<CommitInboundPageResult> {
    return invoke('commit_v3_sync_inbound_page', { command: {
      account_id: scope.account_id, canonical_user_id: scope.canonical_user_id, device_id: scope.device_id,
      expected_cursor: since, next_cursor: page.next_cursor, has_more: page.has_more,
      items: page.items.map(({ event, object }) => ({
        event_id: event.event_id, server_sequence: event.server_sequence, source_device_id: event.device_id,
        project_id: event.project_id, entity_id: event.entity_id, entity_type: event.entity_type,
        operation: event.operation, revision: event.revision, updated_at: canonicalizeSyncTimestamp(event.updated_at), deleted_at: event.deleted_at === null ? null : canonicalizeSyncTimestamp(event.deleted_at),
        envelope: { crypto_version: object.crypto_version, aad_version: object.aad_version,
          nonce: encodeBase64Url(object.nonce), ciphertext: encodeBase64Url(object.ciphertext) },
      })),
    } })
  }
}
