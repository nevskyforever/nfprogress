import { BrowserPersistenceError, persistenceError, runBrowserTransaction } from './persistence'
import { BrowserSyncDurability, snapshotBrowserSyncScope, validateBrowserInboxRecord, validateBrowserSyncCursor,
  type BrowserReceivedInboxRecord, type BrowserSyncScope, type BrowserSyncTransaction } from './syncDurability'
import { REPLAY_LIMITS, prepareReplayPage, replayAnchor, replayExact, replaySame, replayUuid,
  validateReplayManifest, type ReplayAnchor, type ReplayManifest } from './replayRecords'

export const REPLAY_DATABASE_NAME = 'worta-web-replay'
export const REPLAY_DATABASE_VERSION = 1
type Schema = readonly [string, string | string[], ReadonlyArray<readonly [string, string | string[], boolean]>]
const schema: readonly Schema[] = [
  ['identities', 'canonical_user_id', [['local_account_id', 'local_account_id', true], ['device_id', 'device_id', true]]],
  ['accountBindings', 'local_account_id', [['canonical_user_id', 'canonical_user_id', true]]],
  ['outbox', ['account_id', 'event_id'], [['ordinal', ['account_id', 'device_id', 'local_ordinal'], true], ['state', ['account_id', 'state', 'local_ordinal'], false]]],
  ['inbox', ['account_id', 'server_sequence'], [['event', ['account_id', 'event_id'], true], ['state', ['account_id', 'state', 'server_sequence'], false]]],
  ['cursors', ['account_id', 'device_id'], []],
  ['receipts', ['account_id', 'event_id'], [['server_sequence', ['account_id', 'server_sequence'], true]]],
  ['projectBindings', ['account_id', 'project_id'], [['bootstrap', ['account_id', 'bootstrap_id'], true]]],
  ['ownerHeads', ['account_id', 'owner_kind', 'owner_id'], []],
  ['localProjects', ['account_id', 'project_id'], []],
  ['localNotes', ['account_id', 'project_id', 'note_id'], [['identity', ['account_id', 'note_id'], true]]],
  ['legacyNoteHistory', ['account_id', 'project_id', 'note_id', 'record_kind', 'record_id'], [['event', ['account_id', 'event_id'], true]]],
  ['legacyNoteIntents', ['account_id', 'event_id'], [['note', ['account_id', 'project_id', 'note_id'], true], ['ordinal', ['account_id', 'device_id', 'local_ordinal'], true]]],
  ['replayManifest', ['account_id', 'device_id'], []],
]
const names = schema.map(([name]) => name)
const emptyStores = names.filter(name => !['identities', 'accountBindings', 'inbox', 'cursors', 'replayManifest'].includes(name))
function fail(): never { throw new BrowserPersistenceError('corrupt_record') }
const range = (account: string) => IDBKeyRange.bound([account], [account, []])
export interface ReplaySnapshot { manifest: ReplayManifest | null; rows: BrowserReceivedInboxRecord[] }

function validateSchema(database: IDBDatabase): void {
  if (database.version !== 1 || !replaySame([...database.objectStoreNames].sort(), [...names].sort())) throw new BrowserPersistenceError('unsupported_version')
  const transaction = database.transaction(names, 'readonly')
  for (const [name, path, indexes] of schema) {
    const store = transaction.objectStore(name)
    if (!replaySame(store.keyPath, path) || store.autoIncrement || store.indexNames.length !== indexes.length) fail()
    for (const [index, key, unique] of indexes) {
      if (!store.indexNames.contains(index)) fail()
      const value = store.index(index)
      if (!replaySame(value.keyPath, key) || value.unique !== unique || value.multiEntry) fail()
    }
  }
}

function openDatabase(signal: AbortSignal): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    let request: IDBOpenDBRequest, failed = false
    const stop = (error: unknown) => { failed = true; signal.removeEventListener('abort', cancel); try { request?.transaction?.abort() } catch { /* Already aborted. */ } reject(persistenceError(error)) }
    const cancel = () => stop(new BrowserPersistenceError('closed'))
    signal.addEventListener('abort', cancel, { once: true })
    if (signal.aborted) { cancel(); return }
    try { request = indexedDB.open(REPLAY_DATABASE_NAME, REPLAY_DATABASE_VERSION) } catch (error) { stop(error); return }
    request.onblocked = () => stop(new BrowserPersistenceError('upgrade_blocked'))
    request.onerror = () => stop(request.error)
    request.onupgradeneeded = event => {
      try {
        if (failed || signal.aborted || event.oldVersion !== 0) throw new BrowserPersistenceError('unsupported_version')
        for (const [name, keyPath, indexes] of schema) {
          const store = request.result.createObjectStore(name, { keyPath })
          for (const [index, path, unique] of indexes) store.createIndex(index, path, { unique })
        }
      } catch (error) { stop(error) }
    }
    request.onsuccess = () => {
      signal.removeEventListener('abort', cancel)
      if (failed || signal.aborted) { request.result.close(); reject(new BrowserPersistenceError('closed')); return }
      try { validateSchema(request.result); resolve(request.result) }
      catch (error) { request.result.close(); reject(persistenceError(error)) }
    }
  })
}

/** Separate ciphertext staging DB. Compatibility owner/source stores remain empty in slice 1. */
class BrowserReplayStorage {
  private closed = false
  private readonly active = new Set<IDBTransaction>()
  private readonly cancel = () => { void this.close() }
  constructor(private readonly db: IDBDatabase, private readonly scope: BrowserSyncScope, private readonly signal: AbortSignal,
    private readonly current: () => boolean, private readonly release: () => void, private readonly flight: () => Promise<unknown>, private readonly cleanup: () => void) {
    signal.addEventListener('abort', this.cancel, { once: true })
    db.onversionchange = this.cancel
    db.onclose = this.cancel
  }
  private check(): void { if (this.closed || this.signal.aborted || !this.current()) throw new BrowserPersistenceError('closed') }
  async close(): Promise<void> {
    if (!this.closed) {
      this.closed = true; this.signal.removeEventListener('abort', this.cancel); this.cleanup()
      for (const transaction of this.active) { try { transaction.abort() } catch { /* Native transaction already ended. */ } }
      this.db.close(); this.release()
    }
    await this.flight().catch(() => undefined)
  }
  private run<T>(mode: IDBTransactionMode, schedule: (tx: IDBTransaction, result: (value: T) => void, abort: (error: unknown) => void) => void): Promise<T> {
    this.check()
    return runBrowserTransaction<T>(this.db, names, mode === 'readonly' ? 'readonly' : 'readwrite', (tx, result, abort) => {
      this.check(); schedule(tx, value => { this.check(); result(value) }, abort)
    }, (tx, completion) => {
      this.active.add(tx)
      void completion.finally(() => this.active.delete(tx)).catch(() => undefined)
    }).then(value => { this.check(); return value }).catch(error => { this.check(); throw error })
  }
  private load(tx: IDBTransaction, result: (value: ReplaySnapshot) => void, abort: (error: unknown) => void): void {
    const s = this.scope, bound = range(s.accountId), rows: BrowserReceivedInboxRecord[] = []
    const identity = tx.objectStore('identities').get(s.canonicalUserId), alias = tx.objectStore('identities').index('local_account_id').get(s.accountId)
    const binding = tx.objectStore('accountBindings').get(s.accountId), cursors = tx.objectStore('cursors').getAll(bound)
    const manifests = tx.objectStore('replayManifest').getAll(bound), counts = emptyStores.map(name => tx.objectStore(name).count(bound))
    let pending = 6 + counts.length, bytes = 0
    const finish = () => {
      try {
        this.check(); if (--pending) return
        if (counts.some(request => request.result !== 0) || cursors.result.length > 1 || manifests.result.length > 1) fail()
        const i: unknown = identity.result, b: unknown = binding.result
        if (i === undefined ? b !== undefined || alias.result !== undefined : !replayExact(i, ['record_version', 'canonical_user_id', 'local_account_id', 'device_id'])
          || i.record_version !== 1 || i.canonical_user_id !== s.canonicalUserId || i.local_account_id !== s.accountId || i.device_id !== s.deviceId
          || !replaySame(alias.result, i) || !replayExact(b, ['record_version', 'local_account_id', 'canonical_user_id'])
          || b.record_version !== 1 || b.local_account_id !== s.accountId || b.canonical_user_id !== s.canonicalUserId) fail()
        const manifest = manifests.result.length ? validateReplayManifest(manifests.result[0], s) : null
        const checkpoint = validateBrowserSyncCursor(cursors.result[0], s)
        if (checkpoint.ack_cursor !== 0 || checkpoint.proven_prefix !== 0 || checkpoint.next_local_ordinal !== 1
          || checkpoint.pull_cursor !== rows.length || !manifest && (rows.length || cursors.result.length)
          || manifest && (i === undefined || !cursors.result.length || manifest.receive_cursor !== rows.length)) fail()
        let ciphertextBytes = 0
        const ids = new Set<string>()
        for (const [index, row] of rows.entries()) {
          if (row.server_sequence !== index + 1 || ids.has(row.event_id)) fail()
          ids.add(row.event_id)
          const wire = JSON.parse(row.wire_item) as { object: { ciphertext: string } }
          ciphertextBytes += Math.floor(wire.object.ciphertext.length * 3 / 4)
        }
        if (manifest && (ciphertextBytes !== manifest.ciphertext_bytes || bytes + new TextEncoder().encode(JSON.stringify(manifest)).length + REPLAY_LIMITS.controlReserveBytes > REPLAY_LIMITS.inventoryBytes)) fail()
        result({ manifest, rows })
      } catch (error) { abort(error) }
    }
    for (const request of [identity, alias, binding, cursors, manifests, ...counts]) request.onsuccess = finish
    const scan = tx.objectStore('inbox').openCursor(bound)
    scan.onsuccess = () => {
      try {
        this.check(); const cursor = scan.result
        if (!cursor) { finish(); return }
        if (rows.length >= REPLAY_LIMITS.events) fail()
        const row = validateBrowserInboxRecord(cursor.value, s)
        if (row.record_version !== 1 || row.state !== 'received' || row.protocol_version !== 3 || !replaySame(cursor.primaryKey, [s.accountId, row.server_sequence])) fail()
        bytes += new TextEncoder().encode(JSON.stringify(row)).length
        if (bytes > REPLAY_LIMITS.inventoryBytes) fail()
        rows.push(row); cursor.continue()
      } catch (error) { abort(error) }
    }
  }
  read(): Promise<ReplaySnapshot> { return this.run('readonly', (tx, result, abort) => this.load(tx, result, abort)) }
  async start(input: ReplayAnchor): Promise<ReplaySnapshot> {
    const anchor = replayAnchor(input.registry, input.transport), s = this.scope
    await this.run('readwrite', (tx, result, abort) => this.load(tx, old => {
      try {
        if (old.manifest && replaySame(old.manifest.anchor, anchor)) { result(undefined); return }
        if (old.manifest) {
          const prior = old.manifest.anchor
          if (anchor.registry.current_cursor < prior.registry.current_cursor || anchor.transport.cutover_epoch < prior.transport.cutover_epoch) throw new BrowserPersistenceError('stale_cursor')
          if (prior.registry.projects.some(project => !replaySame(project, anchor.registry.projects.find(next => next.project_id === project.project_id)))) throw new BrowserPersistenceError('stale_lineage')
        }
        // Only this account's known, owner-free replay cache can be rebuilt.
        for (const name of ['inbox', 'cursors', 'replayManifest']) tx.objectStore(name).delete(range(s.accountId))
        tx.objectStore('identities').put({ record_version: 1, canonical_user_id: s.canonicalUserId, local_account_id: s.accountId, device_id: s.deviceId })
        tx.objectStore('accountBindings').put({ record_version: 1, local_account_id: s.accountId, canonical_user_id: s.canonicalUserId })
        tx.objectStore('cursors').put({ record_version: 1, account_id: s.accountId, device_id: s.deviceId, pull_cursor: 0, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 1 })
        const manifest: ReplayManifest = { record_version: 1, contract_version: 1, account_id: s.accountId, canonical_user_id: s.canonicalUserId, device_id: s.deviceId,
          generation: crypto.randomUUID(), anchor, receive_cursor: 0, ciphertext_bytes: 0, phase: 'receiving', revision: 1 }
        tx.objectStore('replayManifest').put(manifest); result(undefined)
      } catch (error) { abort(error) }
    }, abort))
    return this.read()
  }
  async commitPage(input: ReplaySnapshot, since: number, raw: string): Promise<ReplaySnapshot> {
    const expected = structuredClone(input), manifest = expected.manifest
    if (!manifest) fail()
    if (manifest.revision === Number.MAX_SAFE_INTEGER) fail()
    const { page, bytes } = prepareReplayPage(raw, since, this.scope, manifest.anchor)
    const replay = since < manifest.receive_cursor && page.next_cursor === manifest.receive_cursor
    const nextBytes = manifest.ciphertext_bytes + (replay ? 0 : bytes)
    const nextManifest = replay ? manifest : { ...manifest, receive_cursor: page.next_cursor, ciphertext_bytes: nextBytes, phase: 'receiving' as const, revision: manifest.revision + 1 }
    const newRows: BrowserReceivedInboxRecord[] = replay ? [] : page.items.map(item => ({ record_version: 1, account_id: this.scope.accountId, device_id: this.scope.deviceId,
      event_id: item.event.event_id, server_sequence: item.event.server_sequence!, protocol_version: 3, state: 'received', wire_item: JSON.stringify(item) }))
    // Match the persisted row representation, including escaped wire_item JSON.
    // Reserve bounds the three fixed-shape identity/binding/cursor control rows.
    const retainedBytes = [...expected.rows, ...newRows].reduce((total, row) => total + new TextEncoder().encode(JSON.stringify(row)).length,
      REPLAY_LIMITS.controlReserveBytes + new TextEncoder().encode(JSON.stringify(nextManifest)).length)
    if (nextBytes > REPLAY_LIMITS.ciphertextBytes || retainedBytes > REPLAY_LIMITS.inventoryBytes) throw new BrowserPersistenceError('source_limit')
    const transaction: BrowserSyncTransaction = (scope, _stores, mode, schedule) => {
      if (!replaySame(scope, this.scope) || mode !== 'readwrite') fail()
      return this.run(mode, (tx, result, abort) => this.load(tx, now => {
        try {
          if (!replaySame(now, expected)) throw new BrowserPersistenceError('stale_cursor')
          schedule(tx, value => {
            try {
              this.check()
              if (!replay) tx.objectStore('replayManifest').put(nextManifest)
              result(value)
            } catch (error) { abort(error) }
          }, abort)
        } catch (error) { abort(error) }
      }, abort))
    }
    await new BrowserSyncDurability(transaction).commitInboundPage(this.scope, since, raw)
    return this.read()
  }
  async finish(input: ReplaySnapshot): Promise<ReplaySnapshot> {
    const expected = structuredClone(input)
    await this.run('readwrite', (tx, result, abort) => this.load(tx, now => {
      try {
        if (!replaySame(now, expected)) throw new BrowserPersistenceError('stale_cursor')
        const manifest = now.manifest
        if (!manifest || manifest.receive_cursor !== manifest.anchor.registry.current_cursor) fail()
        if (manifest.revision === Number.MAX_SAFE_INTEGER) fail()
        if (manifest.phase !== 'received') tx.objectStore('replayManifest').put({ ...manifest, phase: 'received', revision: manifest.revision + 1 })
        result(undefined)
      } catch (error) { abort(error) }
    }, abort))
    return this.read()
  }
}

export type ReplayStorage = Pick<BrowserReplayStorage, 'start' | 'read' | 'commitPage' | 'finish' | 'close'>

export async function openBrowserReplayStorage(input: BrowserSyncScope, signal: AbortSignal, current: () => boolean): Promise<ReplayStorage> {
  const scope = snapshotBrowserSyncScope(input)
  if (![scope.accountId, scope.canonicalUserId, scope.deviceId].every(replayUuid)) throw new BrowserPersistenceError('account_mismatch')
  if (signal.aborted || !current()) throw new BrowserPersistenceError('closed')
  if (typeof window === 'undefined' || !globalThis.isSecureContext || !globalThis.indexedDB || !navigator.locks) throw new BrowserPersistenceError('unavailable')
  const controller = new AbortController(), cancel = () => controller.abort()
  signal.addEventListener('abort', cancel, { once: true }); window.addEventListener('pagehide', cancel, { once: true })
  const cleanup = () => { signal.removeEventListener('abort', cancel); window.removeEventListener('pagehide', cancel) }
  let resolve!: (store: ReplayStorage) => void, reject!: (error: unknown) => void, store: BrowserReplayStorage | undefined
  const ready = new Promise<ReplayStorage>((yes, no) => { resolve = yes; reject = no })
  let flight: Promise<unknown>
  try { flight = navigator.locks.request(`${REPLAY_DATABASE_NAME}:writer`, { mode: 'exclusive', ifAvailable: true }, async lock => {
    if (controller.signal.aborted || !current()) throw new BrowserPersistenceError('closed')
    if (!lock) throw new BrowserPersistenceError('writer_busy')
    const db = await openDatabase(controller.signal)
    if (controller.signal.aborted || !current()) { db.close(); throw new BrowserPersistenceError('closed') }
    let release!: () => void
    const held = new Promise<void>(yes => { release = yes })
    store = new BrowserReplayStorage(db, scope, controller.signal, current, release, () => flight, cleanup)
    resolve(store)
    await held
  }) } catch (error) { cleanup(); throw persistenceError(error) }
  void flight.catch(error => { cleanup(); reject(persistenceError(error)); if (store) void store.close() })
  return ready
}
