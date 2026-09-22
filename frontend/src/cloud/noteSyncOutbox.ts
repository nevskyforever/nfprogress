export interface SealedNoteSyncEnvelope {
  crypto_version: 1
  aad_version: 1
  nonce: string
  ciphertext: string
}

/** Opaque, already-sealed transport input. It intentionally has no plaintext or keys. */
export interface SealedNoteSyncOutboxItem {
  event_id: string
  account_id: string
  device_id: string
  project_id: string
  entity_id: string
  entity_type: 'note'
  operation: 'upsert' | 'delete'
  revision: number
  parent_event_id: string | null
  updated_at: string
  deleted_at: string | null
  local_ordinal: number
  envelope: SealedNoteSyncEnvelope
}

export interface NoteSyncOutboxRepository {
  listSealed(accountId: string, limit: number): Promise<SealedNoteSyncOutboxItem[]>
}
