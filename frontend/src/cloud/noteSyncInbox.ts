import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { NoteSyncInboxRepository, CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { NoteSyncPuller } from './noteSyncPull'

/** Receives exactly one page and durably accepts it; it never decrypts notes. */
export class DurableNoteSyncInbox {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly puller: NoteSyncPuller,
    private readonly repository: NoteSyncInboxRepository,
  ) {}

  async pullOnce(accountId: string, deviceId: string): Promise<CommitInboundPageResult> {
    const binding = await this.bindings.ensureForCurrentUser(accountId)
    const state = await this.repository.readPullState(accountId, deviceId, binding.context.userId)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const page = await this.puller.pullOnce(accountId, deviceId, state.pull_cursor)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    // The Rust command revalidates binding, device, and expected cursor inside BEGIN IMMEDIATE.
    return this.repository.commitInboundPage(page, binding.context.userId)
  }
}
