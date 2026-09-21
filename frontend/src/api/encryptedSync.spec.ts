import { describe, expect, it, vi } from 'vitest'
import type { SyncEventEnvelope } from '@/cloud/syncProtocol'
import {
  MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES,
  MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
  assertEncryptedSyncBatch,
  encryptedSyncApi,
  encryptedSyncObjectFromWire,
  type EncryptedSyncPushItem,
} from './encryptedSync'

const event: SyncEventEnvelope = {
  event_id: '123e4567-e89b-42d3-a456-426614174000', project_id: 'project-1', entity_id: 'note-1',
  entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-09-21T00:00:00.000000Z', deleted_at: null,
}

function item(ciphertext: Uint8Array): EncryptedSyncPushItem {
  return { event, object: { crypto_version: 1, aad_version: 1, nonce: new Uint8Array(24), ciphertext } }
}

describe('encrypted sync transport boundary', () => {
  it('enforces exact individual and aggregate decoded ciphertext limits', () => {
    expect(() => assertEncryptedSyncBatch([item(new Uint8Array(MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES))])).not.toThrow()
    expect(() => assertEncryptedSyncBatch([item(new Uint8Array(MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1))])).toThrow(TypeError)
    const half = MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES / 2
    expect(() => assertEncryptedSyncBatch([item(new Uint8Array(half)), item(new Uint8Array(half))])).not.toThrow()
    expect(() => assertEncryptedSyncBatch([item(new Uint8Array(half)), item(new Uint8Array(half + 1))])).toThrow(RangeError)
  })

  it('rejects malformed/noncanonical wire envelopes and oversized decoded objects', () => {
    const valid = { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' }
    expect(encryptedSyncObjectFromWire(valid)).toMatchObject({ ciphertext: new Uint8Array(16) })
    expect(() => encryptedSyncObjectFromWire({ ...valid, nonce: `${valid.nonce}=` })).toThrow(TypeError)
    expect(() => encryptedSyncObjectFromWire({ ...valid, ciphertext: '*' })).toThrow(TypeError)
  })

  it('serializes canonical Base64URL push and decodes pull without changing C9 metadata', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ protocol_version: 1, encrypted_sync_version: 1, results: [], current_cursor: 0 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        protocol_version: 1, encrypted_sync_version: 1, next_cursor: 1, has_more: false,
        items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: {
          crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA',
        } }],
      }), { status: 200 }))
    await encryptedSyncApi.push('token', {
      protocol_version: 1, encrypted_sync_version: 1, device_id: event.event_id.toUpperCase(),
      items: [{ ...item(new Uint8Array(16)), event: { ...event, event_id: event.event_id.toUpperCase() } }],
    })
    const body = String(fetchMock.mock.calls[0]![1]?.body)
    expect(body).toContain('"nonce":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"')
    expect(body).toContain(`"device_id":"${event.event_id}"`)
    expect(body).toContain(`"event_id":"${event.event_id}"`)
    expect(body).not.toContain(event.event_id.toUpperCase())
    expect(body).not.toContain('=')
    await expect(encryptedSyncApi.pull('token', event.event_id, 0)).resolves.toMatchObject({
      items: [{ event, object: { ciphertext: new Uint8Array(16) } }],
    })
    fetchMock.mockRestore()
  })
})
