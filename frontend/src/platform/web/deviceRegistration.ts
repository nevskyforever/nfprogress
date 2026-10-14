import { syncApi, type SyncDeviceResponse } from '@/api/sync'
import type { NormalUserAuthRuntime } from '@/auth/userAuth'
import type { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { BrowserPersistenceError } from './persistence'
import { snapshotBrowserSyncScope, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'

/** Registration envelope version is independent of the account writer transport. */
export function validateBrowserDeviceRegistration(value: unknown, deviceId: string): SyncDeviceResponse {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new TypeError('invalid_browser_device_registration')
  const row = value as Record<string, unknown>
  if (Object.keys(row).length !== 3 || !['protocol_version', 'device_id', 'last_ack_cursor'].every(k => Object.hasOwn(row, k))
    || row.protocol_version !== 1 || row.device_id !== deviceId
    || !Number.isSafeInteger(row.last_ack_cursor) || (row.last_ack_cursor as number) < 0) throw new TypeError('invalid_browser_device_registration')
  return { protocol_version: 1, device_id: deviceId, last_ack_cursor: row.last_ack_cursor as number }
}

/** Dormant identity-only registration. No reader declaration, cutover, ACK or local cache. */
export class BrowserDeviceRegistration {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly sessionCurrent: () => boolean) {}
  bind(auth: NormalUserAuthRuntime, bindings: AuthoritativeAccountBinding): BrowserDeviceRegistrationRuntime {
    return new BrowserDeviceRegistrationRuntime(this.transaction, this.sessionCurrent, auth, bindings)
  }
}
export class BrowserDeviceRegistrationRuntime {
  constructor(private readonly transaction: BrowserSyncTransaction, private readonly sessionCurrent: () => boolean,
    private readonly auth: NormalUserAuthRuntime, private readonly bindings: AuthoritativeAccountBinding) {}

  async registerOnce(input: BrowserSyncScope): Promise<{ deviceId: string; serverAckCursor: number; ready: false }> {
    const scope = snapshotBrowserSyncScope(input)
    if (!this.sessionCurrent()) throw new BrowserPersistenceError('closed')
    const { context } = await this.bindings.ensureForCurrentUser(scope.accountId)
    if (context.userId !== scope.canonicalUserId) throw new BrowserPersistenceError('account_mismatch')
    const current = () => this.sessionCurrent() && this.auth.isCurrent(context)
    const check = () => { if (!current()) throw new BrowserPersistenceError('closed') }
    // The persistence scheduler validates both durable identity and account binding
    // before invoking this callback. Recheck after HTTP without writing any store.
    const ownership = () => this.transaction<void>(scope, [], 'readonly', (_tx, result, abort) => {
      try { check(); result(undefined) } catch (error) { abort(error) }
    })
    await ownership(); check()
    const registered = await this.auth.authorized(token => { check(); return syncApi.registerDevice(token, scope.deviceId) })
    check()
    if (registered.context.userId !== context.userId || registered.context.authEpoch !== context.authEpoch) throw new BrowserPersistenceError('closed')
    const response = validateBrowserDeviceRegistration(registered.value, scope.deviceId)
    await ownership(); check()
    // Server last_ack_cursor is metadata, never local authority. No retained proof.
    return { deviceId: response.device_id, serverAckCursor: response.last_ack_cursor, ready: false }
  }
}
