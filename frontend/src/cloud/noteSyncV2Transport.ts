import { encryptedSyncV2Api, parseV2Capabilities } from '@/api/encryptedSyncV2'
import { ApiError } from '@/api/client'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { NoteSyncInboxRepository, CommitInboundPageResult } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type { NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import type { NoteSyncAckOnceResult } from './noteSyncDeviceAck'

export class NoteSyncV2TransportError extends Error {
  constructor(readonly code: 'mode_incompatible' | 'native_failure', message = 'Encrypted sync v2 transport mode is incompatible.') { super(message) }
}

interface V2Api {
  capabilities: typeof encryptedSyncV2Api.capabilities
  pull: typeof encryptedSyncV2Api.pull
  ack: typeof encryptedSyncV2Api.ack
}

/** Mode-2 transport adapters with server-mode checks at each HTTP boundary. */
class V2Scope {
  constructor(
    protected readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly identity: CloudIdentityRepository,
    protected readonly api: V2Api,
  ) {}

  protected async bind(accountId: string, deviceId: string): Promise<AuthContextSnapshot> {
    const binding = await this.bindings.ensureForCurrentUser(accountId)
    const identity = await this.native(() => this.identity.read(binding.context.userId))
    if (!identity || identity.local_account_id !== accountId || identity.device_id !== deviceId || !this.auth.isCurrent(binding.context)) {
      throw new StaleAuthContextError()
    }
    return binding.context
  }

  protected assertCurrent(expected: AuthContextSnapshot, actual?: AuthContextSnapshot): void {
    if ((actual && (expected.userId !== actual.userId || expected.authEpoch !== actual.authEpoch)) || !this.auth.isCurrent(expected)) {
      throw new StaleAuthContextError()
    }
  }

  protected async requireMode(context: AuthContextSnapshot): Promise<void> {
    const result = await this.auth.authorized(token => this.api.capabilities(token))
    this.assertCurrent(context, result.context)
    const capability = parseV2Capabilities(result.value)
    if (capability.writer_transport_version !== 2) throw new NoteSyncV2TransportError('mode_incompatible')
  }

  protected mapMode(error: unknown): never {
    if (error instanceof ApiError && error.code === 'sync_transport_mode_incompatible') throw new NoteSyncV2TransportError('mode_incompatible')
    throw error
  }

  protected async native<T>(operation: () => Promise<T>): Promise<T> {
    try { return await operation() }
    catch { throw new NoteSyncV2TransportError('native_failure', 'Encrypted sync v2 native operation failed.') }
  }
}

export class DurableNoteSyncV2Inbox extends V2Scope {
  constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository,
    private readonly repository: NoteSyncInboxRepository, api: V2Api = encryptedSyncV2Api) {
    super(auth, bindings, identity, api)
  }

  async pullOnce(accountId: string, deviceId: string): Promise<CommitInboundPageResult> {
    const context = await this.bind(accountId, deviceId)
    const state = await this.native(() => this.repository.readPullState(accountId, deviceId, context.userId))
    this.assertCurrent(context)
    await this.requireMode(context)
    try {
      const pulled = await this.auth.authorized(token => this.api.pull(token, deviceId, state.pull_cursor))
      this.assertCurrent(context, pulled.context)
      return this.native(() => this.repository.commitInboundPage({ accountId, deviceId, since: state.pull_cursor,
        nextCursor: pulled.value.next_cursor, hasMore: pulled.value.has_more, items: pulled.value.items }, context.userId))
    } catch (error) { this.mapMode(error) }
  }
}

export class NoteSyncV2AckAdapter extends V2Scope {
  constructor(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding, identity: CloudIdentityRepository,
    private readonly repository: NoteSyncAckRepository, api: V2Api = encryptedSyncV2Api) {
    super(auth, bindings, identity, api)
  }

  async ackOnce(accountId: string, deviceId: string): Promise<NoteSyncAckOnceResult> {
    const context = await this.bind(accountId, deviceId)
    const candidate = await this.native(() => this.repository.prepare(accountId, deviceId, context.userId))
    this.assertCurrent(context)
    if (!Number.isSafeInteger(candidate.current_ack_cursor) || candidate.current_ack_cursor < 0
      || !Number.isSafeInteger(candidate.candidate_cursor) || candidate.candidate_cursor < candidate.current_ack_cursor) {
      throw new TypeError('Invalid native ACK candidate.')
    }
    if (candidate.candidate_cursor === candidate.current_ack_cursor) return { status: 'no_progress', cursor: candidate.current_ack_cursor }
    await this.requireMode(context)
    try {
      const acknowledged = await this.auth.authorized(token => this.api.ack(token, {
        protocol_version: 2, encrypted_sync_version: 2, device_id: deviceId, cursor: candidate.candidate_cursor,
      }))
      this.assertCurrent(context, acknowledged.context)
      const status = await this.native(() => this.repository.commit(accountId, deviceId, context.userId,
        candidate.current_ack_cursor, candidate.candidate_cursor))
      return { status, cursor: candidate.candidate_cursor }
    } catch (error) { this.mapMode(error) }
  }
}
