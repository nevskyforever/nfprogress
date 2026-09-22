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
  commitAccepted(accountId: string, deviceId: string, receipts: NoteSyncUploadReceipt[]): Promise<CommitNoteSyncUploadAcceptanceResult[]>
  recordUploadFailure(command: NoteSyncUploadFailure): Promise<void>
}

export interface NoteSyncUploadReceipt {
  event_id: string
  server_sequence: number
  duplicate: boolean
}

export type CommitNoteSyncUploadAcceptanceResult = 'accepted' | 'already_accepted'

export type NoteSyncUploadFailureCode = 'network_unavailable' | 'request_timeout' | 'http_5xx' | 'rate_limited' | 'unauthorized' | 'device_not_registered' | 'cloud_project_disabled' | 'invalid_protocol' | 'conflicting_event' | 'malformed_receipt' | 'local_acceptance_failed'

export interface NoteSyncUploadFailure {
  account_id: string
  device_id: string
  event_ids: string[]
  error_code: NoteSyncUploadFailureCode
}
