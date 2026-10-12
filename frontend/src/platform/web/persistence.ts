import { BrowserProjectBindings } from './projectBindings'
import type { CloudIdentity, CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { CloudAccountBindingRepository, EnsureCloudAccountBindingResult } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { BrowserSyncDurability, validateBrowserV2SyncState, validateBrowserV3SyncState, type BrowserSyncScope } from './syncDurability'

export const WEB_DATABASE_NAME = 'worta-web'
export const WEB_DATABASE_VERSION = 4
const WRITER_LOCK = `${WEB_DATABASE_NAME}:writer`
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const STORES = ['identities', 'accountBindings']
export type BrowserPersistenceCode = 'unavailable' | 'quota_exceeded' | 'unsupported_version' | 'upgrade_blocked' | 'writer_busy' | 'storage_failed' | 'corrupt_record' | 'account_mismatch' | 'closed' | 'conflicting_record' | 'stale_cursor' | 'missing_history' | 'stale_lineage' | 'invalid_lineage_transition'

const SCHEMA: ReadonlyArray<readonly [string, string | string[], ReadonlyArray<readonly [string, string | string[], boolean]>]> = [
  ['identities', 'canonical_user_id', [['local_account_id', 'local_account_id', true], ['device_id', 'device_id', true]]],
  ['accountBindings', 'local_account_id', [['canonical_user_id', 'canonical_user_id', true]]],
  ['outbox', ['account_id', 'event_id'], [['ordinal', ['account_id', 'device_id', 'local_ordinal'], true], ['state', ['account_id', 'state', 'local_ordinal'], false]]],
  ['inbox', ['account_id', 'server_sequence'], [['event', ['account_id', 'event_id'], true], ['state', ['account_id', 'state', 'server_sequence'], false]]],
  ['cursors', ['account_id', 'device_id'], []],
  ['receipts', ['account_id', 'event_id'], [['server_sequence', ['account_id', 'server_sequence'], true]]],
  ['projectBindings', ['account_id', 'project_id'], [['bootstrap', ['account_id', 'bootstrap_id'], true]]],
]

function validateSchema(database: IDBDatabase, transaction: IDBTransaction, version: number): void {
  const schema = version === 1 ? SCHEMA.slice(0, 2) : version === 2 ? SCHEMA.slice(0, 5) : version === 3 ? SCHEMA.slice(0, 6) : SCHEMA
  if (Array.from(database.objectStoreNames).sort().join(',') !== schema.map(([name]) => name).sort().join(',')) throw new BrowserPersistenceError('unsupported_version')
  for (const [name, key, indexes] of schema) {
    const store = transaction.objectStore(name)
    if (JSON.stringify(store.keyPath) !== JSON.stringify(key) || store.autoIncrement || store.indexNames.length !== indexes.length
      || indexes.some(([index, path, unique]) => !store.indexNames.contains(index) || store.index(index).unique !== unique || JSON.stringify(store.index(index).keyPath) !== JSON.stringify(path))) throw new BrowserPersistenceError('corrupt_record')
  }
}

/** Bounded diagnostics only: never retain arbitrary storage error messages/data. */
export class BrowserPersistenceError extends Error {
  readonly name = 'BrowserPersistenceError'
  constructor(readonly code: BrowserPersistenceCode) { super(`web_persistence_${code}`) }
}

export function persistenceError(error: unknown): BrowserPersistenceError {
  if (error instanceof BrowserPersistenceError) return error
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'QuotaExceededError') return new BrowserPersistenceError('quota_exceeded')
  if (name === 'VersionError') return new BrowserPersistenceError('unsupported_version')
  if (['SecurityError', 'NotAllowedError', 'NotSupportedError'].includes(name)) return new BrowserPersistenceError('unavailable')
  return new BrowserPersistenceError('storage_failed')
}

interface IdentityRecord extends CloudIdentity { canonical_user_id: string; record_version: 1 }
interface BindingRecord { local_account_id: string; canonical_user_id: string; record_version: 1 }
function validUser(value: string): void {
  if (typeof value !== 'string' || !UUID.test(value)) throw new BrowserPersistenceError('account_mismatch')
}
function validateRecords(identity: unknown, binding: unknown, user: string): IdentityRecord {
  const i = identity as IdentityRecord | undefined, b = binding as BindingRecord | undefined
  if (!i || !b || Object.keys(i).sort().join(',') !== 'canonical_user_id,device_id,local_account_id,record_version'
    || Object.keys(b).sort().join(',') !== 'canonical_user_id,local_account_id,record_version'
    || i.record_version !== 1 || b.record_version !== 1
    || !UUID.test(i.canonical_user_id) || i.canonical_user_id !== user || b.canonical_user_id !== user
    || i.local_account_id !== b.local_account_id || !UUID.test(i.local_account_id) || !UUID.test(i.device_id)) {
    throw new BrowserPersistenceError('corrupt_record')
  }
  return i
}

/** Infrastructure helper: only synchronous IDB scheduling, never async crypto/HTTP. */
export function runBrowserTransaction<T>(
  database: IDBDatabase,
  stores: string[],
  mode: 'readonly' | 'readwrite',
  schedule: (transaction: IDBTransaction, result: (value: T) => void, fail: (error: unknown) => void) => void,
  track?: (transaction: IDBTransaction, completion: Promise<T>) => void,
): Promise<T> {
  let transaction: IDBTransaction
  try {
    transaction = database.transaction(stores, mode, { durability: 'strict' })
    if (mode === 'readwrite' && transaction.durability !== 'strict') {
      transaction.abort()
      throw new BrowserPersistenceError('unavailable')
    }
  } catch (error) { return Promise.reject(persistenceError(error)) }
  let value: T, hasResult = false, failure: BrowserPersistenceError | undefined
  const completion = new Promise<T>((resolve, reject) => {
    const fail = (error: unknown) => {
      failure ??= persistenceError(error)
      try { transaction.abort() } catch { /* Already completed/aborted; never claim success. */ }
    }
    transaction.oncomplete = () => {
      if (failure) reject(failure)
      else if (!hasResult) reject(new BrowserPersistenceError('storage_failed'))
      else resolve(value)
    }
    transaction.onabort = () => reject(failure ?? persistenceError(transaction.error))
    // Do not preventDefault: a failed request must abort the whole transaction.
    transaction.onerror = event => { failure ??= persistenceError((event.target as IDBRequest).error ?? transaction.error) }
    try {
      const returned: unknown = schedule(transaction, result => { value = result; hasResult = true }, fail)
      if (returned !== undefined) {
        fail(new BrowserPersistenceError('storage_failed'))
        void Promise.resolve(returned).catch(() => undefined)
      }
    } catch (error) { fail(error) }
  })
  track?.(transaction, completion)
  return completion
}

function openDatabase(factory: IDBFactory, signal: AbortSignal): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    let request: IDBOpenDBRequest, failed = false
    const abortUpgrade = () => {
      try { request?.transaction?.abort() } catch { /* Already completed/aborted; opening still fails closed. */ }
    }
    const cancel = () => {
      abortUpgrade()
      fail(new BrowserPersistenceError('closed'))
    }
    const fail = (error: unknown) => {
      failed = true
      signal.removeEventListener('abort', cancel)
      reject(persistenceError(error))
    }
    if (signal.aborted) { cancel(); return }
    signal.addEventListener('abort', cancel, { once: true })
    try { request = factory.open(WEB_DATABASE_NAME, WEB_DATABASE_VERSION) }
    catch (error) { fail(error); return }
    request.onblocked = () => fail(new BrowserPersistenceError('upgrade_blocked'))
    request.onerror = () => fail(request.error)
    request.onupgradeneeded = event => {
      if (failed || ![0, 1, 2, 3].includes(event.oldVersion)) {
        abortUpgrade()
        fail(new BrowserPersistenceError('unsupported_version'))
        return
      }
      try {
        const transaction = request.transaction!
        if (event.oldVersion > 0) {
          validateSchema(request.result, transaction, event.oldVersion)
          const names = event.oldVersion === 1 ? STORES : SCHEMA.slice(0, event.oldVersion === 2 ? 5 : 6).map(([name]) => name)
          const requests = names.map(name => transaction.objectStore(name).getAll())
          let received = 0
          const validate = () => {
            if (++received !== requests.length) return
            try {
              const identities = requests[0]!.result as IdentityRecord[], bindings = requests[1]!.result as BindingRecord[]
              if (identities.length !== bindings.length) throw new BrowserPersistenceError('corrupt_record')
              for (const identity of identities) validateRecords(identity, bindings.find(b => b.canonical_user_id === identity.canonical_user_id), identity.canonical_user_id)
              if (event.oldVersion === 2) validateBrowserV2SyncState(identities.map(identity => ({ canonicalUserId: identity.canonical_user_id, accountId: identity.local_account_id, deviceId: identity.device_id })), requests[2]!.result, requests[3]!.result, requests[4]!.result)
              if (event.oldVersion === 3) validateBrowserV3SyncState(identities.map(identity => ({ canonicalUserId: identity.canonical_user_id, accountId: identity.local_account_id, deviceId: identity.device_id })), requests[2]!.result, requests[3]!.result, requests[4]!.result, requests[5]!.result)
            } catch (error) { abortUpgrade(); fail(error) }
          }
          for (const read of requests) read.onsuccess = validate
        }
        for (const [name, keyPath, indexes] of SCHEMA.slice(event.oldVersion === 0 ? 0 : event.oldVersion === 1 ? 2 : event.oldVersion === 2 ? 5 : 6)) {
          const store = request.result.createObjectStore(name, { keyPath })
          for (const [index, path, unique] of indexes) store.createIndex(index, path, { unique })
        }
      } catch (error) { abortUpgrade(); fail(error) }
    }
    request.onsuccess = () => {
      const database = request.result
      if (failed) { database.close(); return }
      try {
        if (database.version !== WEB_DATABASE_VERSION) {
          throw new BrowserPersistenceError('unsupported_version')
        }
        validateSchema(database, database.transaction(SCHEMA.map(([name]) => name)), WEB_DATABASE_VERSION)
        signal.removeEventListener('abort', cancel)
        resolve(database)
      } catch (error) { database.close(); fail(error) }
    }
  })
}

/** Dormant browser identity/binding and encrypted durability session. No full sync composition. */
class BrowserPersistence implements CloudIdentityRepository, CloudAccountBindingRepository {
  readonly sync: BrowserSyncDurability
  readonly projects: BrowserProjectBindings
  private active = true
  private readonly pending = new Map<IDBTransaction, Promise<unknown>>()
  private closeFlight: Promise<void> | undefined
  private readonly abort = () => { void this.close() }

  constructor(
    private readonly database: IDBDatabase, private readonly user: string,
    private readonly releaseWriter: () => void, private readonly writerFlight: () => Promise<unknown>,
    private readonly signal: AbortSignal, private readonly cleanup: () => void,
  ) {
    this.sync = new BrowserSyncDurability((scope, stores, mode, schedule) => this.syncTransaction(scope, stores, mode, schedule))
    this.projects = new BrowserProjectBindings((scope, stores, mode, schedule) => this.syncTransaction(scope, stores, mode, schedule))
    database.onversionchange = () => { void this.close() }
    database.onclose = () => { void this.close() }
    signal.addEventListener('abort', this.abort, { once: true })
  }

  private check(user = this.user): void {
    if (!this.active) throw new BrowserPersistenceError('closed')
    if (user !== this.user) throw new BrowserPersistenceError('account_mismatch')
  }
  private transaction<T>(mode: 'readonly' | 'readwrite', schedule: Parameters<typeof runBrowserTransaction<T>>[3], stores = STORES): Promise<T> {
    this.check()
    return runBrowserTransaction(this.database, stores, mode, schedule, (transaction, completion) => {
      this.pending.set(transaction, completion)
      void completion.then(() => this.pending.delete(transaction), () => this.pending.delete(transaction))
    }).then(result => { this.check(); return result }, error => { this.check(); throw error })
  }
  private syncTransaction<T>(scope: BrowserSyncScope, stores: string[], mode: 'readonly' | 'readwrite', schedule: Parameters<typeof runBrowserTransaction<T>>[3]): Promise<T> {
    this.check(scope.canonicalUserId)
    return this.transaction(mode, (transaction, result, fail) => {
      const identity = transaction.objectStore('identities').get(this.user)
      const binding = transaction.objectStore('accountBindings').index('canonical_user_id').get(this.user)
      let received = 0
      const start = () => {
        if (++received !== 2) return
        try {
          this.check(scope.canonicalUserId)
          const value = validateRecords(identity.result, binding.result, this.user)
          if (value.local_account_id !== scope.accountId || value.device_id !== scope.deviceId) throw new BrowserPersistenceError('account_mismatch')
          schedule(transaction, result, fail)
        } catch (error) { fail(error) }
      }
      identity.onsuccess = start
      binding.onsuccess = start
    }, [...STORES, ...stores])
  }
  private identity(create: boolean): Promise<CloudIdentity> {
    return this.transaction<CloudIdentity>(create ? 'readwrite' : 'readonly', (transaction, result, fail) => {
      const identities = transaction.objectStore('identities'), bindings = transaction.objectStore('accountBindings')
      const identityRequest = identities.get(this.user)
      const bindingRequest = bindings.index('canonical_user_id').get(this.user)
      let received = 0
      const finish = () => {
        if (++received !== 2) return
        try {
          this.check()
          if (identityRequest.result === undefined && bindingRequest.result === undefined && create) {
            const identity: IdentityRecord = { canonical_user_id: this.user, local_account_id: crypto.randomUUID(), device_id: crypto.randomUUID(), record_version: 1 }
            identities.add(identity)
            bindings.add({ canonical_user_id: this.user, local_account_id: identity.local_account_id, record_version: 1 } satisfies BindingRecord)
            result({ local_account_id: identity.local_account_id, device_id: identity.device_id })
          } else {
            const identity = validateRecords(identityRequest.result, bindingRequest.result, this.user)
            result({ local_account_id: identity.local_account_id, device_id: identity.device_id })
          }
        } catch (error) { fail(error) }
      }
      identityRequest.onsuccess = finish
      bindingRequest.onsuccess = finish
    })
  }
  async provision(canonicalUserId: string): Promise<CloudIdentity> {
    this.check(canonicalUserId)
    return this.identity(true)
  }
  async read(canonicalUserId: string): Promise<CloudIdentity | null> {
    this.check(canonicalUserId)
    return this.identity(false)
  }
  async ensure(localAccountId: string, canonicalUserId: string): Promise<EnsureCloudAccountBindingResult> {
    this.check(canonicalUserId)
    const identity = await this.read(canonicalUserId)
    if (identity?.local_account_id !== localAccountId) throw new BrowserPersistenceError('account_mismatch')
    return 'validated'
  }
  /** Revoke immediately; abort/drain before releasing writer; never delete data. */
  close(): Promise<void> {
    if (this.closeFlight) return this.closeFlight
    this.active = false
    this.signal.removeEventListener('abort', this.abort)
    this.cleanup()
    const pending = Array.from(this.pending.values())
    for (const transaction of this.pending.keys()) {
      try { transaction.abort() } catch { /* Completion may already be queued. */ }
    }
    this.database.close()
    this.closeFlight = Promise.allSettled(pending).then(async () => {
      this.releaseWriter()
      await this.writerFlight().catch(() => undefined)
    })
    return this.closeFlight
  }
  resetForLogout(): Promise<void> { return this.close() }
}

/** Caller supplies a canonical authenticated user ID; this is not authentication. */
export async function openBrowserPersistence(canonicalUserId: string, signal?: AbortSignal): Promise<BrowserPersistence> {
  validUser(canonicalUserId)
  if (signal?.aborted) throw new BrowserPersistenceError('closed')
  let factory: IDBFactory, locks: LockManager
  try {
    if (typeof window === 'undefined' || !globalThis.isSecureContext || !globalThis.indexedDB || !navigator.locks || !crypto.randomUUID) throw new BrowserPersistenceError('unavailable')
    factory = globalThis.indexedDB
    locks = navigator.locks
  } catch (error) { throw error instanceof BrowserPersistenceError ? error : new BrowserPersistenceError('unavailable') }
  const cancellation = new AbortController()
  const cancel = () => cancellation.abort()
  const cleanup = () => {
    signal?.removeEventListener('abort', cancel)
    window.removeEventListener('pagehide', cancel)
  }
  signal?.addEventListener('abort', cancel, { once: true })
  window.addEventListener('pagehide', cancel, { once: true })
  let resolveReady!: (value: BrowserPersistence) => void, rejectReady!: (error: BrowserPersistenceError) => void
  const ready = new Promise<BrowserPersistence>((resolve, reject) => { resolveReady = resolve; rejectReady = reject })
  let session: BrowserPersistence | undefined
  let flight: Promise<unknown>
  try { flight = locks.request(WRITER_LOCK, { mode: 'exclusive', ifAvailable: true }, async lock => {
    if (cancellation.signal.aborted) throw new BrowserPersistenceError('closed')
    if (!lock) throw new BrowserPersistenceError('writer_busy')
    const database = await openDatabase(factory, cancellation.signal)
    if (cancellation.signal.aborted) { database.close(); throw new BrowserPersistenceError('closed') }
    let release!: () => void
    const held = new Promise<void>(resolve => { release = resolve })
    session = new BrowserPersistence(database, canonicalUserId, release, () => flight, cancellation.signal, cleanup)
    try {
      await session.provision(canonicalUserId)
      resolveReady(session)
      await held
    } catch (error) {
      // On open failure no caller owns the session; revoke before releasing.
      void session.close()
      throw error
    }
  }) } catch (error) { cleanup(); throw persistenceError(error) }
  void flight.catch(error => {
    cleanup()
    rejectReady(persistenceError(error))
    if (session) void session.close()
  })
  return ready
}
