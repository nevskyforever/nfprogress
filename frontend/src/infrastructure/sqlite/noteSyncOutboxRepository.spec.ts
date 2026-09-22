import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import type { SealedNoteSyncOutboxItem } from '@/cloud/noteSyncOutbox'
import ipcContractFixture from './noteSyncIpcContract.v1.json'
import { SQLiteNoteSyncOutboxRepository } from './noteSyncOutboxRepository'

const item: SealedNoteSyncOutboxItem = {
  event_id: '123e4567-e89b-42d3-a456-426614174004',
  account_id: 'account-1',
  device_id: '123e4567-e89b-42d3-a456-426614174001',
  project_id: 'deleted-project',
  entity_id: 'note-3',
  entity_type: 'note',
  operation: 'delete',
  revision: 2,
  parent_event_id: '123e4567-e89b-42d3-a456-426614174003',
  updated_at: '2026-09-22T00:00:02.000000Z',
  deleted_at: '2026-09-22T00:00:02.000000Z',
  local_ordinal: 3,
  envelope: {
    crypto_version: 1,
    aad_version: 1,
    nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA',
  },
}
const contract = ipcContractFixture as { list_sealed_note_sync_outbox: SealedNoteSyncOutboxItem[] }

describe('SQLiteNoteSyncOutboxRepository', () => {
  const repository = new SQLiteNoteSyncOutboxRepository()

  beforeEach(() => invoke.mockReset())

  it('uses the explicit account scope and preserves the opaque Rust DTO', async () => {
    expect(contract.list_sealed_note_sync_outbox).toEqual([item])
    invoke.mockResolvedValueOnce(contract.list_sealed_note_sync_outbox)
    await expect(repository.listSealed('account-1', 8)).resolves.toEqual([item])
    expect(invoke).toHaveBeenCalledWith('list_sealed_note_sync_outbox', {
      accountId: 'account-1', limit: 8,
    })
    expect(Object.keys(item).sort()).toEqual([
      'account_id', 'deleted_at', 'device_id', 'entity_id', 'entity_type', 'envelope',
      'event_id', 'local_ordinal', 'operation', 'parent_event_id', 'project_id', 'revision', 'updated_at',
    ])
    expect(Object.keys(item.envelope).sort()).toEqual([
      'aad_version', 'ciphertext', 'crypto_version', 'nonce',
    ])
  })

  it('rejects invalid bounds and account scopes before IPC', () => {
    expect(() => repository.listSealed('', 1)).toThrow(TypeError)
    expect(() => repository.listSealed('account-1', 0)).toThrow(RangeError)
    expect(() => repository.listSealed('account-1', 201)).toThrow(RangeError)
    expect(invoke).not.toHaveBeenCalled()
  })

  it('forwards only the account-scoped server receipt command', async () => {
    const receipt = { event_id: item.event_id, server_sequence: 9, duplicate: true }
    invoke.mockResolvedValueOnce(['accepted'])
    await expect(repository.commitAccepted('account-1', item.device_id, [receipt])).resolves.toEqual(['accepted'])
    expect(invoke).toHaveBeenCalledWith('commit_note_sync_upload_acceptance', {
      command: { account_id: 'account-1', device_id: item.device_id, receipts: [receipt] },
    })
  })
})
