import { acceptUnsealedConflicts } from './browser-note-unsealed-conflict-acceptance.mjs'
import { acceptNoteIntents } from './browser-note-intent-acceptance.mjs'
import { acceptNoteHistory } from './browser-note-history-acceptance.mjs'
import { acceptLegacyNoteApply } from './browser-legacy-note-apply-acceptance.mjs'
/** Real Chromium IDB/Web Locks on a disposable disk profile; isolated auth transport fixtures, actual storage/crypto runtimes. */
import assert from 'node:assert/strict'
import { acceptAccountRegistry } from './browser-account-registry-acceptance.mjs'
import { acceptBootstrapCompletion } from './browser-bootstrap-completion-acceptance.mjs'
import { acceptInitialNotes } from './browser-initial-note-acceptance.mjs'
import { acceptLocalAuthority } from './browser-local-authority-acceptance.mjs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'c21-persistence-'))
const users = ['11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222', '33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444']
const cases = []
let context
const unexpected = []
const completionRequests = []
const registryRequests = []
const ackRequests = []
async function start() {
  context = await chromium.launchPersistentContext(directory, { headless: true })
  context.on('request', request => { const path = new URL(request.url()).pathname; if (!path.startsWith('/api/')) return; if (request.method() === 'POST' && /^\/api\/v1\/cloud\/projects\/[^/]+\/bootstrap\/complete$/.test(path)) completionRequests.push({ path, body: request.postDataJSON() }); else if(request.method()==='GET'&&path==='/api/v1/cloud/projects/bootstrap')registryRequests.push(path); else { if(path.includes('/sync/ack'))ackRequests.push(path); unexpected.push('unrelated API request') } })
}
async function tab() {
  const page = await context.newPage()
  page.on('pageerror', () => unexpected.push('pageerror'))
  await page.goto(`${origin}/scripts/browser-persistence-harness.html`)
  await page.evaluate(async users => {
    globalThis.users = users
    globalThis.nativeRows = async store => {
      const db = await new Promise((resolve, reject) => {
        const request = indexedDB.open(c21.WEB_DATABASE_NAME)
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(Error('inspection_open_failed'))
      })
      try { return await new Promise((resolve, reject) => {
        const request = db.transaction(store).objectStore(store).getAll()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(Error('inspection_read_failed'))
      }) } finally { db.close() }
    }
  }, users)
  return page
}
async function expectCode(page, operation, code) {
  const result = await page.evaluate(async operation => {
    try { await (new Function(`return (async () => (${operation}))()`))(); return 'unexpected_success' }
    catch (error) { return error.code ?? 'untyped_failure' }
  }, operation)
  assert.equal(result, code)
}
try {
  await start()
  let page = await tab()
  // Actual C21.1.02 schema/data, upgraded by the production opener without recreation.
  const seed = { local_account_id: '77777777-7777-4777-8777-777777777777', device_id: '88888888-8888-4888-8888-888888888888' }
  await page.evaluate(async seed => {
    const request = indexedDB.open(c21.WEB_DATABASE_NAME, 1)
    request.onupgradeneeded = () => {
      const identities = request.result.createObjectStore('identities', { keyPath: 'canonical_user_id' })
      identities.createIndex('local_account_id', 'local_account_id', { unique: true })
      identities.createIndex('device_id', 'device_id', { unique: true })
      const bindings = request.result.createObjectStore('accountBindings', { keyPath: 'local_account_id' })
      bindings.createIndex('canonical_user_id', 'canonical_user_id', { unique: true })
    }
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(Error('v1_fixture_open_failed')) })
    try { await c21.runBrowserTransaction(db, ['identities', 'accountBindings'], 'readwrite', (tx, result) => {
      tx.objectStore('identities').add({ ...seed, canonical_user_id: users[0], record_version: 1 })
      tx.objectStore('accountBindings').add({ local_account_id: seed.local_account_id, canonical_user_id: users[0], record_version: 1 })
      result(undefined)
    }) } finally { db.close() }
  }, seed)
  const original = await page.evaluate(async () => {
    globalThis.session = await c21.openBrowserPersistence(users[0])
    return session.read(users[0])
  })
  const rows = await page.evaluate(() => nativeRows('identities'))
  assert.equal(rows.length, 1)
  assert.deepEqual(Object.keys(rows[0]).sort(), ['canonical_user_id', 'device_id', 'local_account_id', 'record_version'])
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).length, 1)
  assert.deepEqual(original, seed)
  cases.push('real v1 to current schema migration preserves exact identity/binding')
  const scopeA = { canonicalUserId: users[0], accountId: original.local_account_id, deviceId: original.device_id }
  const object = { crypto_version: 1, aad_version: 1, nonce: Buffer.alloc(24, 3).toString('base64url'), ciphertext: Buffer.alloc(32, 7).toString('base64url') }
  const note = { event: { event_id: '55555555-5555-4555-8555-555555555555', project_id: 'opaque-project', entity_id: 'opaque-note', entity_type: 'note', operation: 'upsert', revision: 1, updated_at: '2026-10-11T00:00:00Z', deleted_at: null }, object }
  const account = { event: { event_id: '66666666-6666-4666-8666-666666666666', canonical_user_id: users[0], scope: 'account', entity_id: 'opaque-folder', entity_type: 'folder', operation: 'upsert', revision: 1, updated_at: note.event.updated_at, deleted_at: null }, object: { ...object, crypto_version: 2, aad_version: 2 } }
  const bodies = [note, account].map((item, index) => JSON.stringify({ protocol_version: index === 0 ? 2 : 3, encrypted_sync_version: index === 0 ? 2 : 3, device_id: original.device_id, items: [item] }))
  const inbound = JSON.stringify({ protocol_version: 3, encrypted_sync_version: 3, items: [note, account].map((item, index) => ({ ...item, event: { ...item.event, device_id: original.device_id, server_sequence: index + 1 } })), next_cursor: 2, has_more: false })
  const queued = await page.evaluate(({ scope, bodies }) => session.sync.enqueue(scope, bodies), { scope: scopeA, bodies })
  assert.deepEqual(queued.map(row => [row.status, row.item.local_ordinal, row.item.raw_body]), bodies.map((raw, index) => ['enqueued', index + 1, raw]))
  const duplicate = await page.evaluate(({ scope, bodies }) => session.sync.enqueue(scope, bodies.map(raw => JSON.stringify(JSON.parse(raw), null, 2))), { scope: scopeA, bodies })
  assert.deepEqual(duplicate.map(row => [row.status, row.item.raw_body]), bodies.map(raw => ['already_enqueued', raw]))
  assert.deepEqual(await page.evaluate(({ scope, inbound }) => session.sync.commitInboundPage(scope, 0, inbound), { scope: scopeA, inbound }), { committed_cursor: 2, new_events: 2, replayed_events: 0, has_more: false })
  assert.deepEqual(await page.evaluate(({ scope, inbound }) => session.sync.commitInboundPage(scope, 0, inbound), { scope: scopeA, inbound }), { committed_cursor: 2, new_events: 0, replayed_events: 2, has_more: false })
  const durability = async target => target.evaluate(async scope => ({ outbox: await session.sync.listSealed(scope), inbox: await session.sync.listReceived(scope), cursor: await session.sync.readCheckpoint(scope) }), scopeA)
  const saved = await durability(page)
  assert.deepEqual(saved.cursor, { pull_cursor: 2, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 3 })
  assert.equal(saved.inbox.length, 2)
  cases.push('sealed v2/v3 exact bodies and mixed v3 inbox page commit; common cursor and ACK zero')
  await page.evaluate(scope => { globalThis.scopeA = scope }, scopeA)
  const changed = JSON.parse(bodies[0]); changed.items[0].object.ciphertext = Buffer.alloc(32, 8).toString('base64url')
  const nextBody = JSON.parse(bodies[0]); nextBody.items[0].event.event_id = '99999999-9999-4999-8999-999999999999'
  const batchFailure = await page.evaluate(async ({ scope, first, conflicting }) => {
    try { await session.sync.enqueue(scope, [first, conflicting]); return 'unexpected_success' } catch (error) { return error.code }
  }, { scope: scopeA, first: JSON.stringify(nextBody), conflicting: JSON.stringify(changed) })
  assert.equal(batchFailure, 'conflicting_record')
  assert.deepEqual(await durability(page), saved)
  cases.push('duplicate encrypted identity conflict rolls back earlier queued outbox and ordinal')

  await page.reload()
  await page.evaluate(async users => { globalThis.users = users; globalThis.session = await c21.openBrowserPersistence(users[0]) }, users)
  assert.deepEqual(await page.evaluate(() => session.read(users[0])), original)
  assert.deepEqual(await durability(page), saved)
  cases.push('reload preserves identity, sealed outbox bytes, received inbox and common cursor')

  await expectCode(page, 'session.read(users[1])', 'account_mismatch')
  await page.evaluate(async () => { globalThis.old = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  await expectCode(page, 'old.read(users[0])', 'closed')
  const isolation = await page.evaluate(async scope => {
    try { await session.sync.listSealed(scope); return 'unexpected_success' } catch (error) { return error.code }
  }, scopeA)
  assert.equal(isolation, 'account_mismatch')
  const second = await page.evaluate(() => session.read(users[1]))
  const scopeB = { canonicalUserId: users[1], accountId: second.local_account_id, deviceId: second.device_id }
  assert.deepEqual(await page.evaluate(async scope => [await session.sync.listSealed(scope), await session.sync.listReceived(scope), await session.sync.readCheckpoint(scope)], scopeB), [[], [], { pull_cursor: 0, ack_cursor: 0, proven_prefix: 0, next_local_ordinal: 1 }])
  const foreignAccount = JSON.parse(inbound); foreignAccount.items = [foreignAccount.items[1]]
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 0, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeB, raw: JSON.stringify(foreignAccount) }), 'account_mismatch')
  assert.notEqual(second.local_account_id, original.local_account_id)
  assert.notEqual(second.device_id, original.device_id)
  await page.evaluate(value => { globalThis.firstAccountId = value }, original.local_account_id)
  await expectCode(page, 'session.ensure(firstAccountId, users[1])', 'account_mismatch')
  await page.evaluate(async () => { await session.close(); globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await page.evaluate(() => session.read(users[0])), original)
  cases.push('account isolation and logout preserve durable records')

  let secondTab = await tab()
  await expectCode(secondTab, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await expectCode(secondTab, 'c21.openBrowserPersistence(users[1])', 'writer_busy')
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await page.close() // Browser lifecycle releases lock even without explicit logout.
  assert.deepEqual(await secondTab.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]); return session.read(users[0]) }), original)
  cases.push('second/same tab and different account excluded; owner termination transfers lock')
  await secondTab.evaluate(() => session.close())
  await context.close()
  await start()
  page = await tab()
  assert.deepEqual(await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]); return session.read(users[0]) }), original)
  assert.deepEqual(await durability(page), saved)
  cases.push('browser process/profile reopen preserves byte-identical outbox, encrypted inbox and cursor')
  const nextPage = JSON.parse(inbound); nextPage.items = [{ ...nextPage.items[0], event: { ...nextPage.items[0].event, event_id: nextBody.items[0].event.event_id, server_sequence: 3 } }]; nextPage.next_cursor = 3
  const cursorAbort = await page.evaluate(async ({ scope, raw }) => {
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(...args) { if (this.name === 'cursors') throw new DOMException('NOT_LOGGED', 'QuotaExceededError'); return put.apply(this, args) }
    try { await session.sync.commitInboundPage(scope, 2, raw); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.put = put }
  }, { scope: scopeA, raw: JSON.stringify(nextPage) })
  assert.equal(cursorAbort, 'quota_exceeded')
  assert.deepEqual(await durability(page), saved)
  const enqueueAbort = await page.evaluate(async ({ scope, raw }) => {
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(...args) { if (this.name === 'cursors') throw new DOMException('NOT_LOGGED', 'QuotaExceededError'); return put.apply(this, args) }
    try { await session.sync.enqueue(scope, [raw]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.put = put }
  }, { scope: scopeA, raw: JSON.stringify(nextBody) })
  assert.equal(enqueueAbort, 'quota_exceeded')
  assert.deepEqual(await durability(page), saved)
  cases.push('cursor quota failure atomically rolls back queued inbox/outbox and ordinal/pull position')
  const changedInbound = JSON.parse(inbound); changedInbound.items[0].object.ciphertext = changed.items[0].object.ciphertext
  const replayConflict = await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 0, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: JSON.stringify(changedInbound) })
  assert.equal(replayConflict, 'conflicting_record')
  const partialReplay = JSON.parse(inbound); partialReplay.items = [partialReplay.items[1]]
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 0, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: JSON.stringify(partialReplay) }), 'conflicting_record')
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 1, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: JSON.stringify(nextPage) }), 'stale_cursor')
  const empty = JSON.stringify({ protocol_version: 3, encrypted_sync_version: 3, items: [], next_cursor: 2, has_more: false })
  assert.equal((await page.evaluate(({ scope, raw }) => session.sync.commitInboundPage(scope, 2, raw), { scope: scopeA, raw: empty })).committed_cursor, 2)
  assert.deepEqual(await durability(page), saved)
  cases.push('conflicting/incomplete replay and stale cursor fail closed; empty page cannot advance')
  const deviceMismatch = await page.evaluate(async scope => { try { await session.sync.readCheckpoint({ ...scope, deviceId: users[1] }); return 'unexpected_success' } catch (error) { return error.code } }, scopeA)
  assert.equal(deviceMismatch, 'account_mismatch')
  await context.close(); await start(); page = await tab()
  assert.deepEqual(await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]); return session.read(users[0]) }), original)
  assert.deepEqual(await durability(page), saved)
  cases.push('process reopen after failed transactions retains only committed encrypted rows and old cursor/ordinal')

  await page.evaluate(async () => { const read = session.read(users[0]); const close = session.resetForLogout(); const result = await read.then(() => 'unexpected_success', error => error.code); await close; if (result !== 'closed') throw Error('logout_drain_failed') })
  await expectCode(page, 'session.provision(users[0])', 'closed')
  assert.equal(await page.evaluate(async scope => { try { await session.sync.listReceived(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'closed')
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await durability(page), saved)
  const logoutEnqueue = await page.evaluate(async ({ scope, raw }) => {
    const operation = session.sync.enqueue(scope, [raw]), closing = session.resetForLogout()
    const code = await operation.then(() => 'unexpected_success', error => error.code)
    await closing; return code
  }, { scope: scopeA, raw: JSON.stringify(nextBody) })
  assert.equal(logoutEnqueue, 'closed')
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await durability(page), saved)
  await page.evaluate(() => session.close())
  cases.push('logout revokes stale sync handles and aborts enqueue without erasing encrypted durability')

  const quota = await page.evaluate(async () => {
    const add = IDBObjectStore.prototype.add
    IDBObjectStore.prototype.add = function(...args) {
      if (this.name === 'accountBindings') throw new DOMException('NOT_LOGGED', 'QuotaExceededError')
      return add.apply(this, args)
    }
    try { await c21.openBrowserPersistence(users[2]); return 'unexpected_success' }
    catch (error) { return error.code }
    finally { IDBObjectStore.prototype.add = add }
  })
  assert.equal(quota, 'quota_exceeded')
  assert.equal((await page.evaluate(() => nativeRows('identities'))).some(row => row.canonical_user_id === users[2]), false)
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).some(row => row.canonical_user_id === users[2]), false)
  cases.push('injected quota failure rolls back both stores; typed blocker')

  const constraint = await page.evaluate(async firstAccountId => {
    const add = IDBObjectStore.prototype.add
    IDBObjectStore.prototype.add = function(value, ...rest) {
      if (this.name === 'accountBindings') value = { ...value, local_account_id: firstAccountId }
      return add.call(this, value, ...rest)
    }
    try { await c21.openBrowserPersistence(users[3]); return 'unexpected_success' }
    catch (error) { return error.code }
    finally { IDBObjectStore.prototype.add = add }
  }, original.local_account_id)
  assert.equal(constraint, 'storage_failed')
  assert.equal((await page.evaluate(() => nativeRows('identities'))).some(row => row.canonical_user_id === users[3]), false)
  cases.push('real asynchronous constraint error aborts partial transaction')

  const cancelledCreation = await page.evaluate(async () => {
    const controller = new AbortController(), add = IDBObjectStore.prototype.add
    IDBObjectStore.prototype.add = function(...args) {
      if (this.name === 'accountBindings') controller.abort()
      return add.apply(this, args)
    }
    try { await c21.openBrowserPersistence(users[2], controller.signal); return 'unexpected_success' }
    catch (error) { return error.code }
    finally { IDBObjectStore.prototype.add = add }
  })
  assert.equal(cancelledCreation, 'closed')
  assert.equal((await page.evaluate(() => nativeRows('identities'))).some(row => row.canonical_user_id === users[2]), false)
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).some(row => row.canonical_user_id === users[2]), false)
  cases.push('cancellation during provision aborts queued identity and binding writes')

  await page.evaluate(async () => {
    const db = await new Promise(resolve => { const request = indexedDB.open(c21.WEB_DATABASE_NAME); request.onsuccess = () => resolve(request.result) })
    try { await c21.runBrowserTransaction(db, ['accountBindings'], 'readwrite', (transaction, result) => {
      const store = transaction.objectStore('accountBindings'), request = store.index('canonical_user_id').get(users[0])
      request.onsuccess = () => { store.put({ ...request.result, record_version: 99 }); result(undefined) }
    }) } finally { db.close() }
  })
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).find(row => row.canonical_user_id === users[0]).record_version, 99)
  await page.evaluate(async () => {
    const db = await new Promise(resolve => { const request = indexedDB.open(c21.WEB_DATABASE_NAME); request.onsuccess = () => resolve(request.result) })
    try { await c21.runBrowserTransaction(db, ['accountBindings'], 'readwrite', (transaction, result) => {
      const store = transaction.objectStore('accountBindings'), request = store.index('canonical_user_id').get(users[0])
      request.onsuccess = () => { store.put({ ...request.result, record_version: 1 }); result(undefined) }
    }) } finally { db.close() }
  })
  cases.push('unknown binding record rejected without rewriting or regenerating identity')

  const missingLock = await page.evaluate(async () => {
    const descriptor = Object.getOwnPropertyDescriptor(navigator, 'locks')
    Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' }
    catch (error) { return error.code }
    finally { if (descriptor) Object.defineProperty(navigator, 'locks', descriptor); else delete navigator.locks }
  })
  assert.equal(missingLock, 'unavailable')
  const disabled = await page.evaluate(async () => {
    const descriptor = Object.getOwnPropertyDescriptor(window, 'indexedDB')
    Object.defineProperty(window, 'indexedDB', { configurable: true, get() { throw new DOMException('NOT_LOGGED', 'SecurityError') } })
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' }
    catch (error) { return error.code }
    finally { if (descriptor) Object.defineProperty(window, 'indexedDB', descriptor); else delete window.indexedDB }
  })
  assert.equal(disabled, 'unavailable')
  cases.push('missing locks / storage-disabled fail closed without fallback')

  const invalidated = await page.evaluate(async () => {
    const controller = new AbortController()
    globalThis.session = await c21.openBrowserPersistence(users[0], controller.signal)
    controller.abort()
    await session.close()
    try { await session.read(users[0]); return 'unexpected_success' }
    catch (error) { return error.code }
  })
  assert.equal(invalidated, 'closed')
  cases.push('external lifecycle/key-context reset revokes session')

  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]); await session.close() })
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  const third = await page.evaluate(({ scope, raw }) => session.sync.enqueue(scope, [raw]), { scope: scopeA, raw: JSON.stringify(nextBody) })
  saved.outbox.push(third[0].item); saved.cursor.next_local_ordinal = 4
  const alteredEcho = JSON.parse(JSON.stringify(nextPage)); alteredEcho.items[0].object.ciphertext = changed.items[0].object.ciphertext
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 2, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: JSON.stringify(alteredEcho) }), 'conflicting_record')
  assert.deepEqual(await durability(page), saved)
  await page.evaluate(() => session.close())
  cases.push('first own echo must match immutable sealed outbox metadata/ciphertext before receipt cursor can advance')
  const savedCursorRow = (await page.evaluate(() => nativeRows('cursors')))[0]
  await page.evaluate(async scope => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['cursors'], 'readwrite', (tx, result) => { tx.objectStore('cursors').delete([scope.accountId, scope.deviceId]); result(undefined) }) } finally { db.close() }
    globalThis.session = await c21.openBrowserPersistence(users[0])
  }, scopeA)
  assert.equal(await page.evaluate(async scope => { try { await session.sync.readCheckpoint(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'corrupt_record')
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.enqueue(scope, [raw]); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: JSON.stringify(nextBody) }), 'corrupt_record')
  assert.equal(await page.evaluate(async ({ scope, raw }) => { try { await session.sync.commitInboundPage(scope, 0, raw); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, raw: inbound }), 'corrupt_record')
  await page.evaluate(async row => {
    await session.close()
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['cursors'], 'readwrite', (tx, result) => { tx.objectStore('cursors').add(row); result(undefined) }) } finally { db.close() }
  }, savedCursorRow)
  cases.push('missing cursor with retained encrypted records blocks reads and writes without inventing a fresh position')

  await page.evaluate(async scope => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['inbox'], 'readwrite', (tx, result) => {
      const store = tx.objectStore('inbox'), r = store.get([scope.accountId, 1])
      r.onsuccess = () => { store.put({ ...r.result, record_version: 99 }); result(undefined) }
    }) } finally { db.close() }
    globalThis.session = await c21.openBrowserPersistence(users[0])
  }, scopeA)
  assert.equal(await page.evaluate(async scope => { try { await session.sync.listReceived(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'corrupt_record')
  assert.equal((await page.evaluate(() => nativeRows('inbox')))[0].record_version, 99)
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA), saved.cursor)
  await page.evaluate(async row => {
    await session.close()
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['inbox'], 'readwrite', (tx, result) => { tx.objectStore('inbox').put(row); result(undefined) }) } finally { db.close() }
  }, saved.inbox[0])
  cases.push('unsupported persisted inbox record remains retained and blocks reads without cursor advancement')
  await page.evaluate(async () => {
    globalThis.session = await c21.openBrowserPersistence(users[0])
    await new Promise((resolve, reject) => {
      const request = indexedDB.open(c21.WEB_DATABASE_NAME, c21.WEB_DATABASE_VERSION + 1)
      request.onsuccess = () => { request.result.close(); resolve() }
      request.onerror = () => reject(Error('future_fixture_failed'))
    })
  })
  await expectCode(page, 'session.read(users[0])', 'closed')
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'unsupported_version')
  assert.deepEqual(await page.evaluate(() => nativeRows('identities')), rows.concat([{ ...second, canonical_user_id: users[1], record_version: 1 }]))
  assert.deepEqual(await page.evaluate(() => nativeRows('outbox')), saved.outbox)
  assert.deepEqual(await page.evaluate(() => nativeRows('inbox')), saved.inbox)
  assert.deepEqual(await page.evaluate(() => nativeRows('cursors')), [savedCursorRow])
  cases.push('versionchange invalidates old connection; future version refuses downgrade and preserves identity and encrypted state')
  // Dedicated rollback fixtures after every valid-data/restart assertion above.
  await page.evaluate(async seed => {
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject; r.onblocked = reject })
    const r = indexedDB.open(c21.WEB_DATABASE_NAME, 1)
    r.onupgradeneeded = () => {
      const identities = r.result.createObjectStore('identities', { keyPath: 'canonical_user_id' })
      identities.createIndex('local_account_id', 'local_account_id', { unique: true }); identities.createIndex('device_id', 'device_id', { unique: true })
      r.result.createObjectStore('accountBindings', { keyPath: 'local_account_id' }).createIndex('canonical_user_id', 'canonical_user_id', { unique: true })
    }
    const db = await new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = reject })
    try { await c21.runBrowserTransaction(db, ['identities', 'accountBindings'], 'readwrite', (tx, result) => {
      tx.objectStore('identities').add({ ...seed, canonical_user_id: users[0], record_version: 1 })
      tx.objectStore('accountBindings').add({ local_account_id: seed.local_account_id, canonical_user_id: users[0], record_version: 99 }); result(undefined)
    }) } finally { db.close() }
  }, seed)
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
  const nativeSchema = () => page.evaluate(async () => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    const result = { version: db.version, stores: Array.from(db.objectStoreNames) }; db.close(); return result
  })
  assert.deepEqual(await nativeSchema(), { version: 1, stores: ['accountBindings', 'identities'] })
  assert.equal((await page.evaluate(() => nativeRows('accountBindings')))[0].record_version, 99)
  await page.evaluate(async seed => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['accountBindings'], 'readwrite', (tx, result) => { tx.objectStore('accountBindings').put({ local_account_id: seed.local_account_id, canonical_user_id: users[0], record_version: 1 }); result(undefined) }) } finally { db.close() }
  }, seed)
  const upgradeQuota = await page.evaluate(async () => {
    const create = IDBDatabase.prototype.createObjectStore
    IDBDatabase.prototype.createObjectStore = function(name, ...args) { if (name === 'inbox') throw new DOMException('NOT_LOGGED', 'QuotaExceededError'); return create.call(this, name, ...args) }
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBDatabase.prototype.createObjectStore = create }
  })
  assert.equal(upgradeQuota, 'quota_exceeded')
  assert.deepEqual(await nativeSchema(), { version: 1, stores: ['accountBindings', 'identities'] })
  assert.deepEqual((await page.evaluate(() => nativeRows('identities')))[0], { ...seed, canonical_user_id: users[0], record_version: 1 })
  assert.deepEqual(await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]); return session.read(users[0]) }), seed)
  await page.evaluate(() => session.close())
  cases.push('corrupt v1 record and quota upgrade failure abort migration without clearing data; safe retry upgrades')
  await page.evaluate(async () => {
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject; r.onblocked = reject })
    globalThis.session = await c21.openBrowserPersistence(users[0])
  })
  assert.deepEqual(await nativeSchema(), { version: 8, stores: ['accountBindings', 'cursors', 'identities', 'inbox', 'legacyNoteHistory', 'legacyNoteIntents', 'localNotes', 'localProjects', 'outbox', 'ownerHeads', 'projectBindings', 'receipts'] })
  assert.equal((await page.evaluate(() => nativeRows('identities'))).length, 1)
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).length, 1)
  assert.deepEqual(await page.evaluate(async () => [await nativeRows('outbox'), await nativeRows('inbox'), await nativeRows('cursors')]), [[], [], []])
  await page.evaluate(() => session.close())
  cases.push('fresh empty profile atomically creates the exact v8 twelve-store schema and identity/binding')
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  const freshIdentity = await page.evaluate(() => session.read(users[0]))
  const freshScope = { canonicalUserId: users[0], accountId: freshIdentity.local_account_id, deviceId: freshIdentity.device_id }
  const legacyPage = { protocol_version: 2, encrypted_sync_version: 2, items: [{ ...note, event: { ...note.event, device_id: original.device_id, server_sequence: 1 } }], next_cursor: 1, has_more: false }
  await page.evaluate(({ scope, raw }) => session.sync.commitInboundPage(scope, 0, raw), { scope: freshScope, raw: JSON.stringify(legacyPage) })
  const mode3Replay = { ...legacyPage, protocol_version: 3, encrypted_sync_version: 3 }
  assert.deepEqual(await page.evaluate(({ scope, raw }) => session.sync.commitInboundPage(scope, 0, raw), { scope: freshScope, raw: JSON.stringify(mode3Replay) }), { committed_cursor: 1, new_events: 0, replayed_events: 1, has_more: false })
  assert.equal((await page.evaluate(scope => session.sync.listReceived(scope), freshScope))[0].protocol_version, 2)
  await page.evaluate(() => session.close())
  cases.push('transport2 to mixed transport3 replay compares immutable metadata/bytes and retains original received record')
  // C21.1.03 v2 fixture containing every existing durable store, reconstructed only in this disposable profile.
  const v2 = { identities: [{ ...seed, canonical_user_id: users[0], record_version: 1 }], accountBindings: [{ local_account_id: seed.local_account_id, canonical_user_id: users[0], record_version: 1 }], outbox: saved.outbox, inbox: saved.inbox, cursors: [savedCursorRow] }
  await page.evaluate(async fixture => {
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject; r.onblocked = reject })
    const r = indexedDB.open(c21.WEB_DATABASE_NAME, 2)
    r.onupgradeneeded = () => {
      const identities = r.result.createObjectStore('identities', { keyPath: 'canonical_user_id' })
      identities.createIndex('local_account_id', 'local_account_id', { unique: true }); identities.createIndex('device_id', 'device_id', { unique: true })
      r.result.createObjectStore('accountBindings', { keyPath: 'local_account_id' }).createIndex('canonical_user_id', 'canonical_user_id', { unique: true })
      const outbox = r.result.createObjectStore('outbox', { keyPath: ['account_id', 'event_id'] })
      outbox.createIndex('ordinal', ['account_id', 'device_id', 'local_ordinal'], { unique: true }); outbox.createIndex('state', ['account_id', 'state', 'local_ordinal'])
      const inbox = r.result.createObjectStore('inbox', { keyPath: ['account_id', 'server_sequence'] })
      inbox.createIndex('event', ['account_id', 'event_id'], { unique: true }); inbox.createIndex('state', ['account_id', 'state', 'server_sequence'])
      r.result.createObjectStore('cursors', { keyPath: ['account_id', 'device_id'] })
    }
    const db = await new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = reject })
    try { await c21.runBrowserTransaction(db, Object.keys(fixture), 'readwrite', (tx, result) => {
      for (const [store, rows] of Object.entries(fixture)) for (const row of rows) tx.objectStore(store).add(store === 'outbox' ? { ...row, record_version: 99 } : row)
      result(undefined)
    }) } finally { db.close() }
  }, v2)
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
  assert.deepEqual(await nativeSchema(), { version: 2, stores: ['accountBindings', 'cursors', 'identities', 'inbox', 'outbox'] })
  assert.equal((await page.evaluate(() => nativeRows('outbox')))[0].record_version, 99)
  await page.evaluate(async rows => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['outbox'], 'readwrite', (tx, result) => { for (const row of rows) tx.objectStore('outbox').put(row); result(undefined) }) } finally { db.close() }
  }, v2.outbox)
  const receiptUpgradeQuota = await page.evaluate(async () => {
    const create = IDBDatabase.prototype.createObjectStore
    IDBDatabase.prototype.createObjectStore = function(name, ...args) { if (name === 'receipts') throw new DOMException('NOT_LOGGED', 'QuotaExceededError'); return create.call(this, name, ...args) }
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBDatabase.prototype.createObjectStore = create }
  })
  assert.equal(receiptUpgradeQuota, 'quota_exceeded')
  assert.deepEqual(await nativeSchema(), { version: 2, stores: ['accountBindings', 'cursors', 'identities', 'inbox', 'outbox'] })
  for (const [store, rows] of Object.entries(v2)) assert.deepEqual(await page.evaluate(store => nativeRows(store), store), rows)
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  for (const [store, rows] of Object.entries(v2)) assert.deepEqual(await page.evaluate(store => nativeRows(store), store), rows)
  assert.deepEqual(await page.evaluate(() => nativeRows('receipts')), [])
  cases.push('v2 to current schema preserves all five stores byte-for-byte; corrupt/quota upgrade failures leave v2 intact')
  const expected = v2.outbox[0]
  const uploadResponse = (row, sequence, duplicate = false) => ({ protocol_version: row.protocol_version, encrypted_sync_version: row.protocol_version, current_cursor: Math.max(2, sequence), results: [{ event_id: row.event_id, server_sequence: sequence, duplicate }] })
  const commit = (row, response) => page.evaluate(({ scope, row, response }) => session.sync.commitUploadAcceptance(scope, row, response), { scope: scopeA, row, response })
  const receiptRead = row => page.evaluate(({ scope, eventId }) => session.sync.readUploadReceipt(scope, eventId), { scope: scopeA, eventId: row.event_id })
  const retained = () => page.evaluate(scope => session.sync.listOutbox(scope), scopeA)
  assert.equal(await commit(expected, uploadResponse(expected, 1)), 'accepted')
  const firstProof = await receiptRead(expected), acceptedRow = { ...expected, state: 'accepted' }
  assert.deepEqual(await retained(), [acceptedRow, ...v2.outbox.slice(1)])
  assert.deepEqual(await page.evaluate(scope => session.sync.listSealed(scope, 1), scopeA), [v2.outbox[1]])
  assert.equal(firstProof.duplicate, false)
  assert.equal(await commit(expected, uploadResponse(expected, 1)), 'already_accepted')
  assert.equal(await commit(expected, { ...uploadResponse(expected, 1, true), current_cursor: 100 }), 'already_accepted')
  assert.deepEqual(await receiptRead(expected), firstProof)
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA), saved.cursor)
  cases.push('exact acceptance commits immutable receipt and retained accepted row; diagnostic replay keeps first proof and cursors')
  const rejection = async (row, response) => {
    const code = await page.evaluate(async ({ scope, row, response }) => { try { await session.sync.commitUploadAcceptance(scope, row, response); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, row, response })
    assert.equal(code, 'conflicting_record')
  }
  await rejection(expected, uploadResponse(expected, 8))
  await rejection({ ...expected, local_ordinal: 99 }, uploadResponse(expected, 1))
  const changedExpectedBody = JSON.parse(expected.raw_body); changedExpectedBody.items[0].object.ciphertext = changed.items[0].object.ciphertext
  await rejection({ ...expected, raw_body: JSON.stringify(changedExpectedBody) }, uploadResponse(expected, 1))
  await rejection(v2.outbox[1], uploadResponse(v2.outbox[1], 1))
  const unknownBody = JSON.parse(expected.raw_body); unknownBody.items[0].event.event_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
  const unknownExpected = { ...expected, event_id: unknownBody.items[0].event.event_id, raw_body: JSON.stringify(unknownBody) }
  await rejection(unknownExpected, uploadResponse(unknownExpected, 4))
  assert.deepEqual(await receiptRead(expected), firstProof)
  cases.push('conflicting sequence, exact-body/ordinal mismatch, sequence collision and unknown event fail closed')
  const retryEvent = v2.outbox[2], authority = uploadResponse(retryEvent, 3)
  const failedCommit = async mode => page.evaluate(async ({ scope, row, response, mode }) => {
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(value, ...args) {
      if (this.name === 'outbox') {
        if (mode === 'quota') throw new DOMException('NOT_LOGGED', 'QuotaExceededError')
        if (mode === 'abort') this.transaction.abort()
        if (mode === 'constraint') value = { ...value, local_ordinal: 1 }
      }
      return put.call(this, value, ...args)
    }
    try { await session.sync.commitUploadAcceptance(scope, row, response); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.put = put }
  }, { scope: scopeA, row: retryEvent, response: authority, mode })
  assert.equal(await failedCommit('quota'), 'quota_exceeded')
  assert.equal(await failedCommit('abort'), 'storage_failed')
  assert.equal(await failedCommit('constraint'), 'storage_failed')
  assert.equal(await receiptRead(retryEvent), null)
  assert.deepEqual((await retained())[2], retryEvent)
  assert.equal(await commit(retryEvent, uploadResponse(retryEvent, 3, true)), 'accepted')
  assert.equal((await receiptRead(retryEvent)).duplicate, true)
  assert.equal((await retained())[2].raw_body, retryEvent.raw_body)
  cases.push('server-success/local quota, explicit abort and real async constraint failure retain sealed retry bytes; duplicate response then commits')
  await page.reload()
  await page.evaluate(async users => { globalThis.users = users; globalThis.session = await c21.openBrowserPersistence(users[0]) }, users)
  assert.deepEqual(await receiptRead(expected), firstProof)
  assert.deepEqual((await retained())[0], acceptedRow)
  await context.close(); await start(); page = await tab()
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await receiptRead(expected), firstProof)
  assert.deepEqual((await retained())[0], acceptedRow)
  cases.push('receipt and accepted state survive reload and browser/profile reopen with original raw body')
  let competing = await tab()
  await expectCode(competing, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await page.close(); page = competing
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await receiptRead(expected), firstProof)
  cases.push('competing tab cannot bypass receipt writer ownership; owner termination transfers durable proof')
  await page.evaluate(async () => { globalThis.stale = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  const currentB = await page.evaluate(() => session.read(users[1]))
  const newScopeB = { canonicalUserId: users[1], accountId: currentB.local_account_id, deviceId: currentB.device_id }
  assert.equal(await page.evaluate(async ({ scope, eventId }) => { try { await session.sync.readUploadReceipt(scope, eventId); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, eventId: expected.event_id }), 'account_mismatch')
  assert.equal(await page.evaluate(({ scope, eventId }) => session.sync.readUploadReceipt(scope, eventId), { scope: newScopeB, eventId: expected.event_id }), null)
  assert.equal(await page.evaluate(async ({ scope, row, response }) => { try { await session.sync.commitUploadAcceptance(scope, row, response); return 'unexpected_success' } catch (error) { return error.code } }, { scope: newScopeB, row: expected, response: uploadResponse(expected, 1) }), 'corrupt_record')
  assert.equal(await page.evaluate(async ({ scope, eventId }) => { try { await stale.sync.readUploadReceipt(scope, eventId); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, eventId: expected.event_id }), 'closed')
  await page.evaluate(async () => { await session.close(); globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await receiptRead(expected), firstProof)
  cases.push('receipt account isolation and logout revocation retain immutable acceptance proof')
  const mutate = (store, action, value) => page.evaluate(async ({ store, action, value }) => {
    await session.close()
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, [store], 'readwrite', (tx, result) => { tx.objectStore(store)[action](value); result(undefined) }) } finally { db.close() }
    globalThis.session = await c21.openBrowserPersistence(users[0])
  }, { store, action, value })
  await mutate('receipts', 'delete', [scopeA.accountId, expected.event_id])
  assert.equal(await page.evaluate(async scope => { try { await session.sync.listSealed(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'corrupt_record')
  assert.equal(await page.evaluate(async ({ scope, eventId }) => { try { await session.sync.readUploadReceipt(scope, eventId); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, eventId: expected.event_id }), 'corrupt_record')
  await mutate('receipts', 'add', firstProof)
  await mutate('outbox', 'put', expected)
  assert.equal(await page.evaluate(async scope => { try { await session.sync.listSealed(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'corrupt_record')
  assert.equal(await page.evaluate(async ({ scope, row, response }) => { try { await session.sync.commitUploadAcceptance(scope, row, response); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, row: expected, response: uploadResponse(expected, 1) }), 'corrupt_record')
  assert.deepEqual((await page.evaluate(() => nativeRows('receipts'))).find(row => row.event_id === expected.event_id), firstProof)
  await mutate('outbox', 'put', acceptedRow)
  await mutate('outbox', 'put', { ...acceptedRow, state: 'unknown' })
  assert.equal(await page.evaluate(async scope => { try { await session.sync.listSealed(scope); return 'unexpected_success' } catch (error) { return error.code } }, scopeA), 'corrupt_record')
  await mutate('outbox', 'put', acceptedRow)
  assert.deepEqual(await receiptRead(expected), firstProof)
  assert.equal((await retained())[0].raw_body, expected.raw_body)
  cases.push('missing receipt, receipt-with-sealed-row and unknown state fail after reopen/read without silent repair')
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA), saved.cursor)
  await page.evaluate(() => session.close())
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  // C21.1.05: query existing retained v3 data only. No premature head/apply write or schema.
  const historyReferences = v2.outbox.map(row => {
    const proofSequence = row.event_id === expected.event_id ? 1 : row.event_id === retryEvent.event_id ? 3 : 2
    return { ...JSON.parse(row.raw_body).items[0].event, device_id: scopeA.deviceId, server_sequence: proofSequence }
  })
  const historyRead = target => target.evaluate(({ scope, references }) => session.sync.readRetainedHistory(scope, references), { scope: scopeA, references: historyReferences })
  const historyFailure = (references, scope = scopeA, handle = 'session') => page.evaluate(async ({ scope, references, handle }) => {
    try { await globalThis[handle].sync.readRetainedHistory(scope, references); return 'unexpected_success' } catch (error) { return error.code }
  }, { scope, references, handle })
  const allStores = ['identities', 'accountBindings', 'outbox', 'inbox', 'cursors', 'receipts']
  const durableSnapshot = async () => Object.fromEntries(await Promise.all(allStores.map(async store => [store, await page.evaluate(store => nativeRows(store), store)])))
  const historyBefore = await durableSnapshot()
  const historySaved = await historyRead(page)
  assert.equal(historySaved.length, 3)
  assert.deepEqual(historySaved.map(row => row.reference), [...historyReferences].sort((a, b) => a.event_id < b.event_id ? -1 : 1))
  assert.equal(historySaved.filter(row => row.inbox === null).length, 1)
  assert.equal(historySaved.filter(row => row.outbox === null).length, 1) // received-only unaccepted own echo
  assert.ok(historySaved.every(row => row.inbox === null || row.inbox.state === 'received'))
  assert.deepEqual(await page.evaluate(({ scope, references }) => session.sync.readRetainedHistory(scope, [...references].reverse()), { scope: scopeA, references: historyReferences }), historySaved)
  assert.deepEqual(await durableSnapshot(), historyBefore)
  cases.push('retained mixed project/account history reads exact descriptors and ciphertext in deterministic order without modifying six encrypted durability stores')
  assert.equal(await historyFailure([{ ...historyReferences[0], event_id: users[3] }, historyReferences[1]]), 'missing_history')
  assert.equal(await historyFailure([historyReferences[0], { ...historyReferences[0], revision: 2 }]), 'conflicting_record')
  for (const change of [{ entity_id: 'wrong-owner' }, { project_id: 'wrong-project' }, { server_sequence: 4 }, { revision: 2 }]) assert.equal(await historyFailure([{ ...historyReferences[0], ...change }]), 'conflicting_record')
  assert.equal(await historyFailure([{ ...historyReferences[1], canonical_user_id: users[1] }]), 'account_mismatch')
  assert.deepEqual(await durableSnapshot(), historyBefore)
  cases.push('missing/duplicate/conflicting revision, owner, sequence and cross-account references fail closed without partial history results or repair')
  const abortHistory = await page.evaluate(async ({ scope, references }) => {
    const get = IDBObjectStore.prototype.get
    IDBObjectStore.prototype.get = function(...args) {
      const request = get.apply(this, args)
      if (this.name === 'outbox') this.transaction.abort()
      return request
    }
    try { await session.sync.readRetainedHistory(scope, references); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.get = get }
  }, { scope: scopeA, references: historyReferences })
  assert.equal(abortHistory, 'storage_failed')
  assert.deepEqual(await durableSnapshot(), historyBefore)
  assert.deepEqual(await historyRead(page), historySaved)
  cases.push('real IDB read transaction abort rejects whole history batch and preserves original retained records')
  await page.reload()
  await page.evaluate(async users => { globalThis.users = users; globalThis.session = await c21.openBrowserPersistence(users[0]) }, users)
  assert.deepEqual(await historyRead(page), historySaved)
  await context.close(); await start(); page = await tab()
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await historyRead(page), historySaved)
  assert.deepEqual(await durableSnapshot(), historyBefore)
  cases.push('retained encrypted references and deterministic history reads survive reload and disk profile/browser reopen unchanged')
  competing = await tab()
  await expectCode(competing, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await page.close(); page = competing
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await historyRead(page), historySaved)
  cases.push('history repository shares exclusive native Web Locks; owner termination transfers access without losing encrypted records')
  await page.evaluate(async () => { globalThis.stale = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  assert.equal(await historyFailure(historyReferences), 'account_mismatch')
  assert.equal(await historyFailure(historyReferences, newScopeB), 'account_mismatch') // account descriptor cannot cross canonical users
  assert.equal(await historyFailure([historyReferences[0]], newScopeB), 'missing_history')
  assert.equal(await historyFailure(historyReferences, scopeA, 'stale'), 'closed')
  await page.evaluate(async () => { await session.close(); globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await historyRead(page), historySaved)
  assert.deepEqual(await durableSnapshot(), historyBefore)
  cases.push('logout revokes stale history handles; foreign account reads fail and encrypted data remains retained')
  await mutate('receipts', 'delete', [scopeA.accountId, expected.event_id])
  assert.equal(await historyFailure(historyReferences), 'corrupt_record')
  await mutate('receipts', 'add', firstProof)
  await mutate('inbox', 'put', { ...historySaved[0].inbox, record_version: 99 })
  assert.equal(await historyFailure(historyReferences), 'corrupt_record')
  await mutate('inbox', 'put', historySaved[0].inbox)
  assert.deepEqual(await historyRead(page), historySaved)
  assert.deepEqual(await durableSnapshot(), historyBefore)
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA), saved.cursor)
  assert.deepEqual(await nativeSchema(), { version: 8, stores: [...allStores, 'projectBindings', 'ownerHeads', 'localProjects', 'localNotes','legacyNoteHistory','legacyNoteIntents'].sort() })
  cases.push('unknown retained record and broken acceptance half fail after reopen; no automatic repair, schema/head writes, apply proof or ACK advancement')
  // Accepted C21 v3 fixture: all six old stores, including immutable accepted bodies/receipts.
  const v3 = await durableSnapshot()
  await page.evaluate(async fixture => {
    await session.close()
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject })
    const open = indexedDB.open(c21.WEB_DATABASE_NAME, 3)
    open.onupgradeneeded = () => {
      const db = open.result
      const identities = db.createObjectStore('identities', { keyPath: 'canonical_user_id' })
      identities.createIndex('local_account_id', 'local_account_id', { unique: true }); identities.createIndex('device_id', 'device_id', { unique: true })
      db.createObjectStore('accountBindings', { keyPath: 'local_account_id' }).createIndex('canonical_user_id', 'canonical_user_id', { unique: true })
      const outbox = db.createObjectStore('outbox', { keyPath: ['account_id','event_id'] })
      outbox.createIndex('ordinal', ['account_id','device_id','local_ordinal'], { unique: true }); outbox.createIndex('state', ['account_id','state','local_ordinal'])
      const inbox = db.createObjectStore('inbox', { keyPath: ['account_id','server_sequence'] })
      inbox.createIndex('event', ['account_id','event_id'], { unique: true }); inbox.createIndex('state', ['account_id','state','server_sequence'])
      db.createObjectStore('cursors', { keyPath: ['account_id','device_id'] })
      db.createObjectStore('receipts', { keyPath: ['account_id','event_id'] }).createIndex('server_sequence', ['account_id','server_sequence'], { unique: true })
    }
    const db = await new Promise((resolve, reject) => { open.onsuccess = () => resolve(open.result); open.onerror = reject })
    try { await c21.runBrowserTransaction(db, Object.keys(fixture), 'readwrite', (tx, result) => {
      for (const [store, rows] of Object.entries(fixture)) for (const row of rows) tx.objectStore(store).add(store === 'receipts' ? { ...row, record_version: 99 } : row)
      result(undefined)
    }) } finally { db.close() }
  }, v3)
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
  assert.deepEqual(await nativeSchema(), { version: 3, stores: [...allStores].sort() })
  for (const store of allStores.filter(store => store !== 'receipts')) assert.deepEqual(await page.evaluate(store => nativeRows(store), store), v3[store])
  await page.evaluate(async proofs => {
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    try { await c21.runBrowserTransaction(db, ['receipts'], 'readwrite', (tx, result) => { for (const row of proofs) tx.objectStore('receipts').put(row); result(undefined) }) } finally { db.close() }
  }, v3.receipts)
  await page.evaluate(async () => {
    globalThis.upgradeBlocker = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME, 3); r.onsuccess = () => resolve(r.result) })
  })
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'upgrade_blocked')
  await page.evaluate(() => upgradeBlocker.close())
  assert.deepEqual(await nativeSchema(), { version: 3, stores: [...allStores].sort() })
  assert.deepEqual(await durableSnapshot(), v3)
  const lineageUpgradeAbort = await page.evaluate(async () => {
    const getAll = IDBObjectStore.prototype.getAll
    IDBObjectStore.prototype.getAll = function(...args) {
      const request = getAll.apply(this, args)
      if (this.name === 'outbox') this.transaction.abort()
      return request
    }
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.getAll = getAll }
  })
  assert.equal(lineageUpgradeAbort, 'storage_failed')
  assert.deepEqual(await nativeSchema(), { version: 3, stores: [...allStores].sort() })
  assert.deepEqual(await durableSnapshot(), v3)
  const lineageUpgradeQuota = await page.evaluate(async () => {
    const create = IDBDatabase.prototype.createObjectStore
    IDBDatabase.prototype.createObjectStore = function(name, ...args) { if (name === 'projectBindings') throw new DOMException('NOT_LOGGED', 'QuotaExceededError'); return create.call(this, name, ...args) }
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBDatabase.prototype.createObjectStore = create }
  })
  assert.equal(lineageUpgradeQuota, 'quota_exceeded')
  assert.deepEqual(await nativeSchema(), { version: 3, stores: [...allStores].sort() })
  assert.deepEqual(await durableSnapshot(), v3)
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await nativeSchema(), { version: 8, stores: [...allStores, 'projectBindings', 'ownerHeads', 'localProjects', 'localNotes','legacyNoteHistory','legacyNoteIntents'].sort() })
  assert.deepEqual(await durableSnapshot(), v3)
  assert.deepEqual(await page.evaluate(() => nativeRows('projectBindings')), [])
  cases.push('real v3 to current v6 preserves all six legacy stores including accepted ciphertext/receipts; corrupt/quota/request-abort/blocked-upgrade failures preserve intact v3, projectBindings starts empty')
  const projectId = note.event.project_id
  const projectRead = () => page.evaluate(({ scope, id }) => session.projects.read(scope, id), { scope: scopeA, id: projectId })
  assert.equal(await projectRead(), null)
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), scopeA), [])
  assert.deepEqual(await historyRead(page), historySaved)
  assert.equal(await projectRead(), null)
  cases.push('retained encrypted events, accepted upload receipts and retained-history reads cannot implicitly create project lineage')
  const preparedLineage = await page.evaluate(({ scope, id }) => session.projects.prepare(scope, { project_id: id, mode: 'upload_existing' }), { scope: scopeA, id: projectId })
  assert.equal(preparedLineage.phase, 'prepared'); assert.equal(preparedLineage.remote_state, null)
  assert.match(preparedLineage.bootstrap_id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
  assert.deepEqual(await projectRead(), preparedLineage)
  assert.deepEqual(await page.evaluate(({ scope, id }) => session.projects.prepare(scope, { project_id: id, mode: 'upload_existing' }), { scope: scopeA, id: projectId }), preparedLineage)
  const projectFailure = (operation, args) => page.evaluate(async ({ operation, args }) => {
    try { await session.projects[operation](...args); return 'unexpected_success' } catch (error) { return error.code ?? 'untyped_failure' }
  }, { operation, args })
  const registrationEvidence = { remote_state: 'initializing', remote_high_water: 5 }
  const registeredLineage = await page.evaluate(({ scope, expected, evidence }) => session.projects.confirmRegistration(scope, expected, evidence), { scope: scopeA, expected: preparedLineage, evidence: registrationEvidence })
  assert.deepEqual(registeredLineage, { ...preparedLineage, phase: 'registered', ...registrationEvidence })
  assert.deepEqual(await page.evaluate(({ scope, expected, evidence }) => session.projects.confirmRegistration(scope, expected, evidence), { scope: scopeA, expected: preparedLineage, evidence: registrationEvidence }), registeredLineage)
  assert.equal(await projectFailure('confirmRegistration', [scopeA, preparedLineage, { ...registrationEvidence, remote_high_water: 6 }]), 'stale_lineage')
  assert.equal(await projectFailure('confirmRegistration', [scopeA, { ...preparedLineage, bootstrap_id: users[3] }, registrationEvidence]), 'conflicting_record')
  assert.equal(await projectFailure('confirmRegistration', [scopeA, { ...preparedLineage, device_id: scopeA.accountId }, registrationEvidence]), 'corrupt_record')
  assert.equal(await projectFailure('confirmRegistration', [scopeA, registeredLineage, { ...registrationEvidence, ready: true }]), 'corrupt_record')
  assert.equal(await projectFailure('prepare', [scopeA, { project_id: projectId, mode: 'upload_existing', phase: 'ready', initial_event_count: 3 }]), 'corrupt_record')
  assert.deepEqual(await projectRead(), registeredLineage)
  cases.push('explicit upload-existing preparation generates immutable v4 lineage; exact registration CAS/retry succeeds, stale/wrong-lineage/device/phase/cohort updates reject')
  const abortLineage = await page.evaluate(async ({ scope, expected }) => {
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(...args) {
      const request = put.apply(this, args)
      if (this.name === 'projectBindings') this.transaction.abort()
      return request
    }
    try { await session.projects.confirmRegistration(scope, expected, { remote_state: 'active', remote_high_water: 8 }); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.put = put }
  }, { scope: scopeA, expected: registeredLineage })
  assert.equal(abortLineage, 'storage_failed')
  assert.deepEqual(await projectRead(), registeredLineage)
  assert.deepEqual(await durableSnapshot(), v3)
  cases.push('real IDB abort after queued project lineage replacement leaves old phase/high-water and six encrypted stores unchanged')
  const importedProject = 'imported-project', importedBootstrap = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
  const remoteDescriptor = { project_id: importedProject, bootstrap_id: importedBootstrap, remote_state: 'active', remote_high_water: 9 }
  const importedLineage = await page.evaluate(({ scope, descriptor }) => session.projects.importRemote(scope, descriptor), { scope: scopeA, descriptor: remoteDescriptor })
  assert.deepEqual(importedLineage, { record_version: 1, account_id: scopeA.accountId, device_id: scopeA.deviceId, project_id: importedProject, bootstrap_id: importedBootstrap, mode: 'import_remote', phase: 'captured', remote_state: 'active', remote_high_water: 9, initial_event_count: 0, initial_local_ordinal_hi: 0, initial_max_server_sequence: null, blocked_reason: null })
  assert.deepEqual(await page.evaluate(({ scope, descriptor }) => session.projects.importRemote(scope, descriptor), { scope: scopeA, descriptor: remoteDescriptor }), importedLineage)
  assert.deepEqual(await page.evaluate(async ({ scope, id, ignoredCandidate }) => {
    const uuid = crypto.randomUUID
    crypto.randomUUID = () => ignoredCandidate
    try { return await session.projects.prepare(scope, { project_id: id, mode: 'upload_existing' }) }
    finally { crypto.randomUUID = uuid }
  }, { scope: scopeA, id: projectId, ignoredCandidate: importedBootstrap }), registeredLineage)
  assert.equal(await projectFailure('importRemote', [scopeA, { ...remoteDescriptor, project_id: 'other-project' }]), 'conflicting_record')
  assert.equal(await projectFailure('importRemote', [scopeA, { ...remoteDescriptor, bootstrap_id: users[3] }]), 'conflicting_record')
  assert.equal(await projectFailure('importRemote', [scopeA, { ...remoteDescriptor, project_id: projectId }]), 'conflicting_record')
  assert.equal(await projectFailure('importRemote', [scopeA, { ...remoteDescriptor, remote_state: 'initializing' }]), 'corrupt_record')
  assert.deepEqual(await page.evaluate(({ scope, id }) => session.projects.evaluateReadiness(scope, id), { scope: scopeA, id: projectId }), { ready: false, code: 'capture_proof_unavailable', required_cursor: 5 })
  assert.deepEqual(await page.evaluate(({ scope, id }) => session.projects.evaluateReadiness(scope, id), { scope: scopeA, id: importedProject }), { ready: false, code: 'registry_reconciliation_required', required_cursor: 9 })
  assert.deepEqual(await page.evaluate(() => ['capture','markCompleting','markReady','setPaused','setPhase','patch'].map(name => name in session.projects)), [false,false,false,false,false,false])
  assert.deepEqual(await durableSnapshot(), v3)
  cases.push('explicit remote import is captured/active with zero local cohort; conflicting project/bootstrap reuse rejects; no capture/completing/ready/pause or arbitrary patch API and readiness remains blocked')
  const bindingsSaved = await page.evaluate(scope => session.projects.list(scope), scopeA)
  assert.deepEqual(bindingsSaved.map(row => row.project_id), [importedProject, projectId].sort())
  await page.reload()
  await page.evaluate(async users => { globalThis.users = users; globalThis.session = await c21.openBrowserPersistence(users[0]) }, users)
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), scopeA), bindingsSaved)
  await context.close(); await start(); page = await tab()
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), scopeA), bindingsSaved)
  cases.push('explicit project lineage survives reload and disk-profile/browser reopen with exact immutable fields, lifecycle and deterministic ordering')
  competing = await tab()
  await expectCode(competing, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await page.close(); page = competing
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await projectRead(), registeredLineage)
  await page.evaluate(async () => { globalThis.staleLineage = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  assert.equal(await projectFailure('read', [scopeA, projectId]), 'account_mismatch')
  assert.equal(await page.evaluate(({ scope, id }) => session.projects.read(scope, id), { scope: newScopeB, id: projectId }), null)
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), newScopeB), [])
  assert.equal(await page.evaluate(async ({ scope, expected }) => { try { await staleLineage.projects.confirmRegistration(scope, expected, { remote_state: 'active', remote_high_water: 8 }); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, expected: registeredLineage }), 'closed')
  assert.equal(await page.evaluate(async ({ scope, id }) => { try { await staleLineage.projects.prepare(scope, { project_id: id, mode: 'upload_existing' }); return 'unexpected_success' } catch (error) { return error.code } }, { scope: scopeA, id: 'stale-project' }), 'closed')
  assert.equal(await projectFailure('prepare', [{ ...newScopeB, deviceId: scopeA.deviceId }, { project_id: projectId, mode: 'upload_existing' }]), 'account_mismatch')
  await page.evaluate(async () => { await session.close(); globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), scopeA), bindingsSaved)
  assert.deepEqual(await durableSnapshot(), v3)
  cases.push('project bindings obey native Web Locks ownership transfer, account/device isolation and stale logout handle rejection without erasure')
  await mutate('projectBindings', 'put', { ...registeredLineage, record_version: 99 })
  assert.equal(await projectFailure('read', [scopeA, projectId]), 'corrupt_record')
  assert.equal(await projectFailure('confirmRegistration', [scopeA, registeredLineage, registrationEvidence]), 'corrupt_record')
  await mutate('projectBindings', 'put', registeredLineage)
  await mutate('projectBindings', 'put', { ...registeredLineage, phase: 'ready' })
  assert.equal(await projectFailure('list', [scopeA]), 'corrupt_record')
  await mutate('projectBindings', 'put', registeredLineage)
  assert.deepEqual(await page.evaluate(scope => session.projects.list(scope), scopeA), bindingsSaved)
  assert.deepEqual(await page.evaluate(() => nativeRows('projectBindings')), bindingsSaved)
  assert.deepEqual(await durableSnapshot(), v3)
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA), saved.cursor)
  cases.push('unknown/unproven lineage records fail after reopen without repair; durable metadata contains only native IDs/lifecycle fields, ACK/proven remain zero')
  const metadataMutate = (store, action, value) => page.evaluate(async ({ store, action, value }) => {
    const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = reject })
    try { await c21.runBrowserTransaction(db, [store], 'readwrite', (tx, result) => { tx.objectStore(store)[action](value); result(undefined) }) } finally { db.close() }
  }, { store, action, value })
  // v4 fixture contains exactly the seven accepted legacy stores and their bytes.
  const seven = [...allStores, 'projectBindings']
  const oldV4 = await page.evaluate(async stores => Object.fromEntries(await Promise.all(stores.map(async store => [store, await nativeRows(store)]))), seven)
  await page.evaluate(async ({ stores, rows }) => {
    await session.close()
    const db = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result) })
    const schema = stores.map(name => { const s = db.transaction(name).objectStore(name); return { name, keyPath: s.keyPath, indexes: Array.from(s.indexNames, name => { const i = s.index(name); return { name, keyPath: i.keyPath, unique: i.unique } }) } })
    db.close()
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject })
    const r = indexedDB.open(c21.WEB_DATABASE_NAME, 4)
    r.onupgradeneeded = () => { for (const s of schema) { const store = r.result.createObjectStore(s.name, { keyPath: s.keyPath }); for (const i of s.indexes) store.createIndex(i.name, i.keyPath, { unique: i.unique }) } }
    const legacy = await new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = reject })
    try { await c21.runBrowserTransaction(legacy, stores, 'readwrite', (tx, result) => {
      for (const [store, records] of Object.entries(rows)) for (const row of records) tx.objectStore(store).add(store === 'projectBindings' ? { ...row, record_version: 99 } : row)
      result(undefined)
    }) } finally { legacy.close() }
  }, { stores: seven, rows: oldV4 })
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
  assert.deepEqual(await nativeSchema(), { version: 4, stores: seven.sort() })
  for (const row of oldV4.projectBindings) await metadataMutate('projectBindings', 'put', row)
  const v4Failure = async kind => page.evaluate(async kind => {
    const create = IDBDatabase.prototype.createObjectStore, getAll = IDBObjectStore.prototype.getAll
    if (kind === 'quota') IDBDatabase.prototype.createObjectStore = function(name, ...args) { if (name === 'ownerHeads') throw new DOMException('fixture', 'QuotaExceededError'); return create.call(this, name, ...args) }
    else IDBObjectStore.prototype.getAll = function(...args) { const request = getAll.apply(this, args); if (this.name === 'projectBindings') this.transaction.abort(); return request }
    try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBDatabase.prototype.createObjectStore = create; IDBObjectStore.prototype.getAll = getAll }
  }, kind)
  assert.equal(await v4Failure('quota'), 'quota_exceeded')
  assert.deepEqual(await nativeSchema(), { version: 4, stores: seven.sort() })
  assert.equal(await v4Failure('request_abort'), 'storage_failed')
  assert.deepEqual(await nativeSchema(), { version: 4, stores: seven.sort() })
  await page.evaluate(async () => { globalThis.v4Blocker = await new Promise(resolve => { const r = indexedDB.open(c21.WEB_DATABASE_NAME, 4); r.onsuccess = () => resolve(r.result) }) })
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'upgrade_blocked')
  await page.evaluate(() => v4Blocker.close())
  assert.deepEqual(await nativeSchema(), { version: 4, stores: seven.sort() })
  for (const store of seven) assert.deepEqual(await page.evaluate(store => nativeRows(store), store), oldV4[store])
  await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
  assert.deepEqual(await page.evaluate(() => nativeRows('ownerHeads')), [])
  for (const store of seven) assert.deepEqual(await page.evaluate(store => nativeRows(store), store), oldV4[store])
  cases.push('real v4→v6 validates all seven stores; corrupt lineage/quota/request-abort/blocked upgrade preserve v4 exactly; ownerHeads starts empty without fabricated proof')
  await page.evaluate(async scope => {
    globalThis.scopeA = scope
    globalThis.meta = await c21.metadataFixture(session, scope)
    globalThis.metadataWire = async (event, seq) => {
      const lease = meta.keys.leaseForAccount(scope.accountId)
      const object = await lease.use(amk => c21.sealProjectMetadataEvent(amk, event))
      const h = event.header
      try { return { event: { event_id: h.event_id, device_id: h.device_id, server_sequence: seq, project_id: h.project_id, entity_id: h.entity_id, entity_type: 'project_metadata', operation: h.operation === 'delete' ? 'delete' : 'upsert', revision: h.revision, updated_at: h.updated_at, deleted_at: event.deleted_at }, object: { crypto_version: 1, aad_version: 1, nonce: c21.encodeBase64Url(object.nonce), ciphertext: c21.encodeBase64Url(object.ciphertext) } } }
      finally { object.nonce.fill(0); object.ciphertext.fill(0) }
    }
  }, scopeA)
  const peer = users[3], stamp = '2026-10-12T00:00:00.000000Z'
  const metadataEvent = (id, project = importedProject, boot = importedBootstrap, operation = 'create', parents = [], revision = 1, generation = 1) => ({ version: 1, header: { account_id: users[0], bootstrap_id: boot, device_id: peer, entity_id: project, event_id: id, generation, operation, parent_event_ids: parents, project_id: project, revision, updated_at: stamp }, metadata: operation === 'delete' ? null : { name: 'PRIVATE_METADATA_SENTINEL', goal: null, infinite: true, unit: 'symbols', deadline: null, status: 'active', personal_goal: 1, auto_freeze: false, streak_enabled: false, work_method: 'manual', stages_enabled: false, combine_stage_mindmaps: false }, deleted_at: operation === 'delete' ? stamp : null })
  const eid = i => `abcdef00-0000-4000-8000-${String(i).padStart(12, '0')}`
  const events = [metadataEvent(eid(1)), metadataEvent(eid(2), importedProject, importedBootstrap, 'update', [eid(1)], 2, 3), metadataEvent(eid(3), importedProject, importedBootstrap, 'update', [eid(2)], 3, 4),
    metadataEvent(eid(4)), metadataEvent(eid(5), importedProject, importedBootstrap, 'update', [eid(1)], 2, 2),
    metadataEvent(eid(6), importedProject, importedBootstrap, 'update', [eid(99)], 2, 2), metadataEvent(eid(7), importedProject, importedBootstrap, 'update', [eid(3)], 4, 4),
    metadataEvent(eid(8), importedProject, importedBootstrap, 'update', [eid(3)], 5, 5), metadataEvent(eid(9), importedProject, users[2]),
    metadataEvent(eid(10), 'missing-lineage', users[2]), metadataEvent(eid(11), projectId, registeredLineage.bootstrap_id),
    { ...metadataEvent(eid(12), 'coverless-codec2-project', eid(97)), version: 2, metadata: { ...metadataEvent(eid(12)).metadata, cover_reference: null } },
    metadataEvent(eid(13), importedProject, importedBootstrap, 'update', [eid(3)], 4, 5), metadataEvent(eid(14), importedProject, importedBootstrap, 'update', [eid(3)], 4, 5),
    { ...metadataEvent(eid(15), 'own-metadata-project', users[2]), header: { ...metadataEvent(eid(15), 'own-metadata-project', users[2]).header, device_id: scopeA.deviceId } },
    metadataEvent(eid(16), importedProject, importedBootstrap, 'delete', [eid(13)], 5, 6),
    { ...metadataEvent(eid(17)), version: 2, metadata: { ...metadataEvent(eid(17)).metadata, cover_reference: { version: 1, blob_id: eid(98), crypto_version: 1, aad_version: 1, mime_type: 'image/jpeg', plaintext_size: 4, key_fingerprint: '0'.repeat(64), envelope_sha256: '1'.repeat(64) } } }]
  await page.evaluate(({ scope, bootstrap }) => session.projects.importRemote(scope, { project_id: 'own-metadata-project', bootstrap_id: bootstrap, remote_state: 'active', remote_high_water: 0 }), { scope: scopeA, bootstrap: users[2] })
  await page.evaluate(({ scope, bootstrap }) => session.projects.importRemote(scope, { project_id: 'coverless-codec2-project', bootstrap_id: bootstrap, remote_state: 'active', remote_high_water: 0 }), { scope: scopeA, bootstrap: eid(97) })
  const metadataBindingsSaved = await page.evaluate(() => nativeRows('projectBindings'))
  const metadataStart = saved.cursor.pull_cursor
  // Synthetic Metadata server sequence must follow prior immutable upload receipts as well as pull position.
  const metadataSequenceStart = Math.max(metadataStart, ...(await page.evaluate(() => nativeRows('receipts'))).map(row => row.server_sequence))
  const wires = await page.evaluate(async ({ events, start }) => { const result = []; for (let i = 0; i < events.length; i++) result.push(await metadataWire(events[i], start + i + 1)); return result }, { events, start: metadataSequenceStart })
  // A source-equal event with accepted outbox/receipt is still missing native candidate/decision proof.
  const ownWire = wires[14], { device_id: _ownDevice, server_sequence: _ownSeq, ...ownDescriptor } = ownWire.event
  const ownBody = JSON.stringify({ protocol_version: 3, encrypted_sync_version: 3, device_id: scopeA.deviceId, items: [{ event: ownDescriptor, object: ownWire.object }] })
  const ownQueued = await page.evaluate(({ scope, body }) => session.sync.enqueue(scope, [body]), { scope: scopeA, body: ownBody })
  await page.evaluate(({ scope, row, sequence }) => session.sync.commitUploadAcceptance(scope, row, { protocol_version: 3, encrypted_sync_version: 3, results: [{ event_id: row.event_id, server_sequence: sequence, duplicate: false }], current_cursor: sequence }), { scope: scopeA, row: ownQueued[0].item, sequence: ownWire.event.server_sequence })
  const metaPage = JSON.stringify({ protocol_version: 3, encrypted_sync_version: 3, items: wires, next_cursor: wires.at(-1).event.server_sequence, has_more: false })
  await page.evaluate(({ scope, since, raw }) => session.sync.commitInboundPage(scope, since, raw), { scope: scopeA, since: metadataStart, raw: metaPage })
  const metaApply = index => page.evaluate(({ scope, ref }) => session.metadata.apply(scope, ref, meta.auth, meta.bindings, meta.keys), { scope: scopeA, ref: wires[index].event })
  const metaReject = async (index, code) => {
    const before = await metadataSnapshot()
    assert.equal(await page.evaluate(async ({ scope, ref }) => { try { await session.metadata.apply(scope, ref, meta.auth, meta.bindings, meta.keys); return 'unexpected_success' } catch (error) { return error.code ?? 'untyped_failure' } }, { scope: scopeA, ref: wires[index].event }), code)
    assert.deepEqual(await metadataSnapshot(), before)
  }
  const metadataSnapshot = () => page.evaluate(async stores => Object.fromEntries(await Promise.all(stores.map(async store => [store, await nativeRows(store)]))), [...seven, 'ownerHeads'])
  const metaHead = () => page.evaluate(({ scope, project }) => session.metadata.readHead(scope, project), { scope: scopeA, project: importedProject })
  await metaReject(1, 'missing_history')
  cases.push('authenticated latest update cannot become first authority; missing causal parents leave received and empty head')
  assert.equal(await metaApply(0), 'applied')
  const firstHead = await metaHead(), firstApplied = (await page.evaluate(() => nativeRows('inbox'))).find(row => row.event_id === eid(1))
  assert.deepEqual(firstHead.tip_event_ids, [eid(1)]); assert.equal(firstApplied.state, 'applied'); assert.equal(firstApplied.record_version, 2)
  assert.equal(firstApplied.wire_item, JSON.stringify(wires[0])); assert.match(firstApplied.applied_proof.wire_digest, /^[0-9a-f]{64}$/)
  cases.push('actual frozen Metadata decrypt/frame/codec creates valid imported genesis and atomic head+proof+applied inbox; original ciphertext wire unchanged')
  assert.equal(await metaApply(1), 'applied')
  assert.equal(await metaApply(2), 'applied')
  assert.deepEqual((await metaHead()).tip_event_ids, [eid(3)]); assert.equal((await metaHead()).history.length, 3)
  const descendant = await metadataSnapshot()
  assert.equal(await metaApply(0), 'already_applied'); assert.deepEqual(await metadataSnapshot(), descendant)
  cases.push('causal next updates retain full encrypted ancestry and advance exact revision/generation; old applied replay cannot rewrite descendant authority')
  await metaReject(3, 'metadata_conflict'); cases.push('concurrent genesis rejects without choosing latest sequence or discarding branch')
  await metaReject(4, 'metadata_conflict'); cases.push('stale-parent branch rejects with complete tips preserved')
  await metaReject(5, 'missing_history'); cases.push('unknown-parent orphan remains received without blocker or authority mutation')
  await metaReject(6, 'metadata_rejected'); cases.push('non-increasing generation rejects')
  await metaReject(7, 'metadata_rejected'); cases.push('non-native revision increment rejects')
  await metaReject(8, 'conflicting_record'); cases.push('authenticated wrong bootstrap cannot cross imported lineage')
  await metaReject(9, 'missing_history'); cases.push('missing durable project lineage cannot be inferred from decrypted event')
  await metaReject(10, 'ineligible_lineage'); cases.push('upload_existing registered lineage rejects protected apply')
  assert.equal(await metaApply(11), 'applied'); cases.push('authenticated Metadata codec2 null Cover follows native no-material rule and commits coverless imported genesis')
  await metaReject(16, 'cover_material_unavailable'); cases.push('actual authenticated non-null Cover reference blocks until retained encrypted material prerequisite exists')
  await metaReject(14, 'self_echo_unavailable'); cases.push('exact own-source outbox+accepted receipt+identical ciphertext/sequence insufficient without native candidate/decision proof')
  // Prepare both clean siblings against the same complete expected-old head.
  await page.evaluate(async ({ scope, refs }) => { globalThis.planA = await session.metadata.prepareVerified(scope, refs[0], meta.auth, meta.bindings, meta.keys); globalThis.planB = await session.metadata.prepareVerified(scope, refs[1], meta.auth, meta.bindings, meta.keys) }, { scope: scopeA, refs: [wires[12].event, wires[13].event] })
  const beforeRollback = await metadataSnapshot()
  const abortApply = async kind => page.evaluate(async ({ scope, kind }) => {
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function(...args) {
      if (this.name === 'inbox' && kind === 'quota') throw new DOMException('fixture', 'QuotaExceededError')
      const request = put.apply(this, args)
      if (this.name === 'inbox') {
        if (kind === 'abort') this.transaction.abort()
        if (kind === 'key_lock') void meta.keys.lock()
        if (kind === 'logout') void meta.auth.logout()
        if (kind === 'close') void session.close()
      }
      return request
    }
    try { await session.metadata.commitVerifiedImportedMetadataApply(scope, planA); return 'unexpected_success' } catch (error) { return error.code }
    finally { IDBObjectStore.prototype.put = put }
  }, { scope: scopeA, kind })
  assert.equal(await abortApply('abort'), 'storage_failed'); assert.deepEqual(await metadataSnapshot(), beforeRollback)
  cases.push('real IDB abort after both writes queued rolls back authority/proof/inbox together')
  assert.equal(await abortApply('quota'), 'quota_exceeded'); assert.deepEqual(await metadataSnapshot(), beforeRollback)
  cases.push('quota after head write queued rolls back entire protected apply')
  assert.equal(await abortApply('key_lock'), 'closed'); assert.deepEqual(await metadataSnapshot(), beforeRollback)
  cases.push('key lock during queued apply aborts before commit; received ciphertext and authority retained')
  await page.evaluate(async scope => { await meta.keys.dispose(); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  // Reprepare under a fresh actual key context; no stale token may be reused.
  await page.evaluate(async ({ scope, refs }) => { globalThis.planA = await session.metadata.prepareVerified(scope, refs[0], meta.auth, meta.bindings, meta.keys); globalThis.planB = await session.metadata.prepareVerified(scope, refs[1], meta.auth, meta.bindings, meta.keys) }, { scope: scopeA, refs: [wires[12].event, wires[13].event] })
  assert.equal(await abortApply('logout'), 'closed'); assert.deepEqual(await metadataSnapshot(), beforeRollback)
  cases.push('auth logout during live write aborts apply and revokes prepared plans')
  await page.evaluate(async scope => { await meta.keys.dispose(); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  await page.evaluate(async ({ scope, refs }) => { globalThis.planA = await session.metadata.prepareVerified(scope, refs[0], meta.auth, meta.bindings, meta.keys); globalThis.planB = await session.metadata.prepareVerified(scope, refs[1], meta.auth, meta.bindings, meta.keys) }, { scope: scopeA, refs: [wires[12].event, wires[13].event] })
  assert.equal(await abortApply('close'), 'closed'); assert.deepEqual(await metadataSnapshot(), beforeRollback)
  cases.push('session close during queued Metadata writes aborts both stores before releasing writer lock')
  await page.evaluate(async scope => { await meta.keys.dispose(); globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  await page.evaluate(async ({ scope, refs }) => { globalThis.planA = await session.metadata.prepareVerified(scope, refs[0], meta.auth, meta.bindings, meta.keys); globalThis.planB = await session.metadata.prepareVerified(scope, refs[1], meta.auth, meta.bindings, meta.keys) }, { scope: scopeA, refs: [wires[12].event, wires[13].event] })
  assert.equal(await page.evaluate(scope => session.metadata.commitVerifiedImportedMetadataApply(scope, planA), scopeA), 'applied')
  const siblingHead = await metadataSnapshot()
  await expectCode(page, 'session.metadata.commitVerifiedImportedMetadataApply(scopeA, planB)', 'stale_authority')
  assert.deepEqual(await metadataSnapshot(), siblingHead)
  assert.equal(await page.evaluate(scope => session.metadata.commitVerifiedImportedMetadataApply(scope, planA), scopeA), 'already_applied')
  cases.push('complete expected-old CAS rejects stale prepared sibling; exact same token replay is idempotent')
  // Exact applied event with new valid ciphertext but identical header must fail durable wire digest replay.
  const changedEvent = structuredClone(events[0]); changedEvent.metadata.name = 'CHANGED_PRIVATE_SENTINEL'
  const changedWire = await page.evaluate(({ event, seq }) => metadataWire(event, seq), { event: changedEvent, seq: wires[0].event.server_sequence })
  await metadataMutate('inbox', 'put', { ...firstApplied, wire_item: JSON.stringify(changedWire) })
  await metaReject(0, 'conflicting_record')
  await metadataMutate('inbox', 'put', firstApplied)
  cases.push('valid re-encryption of changed payload with same event/header rejected by immutable wire digest, no replay success')
  // Removing any retained ancestor is a hard hole even while head proof is present.
  const parentRow = firstApplied
  await metadataMutate('inbox', 'delete', [scopeA.accountId, parentRow.server_sequence])
  await metaReject(15, 'missing_history')
  await metadataMutate('inbox', 'add', parentRow)
  cases.push('missing encrypted ancestor rejects despite durable head/proof; no empty-history fallback')
  // A locally pending encrypted Metadata candidate blocks peer apply; no compatible-local-state guess.
  const ownOutbox = (await page.evaluate(() => nativeRows('outbox'))).find(row => row.event_id === eid(15))
  const pending = JSON.parse(ownOutbox.raw_body)
  pending.items[0].event.project_id = importedProject; pending.items[0].event.entity_id = importedProject
  await metadataMutate('outbox', 'put', { ...ownOutbox, raw_body: JSON.stringify(pending) })
  await metaReject(15, 'local_incompatible')
  await metadataMutate('outbox', 'put', ownOutbox)
  cases.push('pending local Metadata state blocks peer clean apply rather than inferring native candidate compatibility')
  await page.evaluate(async ({ scope, ref }) => { globalThis.staleBindingPlan = await session.metadata.prepareVerified(scope, ref, meta.auth, meta.bindings, meta.keys) }, { scope: scopeA, ref: wires[15].event })
  await metadataMutate('projectBindings', 'put', { ...importedLineage, remote_high_water: 10 })
  const changedBindingState = await metadataSnapshot()
  await expectCode(page, 'session.metadata.commitVerifiedImportedMetadataApply(scopeA, staleBindingPlan)', 'stale_lineage')
  assert.deepEqual(await metadataSnapshot(), changedBindingState)
  await metadataMutate('projectBindings', 'put', importedLineage)
  cases.push('exact persisted lineage snapshot CAS rejects changed registration high-water without touching Metadata authority/proof')
  const ownReceived = (await page.evaluate(() => nativeRows('inbox'))).find(row => row.event_id === eid(15))
  await metadataMutate('inbox', 'delete', [scopeA.accountId, ownReceived.server_sequence])
  await metaReject(14, 'missing_history')
  await metadataMutate('inbox', 'add', ownReceived)
  cases.push('accepted upload receipt/ciphertext alone cannot become inbox applied proof')
  const beforeChangedReplay = await metadataSnapshot()
  for (const changed of [{ revision: 2 }, { server_sequence: 999 }, { device_id: scopeA.deviceId }]) {
    await metadataMutate('inbox', 'put', { ...firstApplied, wire_item: JSON.stringify({ ...wires[0], event: { ...wires[0].event, ...changed } }) })
    await metaReject(0, 'corrupt_record')
    await metadataMutate('inbox', 'put', firstApplied)
  }
  assert.deepEqual(await metadataSnapshot(), beforeChangedReplay)
  cases.push('changed applied descriptor/revision/sequence/source-device replay rejects immutable proof, no authority rewrite')
  assert.equal(await metaApply(15), 'applied')
  assert.equal((await metaHead()).history.find(p => p.event_id === eid(16)).operation, 'delete')
  const receivedOnly = await page.evaluate(scope => session.sync.listReceived(scope, 200), scopeA)
  assert.equal(receivedOnly.some(row => row.state !== 'received' || row.event_id === eid(16)), false)
  const afterDelete = await metadataSnapshot()
  assert.equal(await metaApply(0), 'already_applied'); assert.deepEqual(await metadataSnapshot(), afterDelete)
  cases.push('clean authenticated tombstone advances causal authority atomically; applied rows excluded from received listing and old replay preserves deletion')
  const finalMeta = await metadataSnapshot()
  assert.equal(JSON.stringify(finalMeta).includes('PRIVATE_METADATA_SENTINEL'), false)
  assert.equal(JSON.stringify(finalMeta).includes('CHANGED_PRIVATE_SENTINEL'), false)
  assert.equal((await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA)).ack_cursor, 0)
  assert.equal((await page.evaluate(scope => session.sync.readCheckpoint(scope), scopeA)).proven_prefix, 0)
  assert.deepEqual(await page.evaluate(() => nativeRows('projectBindings')), metadataBindingsSaved)
  assert.equal((await page.evaluate(({ scope, id }) => session.projects.evaluateReadiness(scope, id), { scope: scopeA, id: importedProject })).ready, false)
  cases.push('all encrypted history retained; no plaintext/key/token persisted; ACK/proven0, imported binding and project readiness unchanged')
  await page.reload()
  await page.evaluate(async ({ users, scope }) => { globalThis.users = users; globalThis.scopeA = scope; globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope) }, { users, scope: scopeA })
  assert.deepEqual(await metadataSnapshot(), finalMeta)
  assert.equal(await metaApply(0), 'already_applied')
  await context.close(); await start(); page = await tab()
  await page.evaluate(async scope => { globalThis.scopeA = scope; globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  assert.deepEqual(await metadataSnapshot(), finalMeta)
  assert.equal(await metaApply(0), 'already_applied')
  cases.push('atomic Metadata authority/proof/immutable ciphertext survive reload and full Chromium disk-profile reopen; exact replay remains stable')
  competing = await tab(); await expectCode(competing, 'c21.openBrowserPersistence(users[0])', 'writer_busy')
  await page.close(); page = competing
  await page.evaluate(async scope => { globalThis.scopeA = scope; globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  assert.deepEqual(await metadataSnapshot(), finalMeta)
  cases.push('Web Locks termination transfers imported Metadata authority intact')
  await page.evaluate(async () => { globalThis.staleMetadata = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  await expectCode(page, 'staleMetadata.metadata.readHead(scopeA, "imported-project")', 'closed')
  await expectCode(page, 'session.metadata.readHead(scopeA, "imported-project")', 'account_mismatch')
  assert.equal(await page.evaluate(({ scope, id }) => session.metadata.readHead(scope, id), { scope: newScopeB, id: importedProject }), null)
  await page.evaluate(async scope => { await session.close(); globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope) }, scopeA)
  assert.deepEqual(await metadataSnapshot(), finalMeta)
  cases.push('Metadata account/device isolation and stale logout handles fail closed without erasing another account history')
  page = await acceptLocalAuthority({ page, scope: scopeA, otherScope: newScopeB, users, cases, expectCode, tab, reopenProfile: async () => { await context.close(); await start(); return tab() } })
  page = await acceptInitialNotes({ page, scope: scopeA, users, cases, expectCode, tab, reopenProfile: async () => { await context.close(); await start(); return tab() } })
  page = await acceptBootstrapCompletion({ page, scope: scopeA, users, cases, expectCode, tab, reopenProfile: async () => { await context.close(); await start(); return tab() } })
  assert.equal(completionRequests.length, 15)
  const retryBodies = completionRequests.filter(r => r.path.includes('/failure-completion/')).map(r => r.body)
  assert.equal(retryBodies.length, 7); retryBodies.forEach(body => assert.deepEqual(body, retryBodies[0]))
  page = await acceptAccountRegistry({ page, scope: scopeA, users, cases, expectCode, tab, reopenProfile: async () => { await context.close(); await start(); return tab() } })
  assert.equal(registryRequests.length,16)
  assert.equal(ackRequests.length,0)
  const beforeApplyNetwork = completionRequests.length+registryRequests.length+ackRequests.length
  page = await acceptLegacyNoteApply({ page, scope:scopeA, users, cases, expectCode, reopenProfile:async()=>{await context.close();await start();return tab()} })
  assert.equal(completionRequests.length+registryRequests.length+ackRequests.length,beforeApplyNetwork)
  page = await acceptNoteHistory({ page, scope:scopeA, users, cases, expectCode, reopenProfile:async()=>{await context.close();await start();return tab()} })
  assert.equal(completionRequests.length,16);assert.equal(registryRequests.length,16);assert.equal(ackRequests.length,0)
  page = await acceptNoteIntents({page,scope:scopeA,users,cases,expectCode,reopenProfile:async()=>{await context.close();await start();return tab()}})
  assert.equal(completionRequests.length,16);assert.equal(registryRequests.length,16);assert.equal(ackRequests.length,0)
  page=await acceptUnsealedConflicts({page,scope:scopeA,users,cases,reopenProfile:async()=>{await context.close();await start();return tab()}})
  assert.equal(completionRequests.length,16);assert.equal(registryRequests.length,16);assert.equal(ackRequests.length,0)
  const finalIntents=await page.evaluate(()=>nativeRows('legacyNoteIntents'))
  const finalHistory = await page.evaluate(()=>nativeRows('legacyNoteHistory'))
  const finalDurability = await metadataSnapshot()
  const localFinal = await page.evaluate(async () => ({ projects: await nativeRows('localProjects'), notes: await nativeRows('localNotes') }))
  const retainedProofs = await page.evaluate(() => nativeRows('receipts'))
  const retainedAccepted = await page.evaluate(() => nativeRows('outbox'))
  const retainedBindings = await page.evaluate(() => nativeRows('projectBindings'))
  await page.evaluate(async () => {
    await new Promise((resolve, reject) => {
      const r = indexedDB.open(c21.WEB_DATABASE_NAME, c21.WEB_DATABASE_VERSION + 1)
      r.onsuccess = () => { r.result.close(); resolve() }; r.onerror = reject
    })
  })
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'unsupported_version')
  assert.deepEqual(await page.evaluate(() => nativeRows('receipts')), retainedProofs)
  assert.deepEqual(await page.evaluate(() => nativeRows('outbox')), retainedAccepted)
  assert.deepEqual(await page.evaluate(() => nativeRows('projectBindings')), retainedBindings)
  assert.deepEqual(await metadataSnapshot(), finalDurability)
  assert.deepEqual(await page.evaluate(async () => ({ projects: await nativeRows('localProjects'), notes: await nativeRows('localNotes') })), localFinal)
  cases.push('future schema rejects older client while preserving immutable receipts and accepted encrypted bodies')
  assert.deepEqual(await page.evaluate(()=>nativeRows('legacyNoteHistory')),finalHistory)
  assert.deepEqual(await page.evaluate(()=>nativeRows('legacyNoteIntents')),finalIntents)
  assert.deepEqual(unexpected, [])
  console.log(JSON.stringify({ result: 'PASS', cases, nativeIndexedDB: true, nativeWebLocks: true, APIRequests: completionRequests.length+registryRequests.length, registryRequests:registryRequests.length, ACKRequests:ackRequests.length, protectedApplyRequests:0, candidateConflictRequests:0, bootstrapCompletionRequests: completionRequests.length, unrelatedAPIRequests: 0, pageErrors: 0 }))
} finally {
  if (context) await context.close()
  await rm(directory, { recursive: true, force: true })
}
