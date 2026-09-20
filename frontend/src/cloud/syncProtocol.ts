/** C9 metadata-only transport contract. It does not serialize project content. */
export const SYNC_PROTOCOL_VERSION = 1 as const
export const SYNC_OPERATIONS = ['upsert', 'delete', 'event'] as const
export type SyncOperation = (typeof SYNC_OPERATIONS)[number]

export interface SyncEventEnvelope {
  event_id: string
  project_id: string
  entity_id: string
  entity_type: string
  operation: SyncOperation
  revision: number
  updated_at: string
  deleted_at: string | null
}

export interface SyncPushRequest {
  protocol_version: typeof SYNC_PROTOCOL_VERSION
  device_id: string
  events: SyncEventEnvelope[]
}
export interface SyncPushResponse {
  protocol_version: typeof SYNC_PROTOCOL_VERSION
  results: Array<{ event_id: string; server_sequence: number; duplicate: boolean }>
  current_cursor: number
}
export interface SyncPullResponse {
  protocol_version: typeof SYNC_PROTOCOL_VERSION
  events: Array<SyncEventEnvelope & { device_id: string; server_sequence: number }>
  next_cursor: number
  has_more: boolean
}
export interface SyncAckRequest {
  protocol_version: typeof SYNC_PROTOCOL_VERSION
  device_id: string
  cursor: number
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const ENTITY_TYPE = /^[a-z][a-z0-9_:-]*$/

export function isSyncEventEnvelope(value: SyncEventEnvelope): boolean {
  const timestamp = (input: string | null) => input === null || !Number.isNaN(Date.parse(input))
  return UUID.test(value.event_id)
    && value.project_id.length > 0 && value.project_id.length <= 512
    && value.entity_id.length > 0 && value.entity_id.length <= 512
    && value.entity_type.length > 0 && value.entity_type.length <= 128 && ENTITY_TYPE.test(value.entity_type)
    && (SYNC_OPERATIONS as readonly string[]).includes(value.operation)
    && Number.isSafeInteger(value.revision) && value.revision >= 1
    && timestamp(value.updated_at) && timestamp(value.deleted_at)
    && ((value.operation === 'delete') === (value.deleted_at !== null))
}

/** Retries reuse the stored envelope verbatim, especially its event_id. */
export function retrySyncEvent(event: SyncEventEnvelope): SyncEventEnvelope {
  return { ...event }
}
