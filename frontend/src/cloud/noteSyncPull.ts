import { encryptedSyncApi } from '@/api/encryptedSync'
import type { ObjectCryptoEnvelope } from '@/crypto'

export interface ValidatedEncryptedPullItem {
  readonly event: {
    readonly event_id: string; readonly device_id: string; readonly server_sequence: number
    readonly project_id: string; readonly entity_id: string; readonly entity_type: string
    readonly operation: 'upsert' | 'delete' | 'event' | 'resolution'; readonly revision: number
    readonly updated_at: string; readonly deleted_at: string | null
  }
  readonly object: ObjectCryptoEnvelope | null
}
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'

export interface ValidatedEncryptedPullBatch {
  readonly accountId: string
  readonly deviceId: string
  readonly since: number
  readonly nextCursor: number
  readonly hasMore: boolean
  /** Opaque validated transport data. It is neither persisted nor applied here. */
  readonly items: readonly ValidatedEncryptedPullItem[]
}

/** Fetches one authenticated page only; durable inbox receipt and cursor advancement are deliberately deferred. */
export class NoteSyncPuller {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
  ) {}

  async pullOnce(localAccountId: string, deviceId: string, since: number, limit = 200): Promise<ValidatedEncryptedPullBatch> {
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const pulled = await this.auth.authorized(accessToken => encryptedSyncApi.pull(accessToken, deviceId, since, limit))
    this.assertCurrentBinding(binding.context, pulled.context)
    return Object.freeze({
      accountId: localAccountId,
      deviceId,
      since,
      nextCursor: pulled.value.next_cursor,
      hasMore: pulled.value.has_more,
      items: Object.freeze([...pulled.value.items]),
    })
  }

  private assertCurrentBinding(expected: AuthContextSnapshot, actual: AuthContextSnapshot): void {
    if (expected.userId !== actual.userId || expected.authEpoch !== actual.authEpoch || !this.auth.isCurrent(expected)) {
      throw new StaleAuthContextError()
    }
  }
}
