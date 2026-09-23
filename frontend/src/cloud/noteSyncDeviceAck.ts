import { syncApi, type SyncDeviceResponse } from '@/api/sync'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError, type AuthContextSnapshot } from '@/auth/userAuth'
import { SYNC_PROTOCOL_VERSION, isSyncCursor } from './syncProtocol'
import type { CommitNoteSyncAckResult, NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'

const CANONICAL_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

interface NoteSyncDeviceAckTransport {
  registerDevice(accessToken: string, deviceId: string): Promise<SyncDeviceResponse>
  ack(accessToken: string, request: { protocol_version: 1, device_id: string, cursor: number }): Promise<void>
}

export type NoteSyncAckOnceResult =
  | { readonly status: 'no_progress', readonly cursor: number }
  | { readonly status: CommitNoteSyncAckResult, readonly cursor: number }

function assertRegistration(response: unknown, deviceId: string): asserts response is SyncDeviceResponse {
  if (typeof response !== 'object' || response === null) throw new TypeError('Malformed sync device registration response.')
  const value = response as SyncDeviceResponse
  if (value.protocol_version !== SYNC_PROTOCOL_VERSION || value.device_id !== deviceId
    || !CANONICAL_UUID.test(value.device_id) || !isSyncCursor(value.last_ack_cursor)) {
    throw new TypeError('Malformed sync device registration response.')
  }
}

/**
 * Internal transport adapter. The durable device id is accepted only after the
 * Rust ACK substrate has revalidated it against local account scope.
 */
export class NoteSyncDeviceAckAdapter {
  constructor(
    private readonly auth: NormalUserAuthRuntime,
    private readonly bindings: AuthoritativeAccountBinding,
    private readonly repository: NoteSyncAckRepository,
    private readonly transport: NoteSyncDeviceAckTransport = syncApi,
  ) {}

  async registerOnce(localAccountId: string, durableDeviceId: string): Promise<{ readonly deviceId: string, readonly serverAckCursor: number }> {
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    // This read-only command is also the durable account/device authority check.
    await this.repository.prepare(localAccountId, durableDeviceId, binding.context.userId)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    const registered = await this.auth.authorized(accessToken => this.transport.registerDevice(accessToken, durableDeviceId))
    this.assertCurrent(binding.context, registered.context)
    assertRegistration(registered.value, durableDeviceId)
    // last_ack_cursor is server metadata only. It never writes local state.
    return { deviceId: durableDeviceId, serverAckCursor: registered.value.last_ack_cursor }
  }

  async ackOnce(localAccountId: string, durableDeviceId: string): Promise<NoteSyncAckOnceResult> {
    const binding = await this.bindings.ensureForCurrentUser(localAccountId)
    const candidate = await this.repository.prepare(localAccountId, durableDeviceId, binding.context.userId)
    if (!this.auth.isCurrent(binding.context)) throw new StaleAuthContextError()
    if (candidate.candidate_cursor === candidate.current_ack_cursor) {
      return { status: 'no_progress', cursor: candidate.current_ack_cursor }
    }
    const acknowledged = await this.auth.authorized(accessToken => this.transport.ack(accessToken, {
      protocol_version: SYNC_PROTOCOL_VERSION,
      device_id: durableDeviceId,
      cursor: candidate.candidate_cursor,
    }))
    this.assertCurrent(binding.context, acknowledged.context)
    // A failed/lost HTTP response never reaches this durable write. A later
    // monotonic retry is safe, including after a server-side commit.
    const status = await this.repository.commit(
      localAccountId, durableDeviceId, binding.context.userId,
      candidate.current_ack_cursor, candidate.candidate_cursor,
    )
    return { status, cursor: candidate.candidate_cursor }
  }

  private assertCurrent(expected: AuthContextSnapshot, actual: AuthContextSnapshot): void {
    if (expected.userId !== actual.userId || expected.authEpoch !== actual.authEpoch || !this.auth.isCurrent(expected)) {
      throw new StaleAuthContextError()
    }
  }
}
