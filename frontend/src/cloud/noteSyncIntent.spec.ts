// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import {
  asAccountMasterKey,
  generateAccountMasterKey,
  type AccountMasterKey,
  type ObjectCryptoEnvelope,
} from '@/crypto'
import { MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES } from '@/api/encryptedSync'
import { createNoteSyncPlaintext, openNoteSyncEvent } from './encryptedSyncProtocol'
import {
  MAX_NOTE_SYNC_PLAINTEXT_BYTES,
  encodeNoteSyncPlaintext,
  type NoteSyncRecord,
} from './noteSyncCodec'
import {
  sealPendingNoteSyncIntents,
  type NoteSyncIntentRepository,
  type UnlockedAccountMasterKeyProvider,
  type UnsealedNoteSyncIntent,
} from './noteSyncIntent'

const eventId = '123e4567-e89b-42d3-a456-426614174000'
const deviceId = '123e4567-e89b-42d3-a456-426614174001'
const canonicalTime = '2026-09-22T00:00:00.000000Z'
const testKey = asAccountMasterKey(new Uint8Array(32).fill(7))

function snapshot(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project',
    source_map_id: null, source_node_id: null, content_format: 'html', title: 'Title',
    content: '<p>Secret</p>', checklist: [], color: 'default', pinned: false, archived: false,
    sort_order: 0, tags: [], created_at: canonicalTime, updated_at: canonicalTime,
    revision: 41, metadata: {}, ...overrides,
  }
}

function tombstone(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'note-1', project_id: 'project-1', stage_id: null, source_type: 'project',
    source_map_id: null, source_node_id: null, content_format: 'html', deleted_at: canonicalTime,
    ...overrides,
  }
}

function intent(overrides: Partial<UnsealedNoteSyncIntent> = {}): UnsealedNoteSyncIntent {
  return {
    event_id: eventId,
    account_id: 'account-scope-1',
    device_id: deviceId,
    project_id: 'project-1',
    entity_id: 'note-1',
    entity_type: 'note',
    operation: 'upsert',
    revision: 1,
    parent_event_id: null,
    updated_at: canonicalTime,
    deleted_at: null,
    local_ordinal: 1,
    mutation_generation: 3,
    snapshot_json: JSON.stringify(snapshot()),
    seal_state: 'pending',
    seal_attempt_count: 0,
    last_error_code: null,
    next_attempt_at: null,
    ...overrides,
  }
}

function repository(
  intents: UnsealedNoteSyncIntent[],
  overrides: Partial<NoteSyncIntentRepository> = {},
): NoteSyncIntentRepository {
  return {
    list: vi.fn(async limit => intents.slice(0, limit)),
    recordSealFailure: failureMock(async () => 'recorded'),
    commitSealedEvent: commitMock(async () => 'sealed'),
    ...overrides,
  }
}

function failureMock(implementation: NoteSyncIntentRepository['recordSealFailure']) {
  return vi.fn(implementation)
}

function commitMock(implementation: NoteSyncIntentRepository['commitSealedEvent']) {
  return vi.fn(implementation)
}

function keyMock(implementation: UnlockedAccountMasterKeyProvider['getUnlockedAccountMasterKey']) {
  return vi.fn(implementation)
}

function provider(
  masterKey: AccountMasterKey = testKey,
  userId = 'canonical-user-id',
): UnlockedAccountMasterKeyProvider {
  return {
    getUnlockedAccountMasterKey: keyMock(async accountId => ({
      status: 'available',
      accountId,
      userId,
      masterKey,
    })),
  }
}

function eventFrom(value: UnsealedNoteSyncIntent) {
  return {
    event_id: value.event_id,
    project_id: value.project_id,
    entity_id: value.entity_id,
    entity_type: value.entity_type,
    operation: value.operation,
    revision: value.revision,
    updated_at: value.updated_at,
    deleted_at: value.deleted_at,
  }
}

describe('durable Note sealing orchestration', () => {
  it('seals an ordinary upsert with real C11 crypto and excludes local revision', async () => {
    const source = intent()
    let envelope: ObjectCryptoEnvelope | undefined
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => {
        envelope = input.envelope
        expect(input.eventId).toBe(source.event_id)
        expect(input.expectedMutationGeneration).toBe(3)
        return 'sealed'
      }),
    })
    const masterKey = await generateAccountMasterKey()

    const result = await sealPendingNoteSyncIntents(store, provider(masterKey, 'user-id-from-provider'))

    expect(result.results).toEqual([{
      event_id: source.event_id, mutation_generation: 3, status: 'sealed',
    }])
    expect(envelope).toBeDefined()
    const opened = await openNoteSyncEvent(
      masterKey,
      'user-id-from-provider',
      eventFrom(source),
      envelope!,
    )
    expect(opened.note).toMatchObject({ id: 'note-1', content: '<p>Secret</p>' })
    expect(opened.note).not.toHaveProperty('revision')
  })

  it('seals a delete tombstone after local project state is gone', async () => {
    const source = intent({
      operation: 'delete',
      updated_at: '2026-09-22T03:00:00+03:00',
      deleted_at: canonicalTime,
      snapshot_json: JSON.stringify(tombstone()),
    })
    let envelope: ObjectCryptoEnvelope | undefined
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => { envelope = input.envelope; return 'sealed' }),
    })

    await expect(sealPendingNoteSyncIntents(store, provider())).resolves.toMatchObject({
      results: [{ status: 'sealed' }],
    })
    const opened = await openNoteSyncEvent(testKey, 'canonical-user-id', eventFrom(source), envelope!)
    expect(opened).toMatchObject({ mutation: 'delete', note: { deleted_at: canonicalTime } })
  })

  it('normalizes stored Note and event timestamps before encryption', async () => {
    const offsetTime = '2026-09-22T03:00:00+03:00'
    const source = intent({
      updated_at: offsetTime,
      snapshot_json: JSON.stringify(snapshot({
        created_at: offsetTime,
        updated_at: offsetTime,
      })),
    })
    let envelope: ObjectCryptoEnvelope | undefined
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => { envelope = input.envelope; return 'sealed' }),
    })

    await sealPendingNoteSyncIntents(store, provider())

    const opened = await openNoteSyncEvent(testKey, 'canonical-user-id', eventFrom(source), envelope!)
    expect(opened.header.updated_at).toBe(canonicalTime)
    expect('updated_at' in opened.note && opened.note.updated_at).toBe(canonicalTime)
    expect('created_at' in opened.note && opened.note.created_at).toBe(canonicalTime)
  })

  it('records malformed snapshots without requesting an AMK', async () => {
    const source = intent({ snapshot_json: '{not-json' })
    const store = repository([source])
    const keys = provider()

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'invalid_note_payload',
    })
    expect(keys.getUnlockedAccountMasterKey).not.toHaveBeenCalled()
    expect(store.recordSealFailure).toHaveBeenCalledWith({
      eventId: source.event_id,
      expectedMutationGeneration: 3,
      errorCode: 'invalid_note_payload',
    })
  })

  it('records snapshot/event identity mismatch before encryption', async () => {
    const source = intent({ snapshot_json: JSON.stringify(snapshot({ id: 'other-note' })) })
    const store = repository([source])
    const keys = provider()

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'metadata_mismatch',
    })
    expect(keys.getUnlockedAccountMasterKey).not.toHaveBeenCalled()
  })

  it.each([
    ['stage', snapshot({ stage_id: 'stage-1' })],
    ['mind-map', snapshot({ source_type: 'mindmap', source_map_id: 'map-1', source_node_id: 'node-1' })],
  ])('blocks unsupported %s dependencies before requesting a key', async (_kind, value) => {
    const source = intent({ snapshot_json: JSON.stringify(value) })
    const store = repository([source])
    const keys = provider()

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'dependency_not_synced',
    })
    expect(keys.getUnlockedAccountMasterKey).not.toHaveBeenCalled()
  })

  it('classifies unsupported content only after dependency eligibility passes', async () => {
    const source = intent({ snapshot_json: JSON.stringify(snapshot({ content_format: 'plain' })) })
    const store = repository([source])
    const keys = provider()

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'unsupported_content_format',
    })
    expect(keys.getUnlockedAccountMasterKey).not.toHaveBeenCalled()
  })

  it('records a missing unlocked AMK and never attempts a commit', async () => {
    const source = intent()
    const store = repository([source])
    const keys: UnlockedAccountMasterKeyProvider = {
      getUnlockedAccountMasterKey: keyMock(async () => ({ status: 'key_unavailable' })),
    }

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'key_unavailable',
    })
    expect(store.commitSealedEvent).not.toHaveBeenCalled()
  })

  it('uses the provider-confirmed crypto userId without assuming it equals account_id', async () => {
    const source = intent({ account_id: 'local-account-scope' })
    let envelope: ObjectCryptoEnvelope | undefined
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => { envelope = input.envelope; return 'sealed' }),
    })
    const keys = provider(testKey, 'backend-user-uuid')

    await sealPendingNoteSyncIntents(store, keys)

    expect(keys.getUnlockedAccountMasterKey).toHaveBeenCalledWith('local-account-scope')
    await expect(openNoteSyncEvent(
      testKey,
      'backend-user-uuid',
      eventFrom(source),
      envelope!,
    )).resolves.toMatchObject({ mutation: 'create' })
  })

  it('rejects an AMK provider response bound to another account', async () => {
    const source = intent()
    const store = repository([source])
    const keys: UnlockedAccountMasterKeyProvider = {
      getUnlockedAccountMasterKey: keyMock(async () => ({
        status: 'available', accountId: 'other-account', userId: 'user', masterKey: testKey,
      })),
    }

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'crypto_context_invalid',
    })
    expect(store.commitSealedEvent).not.toHaveBeenCalled()
  })

  it('records the existing Note plaintext payload limit', async () => {
    const source = intent({
      snapshot_json: JSON.stringify(snapshot({ content: 'x'.repeat(MAX_NOTE_SYNC_PLAINTEXT_BYTES) })),
    })
    const store = repository([source])

    const result = await sealPendingNoteSyncIntents(store, provider())

    expect(result.results[0]).toMatchObject({
      status: 'failure_recorded', error_code: 'payload_too_large',
    })
    expect(store.commitSealedEvent).not.toHaveBeenCalled()
  })

  it('accepts the exact encrypted envelope size boundary using real C11 crypto', async () => {
    const source = intent()
    const base = snapshot({ content: '' })
    delete base.revision
    const note = base as unknown as NoteSyncRecord
    const plaintext = createNoteSyncPlaintext(eventFrom(source), null, note).plaintext
    const overhead = encodeNoteSyncPlaintext(plaintext).byteLength
    source.snapshot_json = JSON.stringify(snapshot({
      content: 'x'.repeat(MAX_NOTE_SYNC_PLAINTEXT_BYTES - overhead),
    }))
    let ciphertextLength = 0
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => {
        ciphertextLength = input.envelope.ciphertext.byteLength
        return 'sealed'
      }),
    })

    const result = await sealPendingNoteSyncIntents(store, provider())

    expect(result.results[0]?.status).toBe('sealed')
    expect(ciphertextLength).toBe(MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES)
  })

  it('drops a stale encrypted result after a concurrent generation change', async () => {
    const source = intent({ mutation_generation: 3 })
    let currentGeneration = 3
    const store = repository([source], {
      commitSealedEvent: commitMock(async input => (
        input.expectedMutationGeneration === currentGeneration ? 'sealed' : 'stale_generation'
      )),
    })

    const pass = sealPendingNoteSyncIntents(store, provider())
    currentGeneration = 4
    const result = await pass

    expect(result.results[0]?.status).toBe('stale_generation')
    expect(store.commitSealedEvent).toHaveBeenCalledTimes(1)
    expect(store.commitSealedEvent).toHaveBeenCalledWith(expect.objectContaining({
      eventId: source.event_id,
      expectedMutationGeneration: 3,
    }))
  })

  it('does not claim a stale failure result was recorded', async () => {
    const source = intent({ snapshot_json: 'null' })
    const store = repository([source], {
      recordSealFailure: failureMock(async () => 'stale_generation'),
    })

    const result = await sealPendingNoteSyncIntents(store, provider())

    expect(result.results[0]).toMatchObject({
      status: 'failure_stale_generation', error_code: 'invalid_note_payload',
    })
  })

  it.each(['sealed', 'already_sealed'] as const)('handles successful CAS result %s once', async commitResult => {
    const source = intent()
    const store = repository([source], {
      commitSealedEvent: commitMock(async () => commitResult),
    })

    const result = await sealPendingNoteSyncIntents(store, provider())

    expect(result.results[0]?.status).toBe(commitResult)
    expect(store.commitSealedEvent).toHaveBeenCalledTimes(1)
  })

  it('reports failure persistence errors without claiming durability', async () => {
    const source = intent({ snapshot_json: '[]' })
    const store = repository([source], {
      recordSealFailure: failureMock(async () => { throw new Error('database unavailable') }),
    })

    const result = await sealPendingNoteSyncIntents(store, provider())

    expect(result.results[0]).toMatchObject({
      status: 'failure_record_failed', error_code: 'invalid_note_payload',
    })
  })

  it('does not repeatedly process blocked intents without explicit permission', async () => {
    const source = intent({ seal_state: 'blocked', last_error_code: 'key_unavailable' })
    const store = repository([source])
    const keys = provider()

    const first = await sealPendingNoteSyncIntents(store, keys)
    const second = await sealPendingNoteSyncIntents(store, keys)

    expect(first.results[0]?.status).toBe('blocked_skipped')
    expect(second.results[0]?.status).toBe('blocked_skipped')
    expect(keys.getUnlockedAccountMasterKey).not.toHaveBeenCalled()
    expect(store.recordSealFailure).not.toHaveBeenCalled()
    expect(store.commitSealedEvent).not.toHaveBeenCalled()

    await sealPendingNoteSyncIntents(store, keys, { retryBlocked: true })
    expect(keys.getUnlockedAccountMasterKey).toHaveBeenCalledTimes(1)
  })

  it('performs one bounded pass and remains restart-compatible', async () => {
    const queued = [
      intent(),
      intent({
        event_id: '123e4567-e89b-42d3-a456-426614174002',
        entity_id: 'note-2',
        local_ordinal: 2,
        snapshot_json: JSON.stringify(snapshot({ id: 'note-2' })),
      }),
      intent({
        event_id: '123e4567-e89b-42d3-a456-426614174003',
        entity_id: 'note-3',
        local_ordinal: 3,
        snapshot_json: JSON.stringify(snapshot({ id: 'note-3' })),
      }),
    ]
    const list = vi.fn(async (limit: number) => queued.slice(0, limit))
    const store = repository([], {
      list,
      commitSealedEvent: commitMock(async input => {
        const index = queued.findIndex(item => item.event_id === input.eventId)
        if (index >= 0) queued.splice(index, 1)
        return 'sealed'
      }),
    })

    const first = await sealPendingNoteSyncIntents(store, provider(), { limit: 2 })
    const second = await sealPendingNoteSyncIntents(store, provider(), { limit: 2 })

    expect(first.listed).toBe(2)
    expect(second.listed).toBe(1)
    expect(list).toHaveBeenNthCalledWith(1, 2, false)
    expect(list).toHaveBeenNthCalledWith(2, 2, false)
    expect(store.commitSealedEvent).toHaveBeenCalledTimes(3)
    expect(queued).toHaveLength(0)
  })

  it('preserves an intent and returns only safe diagnostics for an unknown error', async () => {
    const source = intent()
    const store = repository([source])
    const keys: UnlockedAccountMasterKeyProvider = {
      getUnlockedAccountMasterKey: keyMock(async () => {
        throw new Error('SECRET_SNAPSHOT_OR_KEY_MATERIAL')
      }),
    }

    const result = await sealPendingNoteSyncIntents(store, keys)

    expect(result.results[0]?.status).toBe('unclassified_error')
    expect(JSON.stringify(result)).not.toContain('SECRET_SNAPSHOT_OR_KEY_MATERIAL')
    expect(store.recordSealFailure).not.toHaveBeenCalled()
    expect(store.commitSealedEvent).not.toHaveBeenCalled()
  })

  it('continues past eight unchanged unknown failures across processing passes', async () => {
    const queued = Array.from({ length: 10 }, (_, index) => intent({
      event_id: `123e4567-e89b-42d3-a456-${String(426614175000 + index).padStart(12, '0')}`,
      account_id: `account-scope-${index}`,
      entity_id: `note-${index}`,
      local_ordinal: index + 1,
      snapshot_json: JSON.stringify(snapshot({ id: `note-${index}` })),
    }))
    const list = vi.fn<NoteSyncIntentRepository['list']>()
      .mockResolvedValueOnce(queued.slice(0, 8))
      .mockResolvedValueOnce([...queued.slice(8), ...queued.slice(0, 6)])
    const store = repository([], { list })
    const getKey = keyMock(async accountId => {
      const index = Number(accountId.slice(accountId.lastIndexOf('-') + 1))
      if (index < 8) throw new Error('unknown runtime failure')
      return { status: 'available' as const, accountId, userId: 'canonical-user-id', masterKey: testKey }
    })
    const keys: UnlockedAccountMasterKeyProvider = {
      getUnlockedAccountMasterKey: getKey,
    }

    const first = await sealPendingNoteSyncIntents(store, keys)
    const second = await sealPendingNoteSyncIntents(store, keys)

    expect(first.results.every(result => result.status === 'unclassified_error')).toBe(true)
    expect(second.results.slice(0, 2).map(result => result.status)).toEqual(['sealed', 'sealed'])
    expect(second.results.slice(0, 2).map(result => result.event_id)).toEqual([
      queued[8]!.event_id,
      queued[9]!.event_id,
    ])
    expect(list).toHaveBeenNthCalledWith(1, 8, false)
    expect(list).toHaveBeenNthCalledWith(2, 8, false)
    expect(store.recordSealFailure).not.toHaveBeenCalled()
    expect(queued.every(item => item.seal_state === 'pending')).toBe(true)
  })

  it('reaches eligible work after more than 32 dependency blocks only in retry mode', async () => {
    const queued = Array.from({ length: 34 }, (_, index) => intent({
      event_id: `123e4567-e89b-42d3-a456-${String(426614176000 + index).padStart(12, '0')}`,
      entity_id: `note-${index}`,
      local_ordinal: index + 1,
      snapshot_json: JSON.stringify(snapshot({ id: `note-${index}`, stage_id: 'stage-1' })),
      seal_state: 'blocked',
      last_error_code: 'dependency_not_synced',
    }))
    const list = vi.fn<NoteSyncIntentRepository['list']>()
      .mockResolvedValueOnce(queued.slice(0, 32))
      .mockResolvedValueOnce([...queued.slice(32), ...queued.slice(0, 30)])
    const store = repository([], { list })

    const first = await sealPendingNoteSyncIntents(store, provider(), {
      limit: 32,
      retryBlocked: true,
    })
    const second = await sealPendingNoteSyncIntents(store, provider(), {
      limit: 32,
      retryBlocked: true,
    })

    expect(first.results).toHaveLength(32)
    expect(second.results.slice(0, 2)).toMatchObject([
      { event_id: queued[32]!.event_id, error_code: 'dependency_not_synced' },
      { event_id: queued[33]!.event_id, error_code: 'dependency_not_synced' },
    ])
    expect(list).toHaveBeenNthCalledWith(1, 32, true)
    expect(list).toHaveBeenNthCalledWith(2, 32, true)
  })
})
