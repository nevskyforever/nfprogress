import { beforeEach, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { SQLiteNoteSyncAckRepository } from './noteSyncAckRepository'

const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const USER = '123e4567-e89b-42d3-a456-426614174099'

describe('SQLite Note sync ACK repository', () => {
  beforeEach(() => invoke.mockReset())

  it('uses only typed prepare and conditional commit IPC commands', async () => {
    const repository = new SQLiteNoteSyncAckRepository()
    invoke.mockResolvedValueOnce({ current_ack_cursor: 2, candidate_cursor: 4 }).mockResolvedValueOnce('advanced')
    await expect(repository.prepare('local', DEVICE, USER)).resolves.toEqual({ current_ack_cursor: 2, candidate_cursor: 4 })
    await expect(repository.commit('local', DEVICE, USER, 2, 4)).resolves.toBe('advanced')
    expect(invoke).toHaveBeenNthCalledWith(1, 'prepare_note_sync_ack', {
      command: { account_id: 'local', device_id: DEVICE, canonical_user_id: USER },
    })
    expect(invoke).toHaveBeenNthCalledWith(2, 'commit_note_sync_ack', {
      command: { account_id: 'local', device_id: DEVICE, canonical_user_id: USER, expected_old_ack_cursor: 2, acknowledged_cursor: 4 },
    })
  })
})
