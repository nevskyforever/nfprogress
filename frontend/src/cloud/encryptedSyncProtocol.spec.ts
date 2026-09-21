// @vitest-environment node
import { beforeAll, describe, expect, it } from 'vitest'
import { encryptObjectBytes, generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import type { SyncEventEnvelope } from './syncProtocol'
import {
  createNoteSyncPlaintext,
  openNoteSyncEvent,
  sealNoteSyncEvent,
  validateEncryptedSyncCryptoContext,
} from './encryptedSyncProtocol'
import { encodeNoteSyncPlaintext, type NoteSyncRecord } from './noteSyncCodec'

const canonicalTime = '2026-09-21T00:00:00.000000Z'
const eventId = '123e4567-e89b-42d3-a456-426614174000'

function event(overrides: Partial<SyncEventEnvelope> = {}): SyncEventEnvelope {
  return { event_id: eventId, project_id: 'project-1', entity_id: 'note-1', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: canonicalTime, deleted_at: null, ...overrides }
}

function note(overrides: Partial<NoteSyncRecord> = {}): NoteSyncRecord {
  return {
    id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project', source_map_id: null,
    source_node_id: null, content_format: 'html', title: 'secret-title', content: '<p>secret-content</p>',
    checklist: [], color: 'default', pinned: false, archived: false, sort_order: 0, tags: [],
    created_at: canonicalTime, updated_at: canonicalTime, metadata: {}, ...overrides,
  }
}

describe('C15 encrypted Note protocol', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('canonicalizes outbound UUID/timestamps and accepts equivalent uppercase C9 metadata', async () => {
    const uppercase = event({ event_id: eventId.toUpperCase(), updated_at: '2026-09-21T03:00:00+03:00' })
    const sealed = await sealNoteSyncEvent(amk, 'user-1', uppercase, null, note())
    expect(sealed.event.event_id).toBe(eventId)
    expect(sealed.event.updated_at).toBe(canonicalTime)
    await expect(openNoteSyncEvent(amk, 'user-1', uppercase, sealed.object)).resolves.toMatchObject({
      header: { event_id: eventId, updated_at: canonicalTime }, mutation: 'create',
    })
  })

  it('enforces revision parent rules before encryption', () => {
    expect(() => createNoteSyncPlaintext(event(), eventId, note())).toThrowError(expect.objectContaining({ code: 'invalid_sync_metadata' }))
    expect(() => createNoteSyncPlaintext(event({ revision: 2 }), null, note())).toThrowError(expect.objectContaining({ code: 'invalid_sync_metadata' }))
    expect(() => createNoteSyncPlaintext(event({ revision: 2 }), eventId, note())).toThrowError(expect.objectContaining({ code: 'invalid_sync_metadata' }))
    expect(createNoteSyncPlaintext(event({ revision: 2 }), '123e4567-e89b-42d3-a456-426614174001', note()).plaintext.mutation).toBe('update')
  })

  it('checks C11 context limits as UTF-8 bytes and defers unsynchronized dependencies', async () => {
    expect(() => validateEncryptedSyncCryptoContext({ userId: 'é'.repeat(256), projectId: 'p', entityId: 'n', entityType: 'note' })).not.toThrow()
    expect(() => validateEncryptedSyncCryptoContext({ userId: 'é'.repeat(257), projectId: 'p', entityId: 'n', entityType: 'note' })).toThrowError(expect.objectContaining({ code: 'crypto_context_invalid' }))
    await expect(sealNoteSyncEvent(amk, 'user-1', event(), null, note({ stage_id: 'stage-1' }))).rejects.toMatchObject({ code: 'dependency_not_synced' })
    await expect(sealNoteSyncEvent(amk, 'user-1', event(), null, note({ source_type: 'mindmap', source_map_id: 'map', source_node_id: 'node' }))).rejects.toMatchObject({ code: 'dependency_not_synced' })
  })

  it('fails closed on metadata mismatch, tampering, and malformed plaintext', async () => {
    const sealed = await sealNoteSyncEvent(amk, 'user-1', event(), null, note())
    await expect(openNoteSyncEvent(amk, 'user-1', event({ revision: 2 }), sealed.object)).rejects.toMatchObject({ code: 'metadata_mismatch' })
    const tampered = { ...sealed.object, ciphertext: new Uint8Array(sealed.object.ciphertext) }
    tampered.ciphertext[0]! ^= 1
    await expect(openNoteSyncEvent(amk, 'user-1', event(), tampered)).rejects.toMatchObject({ code: 'decrypt_failed' })

    const malformed = await encryptObjectBytes(amk, { userId: 'user-1', projectId: 'project-1', entityId: 'note-1', entityType: 'note' }, new TextEncoder().encode('{}'))
    await expect(openNoteSyncEvent(amk, 'user-1', event(), malformed)).rejects.toMatchObject({ code: 'invalid_envelope' })
  })

  it('returns safe errors without protected plaintext', async () => {
    const { plaintext } = createNoteSyncPlaintext(event(), null, note())
    const wrongContextEnvelope = await encryptObjectBytes(amk, { userId: 'other', projectId: 'project-1', entityId: 'note-1', entityType: 'note' }, encodeNoteSyncPlaintext(plaintext))
    try {
      await openNoteSyncEvent(amk, 'user-1', event(), wrongContextEnvelope)
      throw new Error('expected failure')
    } catch (error) {
      const message = (error as Error).message
      expect(message).not.toContain('secret-title')
      expect(message).not.toContain('secret-content')
    }
  })
})
