import { describe, expect, it, vi } from 'vitest'
import { syncApi } from '@/api/sync'
import { SYNC_OPERATIONS, SYNC_PROTOCOL_VERSION, isSyncEventEnvelope, retrySyncEvent } from './syncProtocol'
import { canEnableCloudProjectSync } from './capabilities'

const event = { event_id: '123e4567-e89b-42d3-a456-426614174000', project_id: 'p', entity_id: 'n', entity_type: 'note', operation: 'upsert' as const, revision: 1, updated_at: '2026-09-21T00:00:00Z', deleted_at: null }

describe('C9 sync protocol', () => {
  it('uses protocol v1 and the exact metadata operation set', () => {
    expect(SYNC_PROTOCOL_VERSION).toBe(1)
    expect(SYNC_OPERATIONS).toEqual(['upsert', 'delete', 'event'])
    expect(isSyncEventEnvelope(event)).toBe(true)
    expect(isSyncEventEnvelope({ ...event, operation: 'delete', deleted_at: null })).toBe(false)
    expect(isSyncEventEnvelope({ ...event, operation: 'delete', deleted_at: '2026-09-21T01:00:00Z' })).toBe(true)
  })
  it('keeps the event id on retry and never adds content fields', () => {
    expect(retrySyncEvent(event)).toEqual(event)
    expect(Object.keys(event)).not.toContain('payload')
    expect(Object.keys(event)).not.toContain('content')
  })
  it('serializes typed registration, push, cursor pull, and ack requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ protocol_version: 1, device_id: 'd', last_ack_cursor: 0 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ protocol_version: 1, results: [], current_cursor: 0 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ protocol_version: 1, events: [], next_cursor: 4, has_more: false }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await syncApi.registerDevice('token', '123e4567-e89b-42d3-a456-426614174000')
    await syncApi.push('token', { protocol_version: 1, device_id: event.event_id, events: [event] })
    await syncApi.pull('token', event.event_id, 4)
    await syncApi.ack('token', { protocol_version: 1, device_id: event.event_id, cursor: 4 })
    expect(fetchMock.mock.calls[1]![1]).toMatchObject({ method: 'POST', body: JSON.stringify({ protocol_version: 1, device_id: event.event_id, events: [event] }) })
    expect(String(fetchMock.mock.calls[2]![0])).toContain('since=4')
    expect(fetchMock.mock.calls[3]![1]).toMatchObject({ method: 'POST' })
  })
  it('does not enable the C8 production gate', () => expect(canEnableCloudProjectSync()).toBe(false))
})
