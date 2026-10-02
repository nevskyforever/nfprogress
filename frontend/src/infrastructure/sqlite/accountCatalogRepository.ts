import { invoke } from '@tauri-apps/api/core';
import type { CatalogEvent, CatalogPayload, CatalogType } from '@/cloud/accountCatalogCodec';
import type { MetadataScope } from './projectMetadataMigrationRepository';
export interface CatalogEntity {
    entity_type: CatalogType;
    entity_id: string;
    tips: string[];
    branches: CatalogEvent[];
    local: CatalogPayload;
    conflict: boolean;
}
export interface CatalogView {
    state: 'catalog_local' | 'captured' | 'publication_pending' | 'self_echo_pending' | 'active' | 'conflict' | 'blocked';
    entities: CatalogEntity[];
    blockers: string[];
    project_names: Record<string, string>;
}
export interface CatalogDecision {
    entity_type: CatalogType;
    entity_id: string;
    expected_tips: string[];
    expected_local: CatalogPayload;
    proposed: CatalogPayload;
    selected_event_id: string | null;
}
export interface CatalogPending {
    event: CatalogEvent;
    nonce: number[] | null;
    ciphertext: number[] | null;
}
export class SQLiteAccountCatalogRepository {
    authority(scope: MetadataScope): Promise<CatalogView> { return invoke('read_account_catalog', { scope }); }
    begin(scope: MetadataScope, now: string): Promise<CatalogView> { return invoke('begin_account_catalog', { scope, now }); }
    decide(scope: MetadataScope, decision: CatalogDecision, now: string): Promise<string> { return invoke('decide_account_catalog', { scope, decision, now }); }
    pending(scope: MetadataScope, sealed: boolean, now: string): Promise<CatalogPending[]> { return invoke('pending_account_catalog', { scope, sealed, now }); }
    seal(scope: MetadataScope, eventId: string, frame: Uint8Array, nonce: Uint8Array, ciphertext: Uint8Array): Promise<void> { return invoke('seal_account_catalog', { scope, eventId, frame: Array.from(frame), nonce: Array.from(nonce), ciphertext: Array.from(ciphertext) }); }
    receipt(scope: MetadataScope, eventId: string, serverSequence: number): Promise<void> { return invoke('receipt_account_catalog', { scope, eventId, serverSequence }); }
}
