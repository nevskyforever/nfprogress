import { invoke } from '@tauri-apps/api/core'

import type { NoteSyncOutboxRepository, SealedNoteSyncOutboxItem } from '@/cloud/noteSyncOutbox'

const MAX_RUST_SEALED_OUTBOX_LIST_LIMIT = 200

export class SQLiteNoteSyncOutboxRepository implements NoteSyncOutboxRepository {
  listSealed(accountId: string, limit: number): Promise<SealedNoteSyncOutboxItem[]> {
    if (typeof accountId !== 'string' || accountId.length < 1 || accountId.length > 512) {
      throw new TypeError('Invalid Note sync outbox account scope.')
    }
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > MAX_RUST_SEALED_OUTBOX_LIST_LIMIT) {
      throw new RangeError('Invalid sealed Note sync outbox list limit.')
    }
    return invoke<SealedNoteSyncOutboxItem[]>('list_sealed_note_sync_outbox', {
      accountId,
      limit,
    })
  }
}
