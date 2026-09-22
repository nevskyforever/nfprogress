import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { decodeBase64Url } from '@/api/base64url'
import type {
  CommitSealedNoteSyncEventResult,
  NoteSyncSealErrorCode,
  NoteSyncSealState,
  RecordNoteSyncSealFailureResult,
  UnsealedNoteSyncIntent,
} from '@/cloud/noteSyncIntent'
import ipcContractFixture from './noteSyncIpcContract.v1.json'
import { SQLiteNoteSyncIntentRepository } from './noteSyncIntentRepository'

interface NoteSyncIpcContractFixture {
  list_unsealed_note_sync_intents: UnsealedNoteSyncIntent[]
  record_note_sync_seal_failure: {
    command: {
      event_id: string
      expected_mutation_generation: number
      error_code: NoteSyncSealErrorCode
    }
  }
  commit_sealed_note_sync_event: {
    command: {
      event_id: string
      expected_mutation_generation: number
      envelope: {
        crypto_version: 1
        aad_version: 1
        nonce: string
        ciphertext: string
      }
    }
  }
  operation_values: UnsealedNoteSyncIntent['operation'][]
  seal_state_values: NoteSyncSealState[]
  error_code_values: NoteSyncSealErrorCode[]
  record_failure_result_values: RecordNoteSyncSealFailureResult[]
  commit_result_values: CommitSealedNoteSyncEventResult[]
}

const contract = ipcContractFixture as NoteSyncIpcContractFixture

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

  it('matches the shared fixture serialized by the real Rust serde DTOs', async () => {
    expect(contract.operation_values).toEqual(['upsert', 'delete'])
    expect(contract.seal_state_values).toEqual([
      'pending', 'retryable_error', 'blocked', 'invariant_error',
    ])
    expect(contract.error_code_values).toEqual([
      'key_unavailable',
      'payload_too_large',
      'encrypted_sync_object_too_large',
      'dependency_not_synced',
      'unsupported_content_format',
      'invalid_note_payload',
      'crypto_context_invalid',
      'invalid_sync_metadata',
      'invalid_envelope',
      'metadata_mismatch',
      'runtime_unavailable',
    ])
    expect(contract.record_failure_result_values).toEqual([
      'recorded', 'stale_generation', 'already_sealed',
    ])
    expect(contract.commit_result_values).toEqual([
      'sealed', 'stale_generation', 'already_sealed',
    ])

    const [upsert, deleted] = contract.list_unsealed_note_sync_intents
    expect(Object.keys(upsert!).sort()).toEqual([
      'account_id', 'deleted_at', 'device_id', 'entity_id', 'entity_type', 'event_id',
      'last_error_code', 'local_ordinal', 'mutation_generation', 'next_attempt_at',
      'operation', 'parent_event_id', 'project_id', 'revision', 'seal_attempt_count',
      'seal_state', 'snapshot_json', 'updated_at',
    ])
    expect(upsert).toMatchObject({
      operation: 'upsert',
      parent_event_id: null,
      deleted_at: null,
      seal_state: 'pending',
      last_error_code: null,
      next_attempt_at: null,
      mutation_generation: Number.MAX_SAFE_INTEGER,
    })
    expect(deleted).toMatchObject({
      operation: 'delete',
      seal_state: 'retryable_error',
      mutation_generation: 7,
      last_error_code: 'runtime_unavailable',
    })
    expect(Number.isSafeInteger(upsert!.mutation_generation)).toBe(true)

    invoke.mockResolvedValueOnce(contract.list_unsealed_note_sync_intents)
    await expect(repository.list(2)).resolves.toEqual(contract.list_unsealed_note_sync_intents)
    expect(invoke).toHaveBeenLastCalledWith('list_unsealed_note_sync_intents', { limit: 2 })

    const failure = contract.record_note_sync_seal_failure.command
    invoke.mockResolvedValueOnce('recorded')
    await expect(repository.recordSealFailure({
      eventId: failure.event_id,
      expectedMutationGeneration: failure.expected_mutation_generation,
      errorCode: failure.error_code,
    })).resolves.toBe('recorded')
    expect(invoke).toHaveBeenLastCalledWith('record_note_sync_seal_failure', {
      command: failure,
    })

    const commit = contract.commit_sealed_note_sync_event.command
    invoke.mockResolvedValueOnce('sealed')
    await expect(repository.commitSealedEvent({
      eventId: commit.event_id,
      expectedMutationGeneration: commit.expected_mutation_generation,
      envelope: {
        crypto_version: commit.envelope.crypto_version,
        aad_version: commit.envelope.aad_version,
        nonce: decodeBase64Url(commit.envelope.nonce),
        ciphertext: decodeBase64Url(commit.envelope.ciphertext),
      },
    })).resolves.toBe('sealed')
    expect(invoke).toHaveBeenLastCalledWith('commit_sealed_note_sync_event', {
      command: commit,
    })
    expect(decodeBase64Url(commit.envelope.nonce)).toHaveLength(24)
    expect(decodeBase64Url(commit.envelope.ciphertext)).toHaveLength(16)
  })

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
