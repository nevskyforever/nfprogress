import { invoke } from '@tauri-apps/api/core'

export interface NoteSyncAckCandidate {
  readonly current_ack_cursor: number
  readonly candidate_cursor: number
}

export type CommitNoteSyncAckResult =
  | 'advanced'
  | 'already_acknowledged'
  | 'already_advanced'
  | 'stale'

export interface NoteSyncAckRepository {
  prepare(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncAckCandidate>
  commit(accountId: string, deviceId: string, canonicalUserId: string, expectedOldAckCursor: number, acknowledgedCursor: number): Promise<CommitNoteSyncAckResult>
}

/** Narrow IPC boundary for the durable ACK substrate; it accepts no SQL or capability. */
export class SQLiteNoteSyncAckRepository implements NoteSyncAckRepository {
  prepare(accountId: string, deviceId: string, canonicalUserId: string): Promise<NoteSyncAckCandidate> {
    return invoke('prepare_note_sync_ack', {
      command: { account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId },
    })
  }

  commit(accountId: string, deviceId: string, canonicalUserId: string, expectedOldAckCursor: number, acknowledgedCursor: number): Promise<CommitNoteSyncAckResult> {
    return invoke('commit_note_sync_ack', {
      command: {
        account_id: accountId, device_id: deviceId, canonical_user_id: canonicalUserId,
        expected_old_ack_cursor: expectedOldAckCursor, acknowledged_cursor: acknowledgedCursor,
      },
    })
  }
}
