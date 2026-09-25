import { beforeEach, describe, expect, it, vi } from 'vitest'
import { invoke } from '@tauri-apps/api/core'
import { SQLiteNoteSyncResolutionRepository } from './noteSyncResolutionRepository'

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))
const mockedInvoke = vi.mocked(invoke)

describe('SQLite Note resolution sealing repository', () => {
  beforeEach(() => mockedInvoke.mockReset())

  it('passes the complete durable CAS scope and opaque envelope to Rust', async () => {
    mockedInvoke.mockResolvedValue('sealed')
    const repository = new SQLiteNoteSyncResolutionRepository()
    await expect(repository.commit({
      eventId: '123e4567-e89b-42d3-a456-426614174100', accountId: 'account',
      canonicalUserId: '123e4567-e89b-42d3-a456-426614174001',
      deviceId: '123e4567-e89b-42d3-a456-426614174002', projectId: 'project', entityId: 'note',
      canonicalPayload: 'e30', envelope: { crypto_version: 1, aad_version: 1,
        nonce: new Uint8Array(24), ciphertext: new Uint8Array(16) },
    })).resolves.toBe('sealed')
    expect(mockedInvoke).toHaveBeenCalledWith('commit_sealed_note_resolution_event', { command: {
      event_id: '123e4567-e89b-42d3-a456-426614174100', account_id: 'account',
      canonical_user_id: '123e4567-e89b-42d3-a456-426614174001',
      device_id: '123e4567-e89b-42d3-a456-426614174002', project_id: 'project', entity_id: 'note',
      expected_canonical_payload: 'e30', envelope: { crypto_version: 1, aad_version: 1,
        nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' },
    } })
  })
})
