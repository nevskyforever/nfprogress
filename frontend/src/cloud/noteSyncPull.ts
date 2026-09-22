import { encryptedSyncApi, type EncryptedSyncPullItem } from '@/api/encryptedSync'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'

export interface ValidatedEncryptedPullBatch {
  readonly accountId: string
  readonly deviceId: string
  readonly since: number
  readonly nextCursor: number
  readonly hasMore: boolean
  /** Opaque validated transport data. It is neither persisted nor applied here. */
  readonly items: readonly EncryptedSyncPullItem[]
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
