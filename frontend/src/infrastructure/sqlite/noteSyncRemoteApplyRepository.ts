import { invoke } from '@tauri-apps/api/core'

export type NoteSyncRemoteApplyStatus =
  | 'applied'
  | 'already_applied'
  | 'self_echo_applied'
  | 'orphan'
  | 'conflict'
  | 'rejected'

/** Narrow input for the authenticated decrypt-to-apply boundary. */
export interface VerifiedNoteSyncRemoteApplyCommand {
  readonly account_id: string
  readonly canonical_user_id: string
  readonly pulling_device_id: string
  readonly event_id: string
  readonly server_sequence: number
  readonly source_device_id: string
  readonly crypto_version: number
  readonly aad_version: number
  readonly nonce: readonly number[]
  readonly ciphertext: readonly number[]
  readonly plaintext: readonly number[]
}

export interface NoteSyncRemoteApplyRepository {
  applyVerified(command: VerifiedNoteSyncRemoteApplyCommand): Promise<NoteSyncRemoteApplyStatus>
}

export class SQLiteNoteSyncRemoteApplyRepository implements NoteSyncRemoteApplyRepository {
  applyVerified(command: VerifiedNoteSyncRemoteApplyCommand): Promise<NoteSyncRemoteApplyStatus> {
    return invoke<NoteSyncRemoteApplyStatus>('apply_verified_received_note', { command })
  }
}
