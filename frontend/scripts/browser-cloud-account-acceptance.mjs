import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'worta-browser-account-'))
const calls = []
let context
let records
let failCrypto = false

async function launch() {
  context = await chromium.launchPersistentContext(directory, { headless: true })
  await context.route(url => url.pathname.startsWith('/api/'), async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    calls.push(path)
    const send = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (path === '/api/v1/auth/login' && request.method() === 'POST') {
      const { username, password } = request.postDataJSON()
      if (!['one', 'two'].includes(username) || password !== 'account-password') return send({ detail: { code: 'invalid_credentials' } }, 401)
      return send({ access_token: `synthetic-access-${username}`, refresh_token: `synthetic-refresh-${username}`, access_expires_in: 60 })
    }
    const name = request.headers().authorization?.replace('Bearer synthetic-access-', '')
    if (!['one', 'two'].includes(name)) return send({ detail: { code: 'unauthorized' } }, 401)
    if (path === '/api/v1/account/me' && request.method() === 'GET') {
      return send({ id: name === 'one' ? '11111111-1111-4111-8111-111111111111' : '22222222-2222-4222-8222-222222222222', username: name, email: `${name}@example.test`, email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' })
    }
    if (path === '/api/v1/legal/documents/status' && request.method() === 'GET') return send({ documents: [], missing_required_document_ids: [] })
    if (path === '/api/v1/legal/documents/accept' && request.method() === 'POST') return send({ documents: [], missing_required_document_ids: [] })
    if (path === '/api/v1/account/crypto' && request.method() === 'GET') {
      if (failCrypto) return route.abort('failed')
      return send(records[name])
    }
    if (path === '/api/v1/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204 })
    return send({ detail: { code: 'unexpected_api' } }, 404)
  })
}

async function openPage() {
  const page = await context.newPage()
  await page.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
  await page.waitForFunction(() => !!window.harness)
  return page
}

try {
  await launch()
  let page = await openPage()
  records = await page.evaluate(() => harness.createRecords())
  const first = await page.evaluate(async () => {
    window.session = harness.realSession()
    const identity = await session.login('one', 'account-password')
    assertStatus(session.status, 'authenticated')
    try { session.localNoteRepository(); throw Error('locked_local_repository_accepted') }
    catch (error) { if (error.message === 'locked_local_repository_accepted') throw error; if (error.code !== 'closed') throw error }
    try { await session.unlock('wrong-encryption-password'); throw Error('wrong_password_accepted') }
    catch (error) { if (error.message === 'wrong_password_accepted') throw error }
    assertStatus(session.status, 'authenticated')
    window.lease = await session.unlock('encryption-password')
    assertStatus(session.status, 'unlocked')
    if (await lease.use(async key => key.length) !== 32) throw Error('wrong_key_length')
    const repository = session.localNoteRepository()
    if (repository.scope.canonicalUserId !== '11111111-1111-4111-8111-111111111111') throw Error('wrong_local_scope')
    const project = { id: 'persist-project', name: 'PRIVATE_PROJECT_SENTINEL', goal: null, infinite: true, unit: 'symbols', status: 'active', created_at: null, updated_at: null, payload: {} }
    await repository.source.createProject(repository.scope, project)
    const snapshot = await repository.source.readSnapshot(repository.scope, project.id)
    await repository.source.createNote(repository.scope, snapshot.token, { id: 'persist-note', project_id: project.id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', title: 'PRIVATE_TITLE_SENTINEL', content: '<p>PRIVATE_BODY_SENTINEL</p>', checklist: [], color: 'default', pinned: false, archived: false, sort_order: 0, tags: [], created_at: '2026-01-01T00:00:00.000000Z', updated_at: '2026-01-01T00:00:00.000000Z', metadata: {}, revision: 0 })
    await repository.source.createProject(repository.scope, { ...project, id: 'isolated-project', name: 'ISOLATED_PROJECT_SENTINEL' })
    const isolated = await repository.source.readSnapshot(repository.scope, 'isolated-project')
    if (isolated.notes.length !== 0) throw Error('cross_project_note_visible')
    window.retainedLocalSource = repository.source
    return identity
    function assertStatus(actual, expected) { if (actual !== expected) throw Error(`status_${actual}_${expected}`) }
  })
  const secondTab = await openPage()
  await secondTab.evaluate(records => { harness.records = records }, records)
  const busy = await secondTab.evaluate(async () => {
    window.session = harness.realSession()
    try { await session.login('one', 'account-password'); return 'unexpected_success' }
    catch (error) { return error.code ?? 'unknown' }
  })
  assert.equal(busy, 'writer_busy')
  assert.equal(await secondTab.evaluate(() => session.status), 'logged_out')

  await page.evaluate(async () => {
    await session.lock()
    if (session.status !== 'locked') throw Error('not_locked')
    try { await lease.use(async () => undefined); throw Error('stale_lease_accepted') }
    catch (error) { if (error.message === 'stale_lease_accepted') throw error }
  })
  assert.equal(await page.evaluate(async () => {
    try { await retainedLocalSource.readSnapshot({ canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: session.currentIdentity.local_account_id, deviceId: session.currentIdentity.device_id }, 'persist-project'); return 'unexpected_success' }
    catch (error) { return error.code ?? 'unknown' }
  }), 'closed')
  const sameTabIdentity = await secondTab.evaluate(async () => session.login('one', 'account-password'))
  assert.deepEqual(sameTabIdentity, first)
  assert.equal(await page.evaluate(async () => {
    try { await session.unlock('encryption-password'); return 'unexpected_success' }
    catch (error) { return error.code ?? 'unknown' }
  }), 'writer_busy')
  await secondTab.evaluate(async () => session.logout())
  await page.evaluate(async () => {
    await session.unlock('encryption-password')
    await session.logout()
    if (session.status !== 'logged_out' || session.currentIdentity !== null) throw Error('logout_not_revoked')
  })
  const rows = await page.evaluate(async () => ({ identities: await harness.rows('identities'), bindings: await harness.rows('accountBindings') }))
  assert.equal(rows.identities.length, 1)
  assert.equal(rows.bindings.length, 1)
  assert.equal(rows.identities[0].device_id, first.device_id)
  const serialized = JSON.stringify(rows)
  for (const secret of ['synthetic-access', 'synthetic-refresh', 'account-password', 'encryption-password', 'ciphertext', 'masterKey']) {
    assert.equal(serialized.includes(secret), false)
  }
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)
  const otherStores = await page.evaluate(async () => {
    const names = ['outbox', 'inbox', 'cursors', 'receipts', 'projectBindings', 'ownerHeads', 'localProjects', 'localNotes', 'legacyNoteHistory', 'legacyNoteIntents']
    return Promise.all(names.map(name => harness.rows(name).then(rows => rows.length)))
  })
  assert.deepEqual(otherStores, [0, 0, 0, 0, 0, 0, 2, 1, 0, 0])
  const stored = await page.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }))
  const storedText = JSON.stringify(stored)
  for (const plaintext of ['PRIVATE_PROJECT_SENTINEL', 'PRIVATE_TITLE_SENTINEL', 'PRIVATE_BODY_SENTINEL', 'encryption-password', 'masterKey']) assert.equal(storedText.includes(plaintext), false)
  assert.ok(stored.notes[0].envelope.ciphertext)

  await context.close()
  await launch()
  page = await openPage()
  await page.evaluate(records => { harness.records = records }, records)
  const reopened = await page.evaluate(async () => {
    window.session = harness.realSession()
    const identity = await session.login('one', 'account-password')
    await session.unlock('encryption-password')
    const repository = session.localNoteRepository()
    const snapshot = await repository.source.readSnapshot(repository.scope, 'persist-project')
    const note = await repository.source.withDecryptedSnapshot(repository.scope, snapshot.token, async data => data.notes[0]?.note)
    if (note?.content !== '<p>PRIVATE_BODY_SENTINEL</p>' || note.title !== 'PRIVATE_TITLE_SENTINEL') throw Error('persistent_note_reopen_failed')
    return identity
  })
  assert.deepEqual(reopened, first)
  await page.evaluate(async () => session.logout())

  const other = await page.evaluate(async () => {
    window.session = harness.realSession()
    const identity = await session.login('two', 'account-password')
    await session.unlock('encryption-password')
    const repository = session.localNoteRepository()
    if (repository.scope.canonicalUserId !== '22222222-2222-4222-8222-222222222222') throw Error('wrong_second_scope')
    try { await repository.source.readSnapshot(repository.scope, 'persist-project'); throw Error('cross_account_source_visible') }
    catch (error) { if (error.message === 'cross_account_source_visible') throw error; if (error.code !== 'missing_local_source') throw error }
    await repository.source.createProject(repository.scope, { id: 'persist-project', name: 'SECOND_ACCOUNT_PROJECT', goal: null, infinite: true, unit: 'symbols', status: 'active', created_at: null, updated_at: null, payload: {} })
    const own = await repository.source.readSnapshot(repository.scope, 'persist-project')
    const ownName = await repository.source.withDecryptedSnapshot(repository.scope, own.token, async data => data.project.name)
    if (ownName !== 'SECOND_ACCOUNT_PROJECT') throw Error('second_account_project_mismatch')
    await session.logout()
    return identity
  })
  assert.notEqual(other.local_account_id, first.local_account_id)
  assert.notEqual(other.device_id, first.device_id)

  failCrypto = true
  await page.evaluate(async () => {
    window.session = harness.realSession()
    try { await session.login('one', 'account-password'); throw Error('network_success') }
    catch (error) { if (error.message === 'network_success') throw error }
    if (session.status !== 'logged_out') throw Error('network_false_authentication')
  })
  failCrypto = false
  await page.evaluate(async () => {
    harness.pauseCrypto = true
    window.session = harness.session()
    const pending = session.login('one', 'account-password').then(() => false, () => true)
    for (let attempt = 0; attempt < 100 && !harness.resumeCrypto; attempt++) await new Promise(resolve => setTimeout(resolve, 1))
    if (!harness.resumeCrypto) throw Error('crypto_request_not_started')
    await session.logout()
    harness.resumeCrypto()
    if (!await pending || session.status !== 'logged_out') throw Error('stale_crypto_response_accepted')
    harness.pauseCrypto = false
    harness.resumeCrypto = null
  })

  await page.evaluate(async () => {
    const request = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    await new Promise((resolve, reject) => {
      const tx = db.transaction('identities', 'readwrite')
      const row = { canonical_user_id: '11111111-1111-4111-8111-111111111111', local_account_id: 'bad', device_id: 'bad', record_version: 1 }
      tx.objectStore('identities').put(row)
      tx.oncomplete = resolve
      tx.onabort = () => reject(tx.error)
    })
    db.close()
  })
  assert.equal(await page.evaluate(async () => {
    window.session = harness.realSession()
    try { await session.login('one', 'account-password'); return 'unexpected_success' }
    catch (error) { return error.code ?? 'unknown' }
  }), 'corrupt_record')
  assert.equal((await page.evaluate(() => harness.rows('identities')))[0].local_account_id, 'bad')
  assert.equal(await page.evaluate(async () => {
    const original = Object.getOwnPropertyDescriptor(navigator, 'locks')
    Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined })
    try {
      window.session = harness.realSession()
      await session.login('two', 'account-password')
      return 'unexpected_success'
    } catch (error) { return error.code ?? 'unknown' }
    finally { if (original) Object.defineProperty(navigator, 'locks', original); else delete navigator.locks }
  }), 'unavailable')
  assert.ok(calls.includes('/api/v1/auth/login') && calls.includes('/api/v1/legal/documents/status') && calls.includes('/api/v1/account/me') && calls.includes('/api/v1/account/crypto'))
  assert.ok(calls.every(path => ['/api/v1/auth/login', '/api/v1/legal/documents/status', '/api/v1/legal/documents/accept', '/api/v1/account/me', '/api/v1/account/crypto', '/api/v1/auth/logout'].includes(path)))
  const localRows = await page.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }))
  assert.equal(localRows.projects.length, 3)
  assert.equal(localRows.notes.length, 1)
  const localText = JSON.stringify(localRows)
  for (const plaintext of ['PRIVATE_PROJECT_SENTINEL', 'PRIVATE_TITLE_SENTINEL', 'PRIVATE_BODY_SENTINEL', 'ISOLATED_PROJECT_SENTINEL', 'SECOND_ACCOUNT_PROJECT']) assert.equal(localText.includes(plaintext), false)
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)
  console.log('Browser account acceptance PASS: encrypted local Note persistence across browser restart, account/project isolation, lock revocation, two-tab writer contention, wrong password and corruption refusal; no Note writer/ACK/declaration calls')
} finally {
  await context?.close()
  await rm(directory, { recursive: true, force: true })
}
