/** Real Chromium IDB/Web Locks acceptance on a disposable disk profile; no app/API/native mocks. */
import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'c21-persistence-'))
const users = ['11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444']
const cases = []
let context
const unexpected = []
async function start() {
  context = await chromium.launchPersistentContext(directory, { headless: true })
  context.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) unexpected.push('API request') })
  await context.route(`${origin}/c21-harness`, route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>C21 persistence acceptance</title>' }))
}
async function tab() {
  const page = await context.newPage()
  page.on('pageerror', () => unexpected.push('pageerror'))
  await page.goto(`${origin}/c21-harness`)
  await page.evaluate(async users => {
    globalThis.c21 = await import('/src/platform/web/persistence.ts')
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
    try { await (new Function(`return (${operation})`))(); return 'unexpected_success' }
    catch (error) { return error.code ?? 'untyped_failure' }
  }, operation)
  assert.equal(result, code)
}
try {
  await start()
  let page = await tab()
  const original = await page.evaluate(async () => {
    globalThis.session = await c21.openBrowserPersistence(users[0])
    return session.read(users[0])
  })
  const rows = await page.evaluate(() => nativeRows('identities'))
  assert.equal(rows.length, 1)
  assert.deepEqual(Object.keys(rows[0]).sort(), ['canonical_user_id', 'device_id', 'local_account_id', 'record_version'])
  assert.equal((await page.evaluate(() => nativeRows('accountBindings'))).length, 1)
  cases.push('first open atomically creates allowlisted identity/binding')

  await page.reload()
  await page.evaluate(async users => { globalThis.c21 = await import('/src/platform/web/persistence.ts'); globalThis.users = users; globalThis.session = await c21.openBrowserPersistence(users[0]) }, users)
  assert.deepEqual(await page.evaluate(() => session.read(users[0])), original)
  cases.push('reload identity durability')

  await expectCode(page, 'session.read(users[1])', 'account_mismatch')
  await page.evaluate(async () => { globalThis.old = session; await session.resetForLogout(); globalThis.session = await c21.openBrowserPersistence(users[1]) })
  await expectCode(page, 'old.read(users[0])', 'closed')
  const second = await page.evaluate(() => session.read(users[1]))
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
  cases.push('disk profile survives browser process restart')

  await page.evaluate(async () => { const read = session.read(users[0]); const close = session.resetForLogout(); const result = await read.then(() => 'unexpected_success', error => error.code); await close; if (result !== 'closed') throw Error('logout_drain_failed') })
  await expectCode(page, 'session.provision(users[0])', 'closed')
  cases.push('logout aborts pending transaction and revokes stale handle')

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

  await page.evaluate(async () => {
    globalThis.session = await c21.openBrowserPersistence(users[0])
    await new Promise((resolve, reject) => {
      const request = indexedDB.open(c21.WEB_DATABASE_NAME, 2)
      request.onsuccess = () => { request.result.close(); resolve() }
      request.onerror = () => reject(Error('future_fixture_failed'))
    })
  })
  await expectCode(page, 'session.read(users[0])', 'closed')
  await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'unsupported_version')
  assert.deepEqual(await page.evaluate(() => nativeRows('identities')), rows.concat([{ ...second, canonical_user_id: users[1], record_version: 1 }]))
  cases.push('versionchange invalidates old connection; future version refuses downgrade and preserves identity')
  assert.deepEqual(unexpected, [])
  console.log(JSON.stringify({ result: 'PASS', cases, nativeIndexedDB: true, nativeWebLocks: true, APIRequests: 0, pageErrors: 0 }))
} finally {
  if (context) await context.close()
  await rm(directory, { recursive: true, force: true })
}
