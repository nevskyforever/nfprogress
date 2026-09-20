import { apiRequest } from './client'
import {
  SYNC_PROTOCOL_VERSION,
  type SyncAckRequest,
  type SyncPullResponse,
  type SyncPushRequest,
  type SyncPushResponse,
} from '@/cloud/syncProtocol'

function authorization(accessToken: string): Headers {
  const headers = new Headers()
  headers.set('Authorization', `Bearer ${accessToken}`)
  return headers
}

export interface SyncDeviceResponse {
  protocol_version: typeof SYNC_PROTOCOL_VERSION
  device_id: string
  last_ack_cursor: number
}

/** Typed C9 client only. Production UI deliberately does not call this yet. */
export const syncApi = {
  registerDevice(accessToken: string, deviceId: string): Promise<SyncDeviceResponse> {
    return apiRequest(`/api/v1/sync/devices/${encodeURIComponent(deviceId)}`, {
      method: 'PUT', headers: authorization(accessToken),
    })
  },
  push(accessToken: string, request: SyncPushRequest): Promise<SyncPushResponse> {
    return apiRequest('/api/v1/sync/push', { method: 'POST', headers: authorization(accessToken), body: request })
  },
  pull(accessToken: string, deviceId: string, since: number, limit?: number): Promise<SyncPullResponse> {
    const query = new URLSearchParams({ device_id: deviceId, since: String(since), protocol_version: String(SYNC_PROTOCOL_VERSION) })
    if (limit !== undefined) query.set('limit', String(limit))
    return apiRequest(`/api/v1/sync/pull?${query}`, { headers: authorization(accessToken) })
  },
  ack(accessToken: string, request: SyncAckRequest): Promise<void> {
    return apiRequest('/api/v1/sync/ack', { method: 'POST', headers: authorization(accessToken), body: request })
  },
}
