import { invoke } from '@tauri-apps/api/core'

export type EnsureCloudAccountBindingResult = 'created' | 'validated'

export interface CloudAccountBindingRepository {
  ensure(localAccountId: string, canonicalUserId: string): Promise<EnsureCloudAccountBindingResult>
}

export class SQLiteCloudAccountBindingRepository implements CloudAccountBindingRepository {
  ensure(localAccountId: string, canonicalUserId: string): Promise<EnsureCloudAccountBindingResult> {
    return invoke('ensure_cloud_account_binding', {
      command: {
        local_account_id: localAccountId,
        canonical_user_id: canonicalUserId,
      },
    })
  }
}
