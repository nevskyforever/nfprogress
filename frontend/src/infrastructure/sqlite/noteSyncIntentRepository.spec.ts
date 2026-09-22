import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { decodeBase64Url } from '@/api/base64url'
import type { UnsealedNoteSyncIntent } from '@/cloud/noteSyncIntent'
import { SQLiteNoteSyncIntentRepository } from './noteSyncIntentRepository'

const intent: UnsealedNoteSyncIntent = {
  event_id: '123e4567-e89b-42d3-a456-426614174000',
  account_id: 'account-1',
  device_id: '123e4567-e89b-42d3-a456-426614174001',
  project_id: 'project-1',
  entity_id: 'note-1',
  entity_type: 'note',
  operation: 'upsert',
  revision: 1,
  parent_event_id: null,
  updated_at: '2026-09-22T00:00:00.000000Z',
  deleted_at: null,
  local_ordinal: 1,
  mutation_generation: 3,
  snapshot_json: '{"id":"note-1"}',
  seal_state: 'pending',
  seal_attempt_count: 0,
  last_error_code: null,
  next_attempt_at: null,
}

describe('SQLiteNoteSyncIntentRepository', () => {
  const repository = new SQLiteNoteSyncIntentRepository()

  beforeEach(() => invoke.mockReset())

  it('maps the bounded listing command and preserves the snake_case Rust DTO', async () => {
    invoke.mockResolvedValueOnce([intent])

    await expect(repository.list(8)).resolves.toEqual([intent])
    expect(invoke).toHaveBeenCalledWith('list_unsealed_note_sync_intents', { limit: 8 })
    expect(() => repository.list(0)).toThrow(RangeError)
    expect(() => repository.list(201)).toThrow(RangeError)
    expect(invoke).toHaveBeenCalledTimes(1)
  })

  it.each(['recorded', 'stale_generation', 'already_sealed'] as const)(
    'maps failure CAS result %s without changing generation',
    async result => {
      invoke.mockResolvedValueOnce(result)

      await expect(repository.recordSealFailure({
        eventId: intent.event_id,
        expectedMutationGeneration: 3,
        errorCode: 'key_unavailable',
      })).resolves.toBe(result)
      expect(invoke).toHaveBeenCalledWith('record_note_sync_seal_failure', {
        command: {
          event_id: intent.event_id,
          expected_mutation_generation: 3,
          error_code: 'key_unavailable',
        },
      })
    },
  )

  it.each(['sealed', 'stale_generation', 'already_sealed'] as const)(
    'encodes a canonical base64url envelope for commit result %s',
    async result => {
      invoke.mockResolvedValueOnce(result)
      const nonce = Uint8Array.from({ length: 24 }, (_, index) => index)
      const ciphertext = Uint8Array.from({ length: 16 }, (_, index) => 0xfb - index)

      await expect(repository.commitSealedEvent({
        eventId: intent.event_id,
        expectedMutationGeneration: 3,
        envelope: { crypto_version: 1, aad_version: 1, nonce, ciphertext },
      })).resolves.toBe(result)

      const call = invoke.mock.calls[0] as [string, {
        command: { envelope: { nonce: string; ciphertext: string } }
      }]
      expect(call[0]).toBe('commit_sealed_note_sync_event')
      expect(call[1]).toMatchObject({
        command: {
          event_id: intent.event_id,
          expected_mutation_generation: 3,
          envelope: { crypto_version: 1, aad_version: 1 },
        },
      })
      expect(call[1].command.envelope.nonce).not.toContain('=')
      expect(call[1].command.envelope.ciphertext).not.toContain('=')
      expect(decodeBase64Url(call[1].command.envelope.nonce)).toEqual(nonce)
      expect(decodeBase64Url(call[1].command.envelope.ciphertext)).toEqual(ciphertext)
      expect(Array.isArray(call[1].command.envelope.ciphertext)).toBe(false)
    },
  )
})
