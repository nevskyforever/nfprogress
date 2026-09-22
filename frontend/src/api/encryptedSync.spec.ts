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
import { ApiResponseTooLargeError } from './client'

const event: SyncEventEnvelope = {
  event_id: '123e4567-e89b-42d3-a456-426614174000', project_id: 'project-1', entity_id: 'note-1',
  entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-09-21T00:00:00.000000Z', deleted_at: null,
}

function item(ciphertext: Uint8Array): EncryptedSyncPushItem {
  return { event, object: { crypto_version: 1, aad_version: 1, nonce: new Uint8Array(24), ciphertext } }
}

const pulled = (overrides: Record<string, unknown> = {}) => ({
  protocol_version: 1, encrypted_sync_version: 1, next_cursor: 1, has_more: false,
  items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: {
    crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA',
  } }],
  ...overrides,
})

const HEAVY_BOUNDARY_TIMEOUT = 30_000

// Canonical unpadded Base64URL for a zero-filled byte string. Avoiding the
// byte-by-byte fixture encoder keeps the boundary test focused on pull parsing.
function zeroBase64Url(byteLength: number): string {
  const remainder = byteLength % 3
  return 'A'.repeat(Math.floor(byteLength / 3) * 4 + (remainder === 0 ? 0 : remainder + 1))
}

async function expectRejectedPull(response: unknown, since = 0): Promise<void> {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify(response), { status: 200 }))
  await expect(encryptedSyncApi.pull('token', event.event_id, since)).rejects.toThrow(TypeError)
  fetchMock.mockRestore()
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
    const wireEvent = JSON.parse(body).items[0].event
    expect(Object.keys(wireEvent).sort()).toEqual([
      'event_id', 'project_id', 'entity_id', 'entity_type', 'operation', 'revision', 'updated_at', 'deleted_at',
    ].sort())
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

  it('rejects unexpected event fields before protected plaintext can reach the network', () => {
    const protectedContent = 'C15_PROTECTED_PLAINTEXT_MARKER'
    const protectedTitle = 'C15_PROTECTED_TITLE_MARKER'
    const hostileEvent = { ...event, content: protectedContent, title: protectedTitle } as SyncEventEnvelope
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    expect(() => encryptedSyncApi.push('token', {
      protocol_version: 1,
      encrypted_sync_version: 1,
      device_id: event.event_id,
      items: [{ ...item(new Uint8Array(16)), event: hostileEvent }],
    })).toThrow(TypeError)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain(protectedContent)
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain(protectedTitle)
    fetchMock.mockRestore()
  })

  it('strictly validates complete C9 pull metadata and pagination invariants', async () => {
    await expectRejectedPull(pulled({ protocol_version: 2 }))
    await expectRejectedPull(pulled({ encrypted_sync_version: 2 }))
    await expectRejectedPull(pulled({ items: [{ ...pulled().items[0], event: { ...event, event_id: 'not-a-uuid', device_id: event.event_id, server_sequence: 1 } }] }))
    await expectRejectedPull(pulled({ items: [{ ...pulled().items[0], event: { ...event, device_id: event.event_id, server_sequence: 1, updated_at: '2026-02-30T00:00:00Z' } }] }))
    await expectRejectedPull(pulled({ items: [{ ...pulled().items[0], event: { ...event, device_id: event.event_id, server_sequence: 1, updated_at: '2026-09-21T00:00:00.1234567Z' } }] }))
    await expectRejectedPull(pulled({ items: [{ ...pulled().items[0], event: { ...event, device_id: event.event_id, server_sequence: 1, operation: 'delete', deleted_at: null } }] }))
    await expectRejectedPull(pulled({ next_cursor: 2 }))
    await expectRejectedPull(pulled({ next_cursor: 1.5 }))
    await expectRejectedPull(pulled({ has_more: 'false' }))
    await expectRejectedPull(pulled({ items: [
      ...pulled().items,
      { event: { ...event, device_id: event.event_id, server_sequence: 2 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } },
    ], next_cursor: 2 }))
    await expectRejectedPull(pulled({ items: [
      ...pulled().items,
      { event: { ...event, event_id: '123e4567-e89b-42d3-a456-426614174001', device_id: event.event_id, server_sequence: 1 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } },
    ] }))
    await expectRejectedPull(pulled({ items: [
      { event: { ...event, device_id: event.event_id, server_sequence: 2 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } },
      { event: { ...event, event_id: '123e4567-e89b-42d3-a456-426614174001', device_id: event.event_id, server_sequence: 1 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } },
    ], next_cursor: 1 }))
    await expectRejectedPull(pulled({ items: [], next_cursor: 1, has_more: true }))
  })

  it('preserves unknown entities as opaque data but rejects malformed or absent Note objects', async () => {
    const unknown = pulled({ items: [{ event: { ...event, entity_type: 'future_entity', device_id: event.event_id, server_sequence: 1 }, object: null }] })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify(unknown), { status: 200 }))
    await expect(encryptedSyncApi.pull('token', event.event_id, 0)).resolves.toMatchObject({ items: [{ event: { entity_type: 'future_entity' }, object: null }] })
    fetchMock.mockRestore()
    await expectRejectedPull(pulled({ items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: null }] }))
    await expectRejectedPull(pulled({ items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' } }] }))
    await expectRejectedPull(pulled({ items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: '*' } }] }))
  })

  it('bounds the HTTP body before JSON materialization', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('{}', {
      status: 200, headers: { 'Content-Length': '33554433' },
    }))
    await expect(encryptedSyncApi.pull('token', event.event_id, 0)).rejects.toBeInstanceOf(ApiResponseTooLargeError)
    fetchMock.mockRestore()
  })

  it('rejects a decoded pull object over the exact ciphertext limit', async () => {
    const oversized = zeroBase64Url(MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1)
    await expectRejectedPull(pulled({ items: [{ event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: {
      crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: oversized,
    } }] }))
  }, HEAVY_BOUNDARY_TIMEOUT)

  it('rejects a decoded pull batch over the exact aggregate ciphertext limit', async () => {
    const maximum = zeroBase64Url(MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES)
    await expectRejectedPull(pulled({ items: [
      { event: { ...event, device_id: event.event_id, server_sequence: 1 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: maximum } },
      { event: { ...event, event_id: '123e4567-e89b-42d3-a456-426614174001', device_id: event.event_id, server_sequence: 2 }, object: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: maximum } },
    ], next_cursor: 2 }))
  }, HEAVY_BOUNDARY_TIMEOUT)
})
