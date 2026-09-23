import { invoke } from '@tauri-apps/api/core'

export interface CloudIdentity {
  readonly local_account_id: string
  readonly device_id: string
}

export interface CloudIdentityRepository {
  provision(canonicalUserId: string): Promise<CloudIdentity>
  read(canonicalUserId: string): Promise<CloudIdentity | null>
}

/** Narrow IPC boundary for durable account/device identity; it accepts no caller device ID or SQL. */
export class SQLiteCloudIdentityRepository implements CloudIdentityRepository {
  provision(canonicalUserId: string): Promise<CloudIdentity> {
    return invoke<CloudIdentity>('provision_cloud_identity', {
      command: { canonical_user_id: canonicalUserId },
    })
  }

  read(canonicalUserId: string): Promise<CloudIdentity | null> {
    return invoke<CloudIdentity | null>('read_cloud_identity', {
      command: { canonical_user_id: canonicalUserId },
    })
  }
}
