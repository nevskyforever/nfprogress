// Real FastAPI/PostgreSQL acceptance. route.fetch is a network proxy, not a response fixture.
import assert from 'node:assert/strict'
import { chromium } from '@playwright/test'
const origin = new URL(process.argv[2]).origin, backend = new URL(process.argv[3]).origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
assert.equal(new URL(backend).hostname, '127.0.0.1')
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ locale: 'ru-RU' })
let phase = 'setup', failNetwork = false
const reads = [], registrations = [], pageErrors = []
await context.route(url => url.pathname.startsWith('/api/'), async route => {
  const request = route.request()
  if (phase === 'registration') registrations.push({ method: request.method(), path: new URL(request.url()).pathname })
  if (phase === 'read') reads.push({ method: request.method(), path: new URL(request.url()).pathname })
  if (failNetwork && new URL(request.url()).pathname === '/api/v3/sync/encrypted/pull') return route.abort('failed')
  const response = await route.fetch({ url: backend + new URL(request.url()).pathname + new URL(request.url()).search })
  await route.fulfill({ response })
})
const page = await context.newPage()
page.on('pageerror', e => pageErrors.push(e.message))
const expected = { Valid: null, Corrupt: 'invalid_encrypted_history', Foreign: 'invalid_encrypted_history', Dependency: 'metadata_dependency_or_deleted', Gate: 'compression_reader_required' }
const identities = []
try {
  for (const [username, failure] of Object.entries(expected)) {
    phase = 'setup'
    await page.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
    await page.waitForFunction(() => !!window.harness)
    await page.evaluate(async ({ username, scenario }) => {
      const crypto = await import('/src/crypto/index.ts'), { encodeBase64Url } = await import('/src/api/base64url.ts')
      const { accountCryptoApi } = await import('/src/api/accountCrypto.ts'), { sealProjectMetadataEvent } = await import('/src/cloud/projectMetadataCodec.ts')
      const response = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password: 'correct horse battery staple' }) })
      if (!response.ok) throw Error('fixture_login_failed')
      const token = (await response.json()).access_token
      const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
      const me = await (await fetch('/api/v1/account/me', { headers })).json()
      const api = async (path, method = 'POST', body) => {
        const r = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
        if (!r.ok) throw Error(`fixture_api_failed_${path}_${r.status}_${await r.text()}`)
        return r.status === 204 ? undefined : r.json()
      }
      const amk = await crypto.generateAccountMasterKey(), recoveryKey = await crypto.generateRecoveryKey()
      try {
        const password = await crypto.wrapAmkWithPassphrase(amk, 'encryption-password'), recovery = await crypto.wrapAmkWithRecoveryKey(amk, recoveryKey)
        await accountCryptoApi.provision(token, { password: { ...password, kdf: { ...password.kdf, salt: encodeBase64Url(password.kdf.salt) }, nonce: encodeBase64Url(password.nonce), ciphertext: encodeBase64Url(password.ciphertext) },
          recovery: { ...recovery, nonce: encodeBase64Url(recovery.nonce), ciphertext: encodeBase64Url(recovery.ciphertext) } })
        const sourceDevice = window.crypto.randomUUID()
        await api(`/api/v1/sync/devices/${sourceDevice}`, 'PUT')
        await api('/api/v2/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 0 })
        await api('/api/v3/sync/encrypted/reader-ready', 'POST', { device_id: sourceDevice, reader_transport_version: 3 })
        await api('/api/v3/sync/encrypted/cutover', 'POST', { expected_cutover_epoch: 1 })
        for (const projectId of ['server-project', 'second-project']) {
          const bootstrap = window.crypto.randomUUID()
          await api(`/api/v1/cloud/projects/${projectId}/bootstrap`, 'POST', { bootstrap_id: bootstrap, device_id: sourceDevice })
          await api(`/api/v1/cloud/projects/${projectId}/bootstrap/complete`, 'POST', { bootstrap_id: bootstrap, device_id: sourceDevice, initial_event_count: 0, initial_max_server_sequence: 0 })
          const event = { version: 1, header: { account_id: scenario === 'Foreign' ? window.crypto.randomUUID() : me.id, bootstrap_id: bootstrap, device_id: sourceDevice,
            entity_id: projectId, event_id: window.crypto.randomUUID(), project_id: projectId, generation: 1, revision: 1, operation: 'create', parent_event_ids: [], updated_at: '2026-10-27T00:00:00.000000Z' },
            metadata: { name: `PRIVATE_CLOUD_${username}_${projectId}`, goal: 1000, infinite: false, unit: 'symbols', deadline: null, status: 'активен', personal_goal: 100,
              auto_freeze: false, streak_enabled: false, work_method: 'manual', stages_enabled: false, combine_stage_mindmaps: false }, deleted_at: null }
          if (scenario === 'Dependency') Object.assign(event.header, { operation: 'update', revision: 2, generation: 2, parent_event_ids: [window.crypto.randomUUID()] })
          const sealed = await sealProjectMetadataEvent(amk, event)
          if (scenario === 'Corrupt') sealed.ciphertext[0] ^= 1
          const wire = { event_id: event.header.event_id, project_id: projectId, entity_id: projectId, entity_type: 'project_metadata', operation: 'upsert', revision: event.header.revision, updated_at: event.header.updated_at, deleted_at: null }
          await api('/api/v3/sync/encrypted/push', 'POST', { protocol_version: 3, encrypted_sync_version: 3, device_id: sourceDevice,
            items: [{ event: wire, object: { ...sealed, nonce: encodeBase64Url(sealed.nonce), ciphertext: encodeBase64Url(sealed.ciphertext) } }] })
        }
        if (scenario === 'Gate') {
          await api('/api/v3/sync/encrypted/compression-reader-capabilities', 'PUT', { device_id: sourceDevice, compression_id1: true })
          const ready = await api('/api/v3/sync/encrypted/compression-writer', 'POST', { device_id: sourceDevice })
          if (!ready.ready) throw Error('fixture_compression_gate_failed')
        }
        window.fixtureApi = api // test setup only; never exposed to the application session.
      } finally { amk.fill(0); recoveryKey.fill(0) }
      harness.mountAccountCard()
    }, { username, scenario: username })
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill('correct horse battery staple')
    await page.locator('form').first().evaluate(form => form.requestSubmit())
    await page.waitForSelector('[data-status="authenticated"]')
    await page.locator('input[autocomplete="off"]').fill('encryption-password')
    await page.locator('form').first().evaluate(form => form.requestSubmit())
    await page.waitForSelector('[data-status="unlocked"]')
    const deviceId = await page.evaluate(async () => {
      const r = await window.fixtureApi('/api/v1/account/me', 'GET')
      const rows = await harness.rows('identities')
      return rows.find(row => row.canonical_user_id === r.id).device_id
    })
    assert.ok(deviceId)
    identities.push(deviceId)
    const before = await page.evaluate(async () => {
      const r = {}; for (const store of ['identities', 'accountBindings', 'localProjects', 'localNotes', 'localStages', 'localDocuments', 'inbox', 'outbox', 'ownerHeads', 'cursors', 'projectBindings', 'receipts', 'legacyNoteHistory', 'legacyNoteIntents']) r[store] = await harness.rows(store)
      return r
    })
    phase = 'read'
    await page.getByRole('button', { name: 'Облачные проекты WORTA', exact: true }).click()
    await page.locator('li').filter({ has: page.locator('code').filter({ hasText: /^server-project$/ }) }).getByRole('button').click()
    await page.waitForSelector('[data-read-code="sync_device_not_registered"]')
    // Register through the existing identity-only owner using an explicit UI action.
    phase = 'registration'
    await page.getByRole('button', { name: 'Зарегистрировать браузер для доступа к облаку', exact: true }).click()
    await page.waitForFunction(() => !document.querySelector('[data-testid="cloud-project-read"] button')?.disabled)
    phase = 'read'
    await page.getByTestId('cloud-project-read').getByRole('button').click()
    if (failure) {
      await page.locator("[data-read-code]").waitFor()
      assert.equal(await page.locator("[data-read-code]").getAttribute("data-read-code"), failure)
      assert.equal(await page.getByTestId('cloud-project-metadata').count(), 0)
    } else {
      await page.getByTestId('cloud-project-metadata').getByRole('heading').waitFor()
      assert.match(await page.getByTestId('cloud-project-metadata').innerText(), /PRIVATE_CLOUD_Valid_/)
      assert.match(await page.getByTestId('cloud-project-metadata').innerText(), /Тексты, этапы, заметки и другие данные ещё не открыты/)
      failNetwork = true
      await page.getByTestId('cloud-project-read').getByRole('button').click()
      await page.waitForSelector('[data-read-code="connection_failed"]')
      assert.equal(await page.getByTestId('cloud-project-metadata').count(), 0)
      failNetwork = false
      await page.getByTestId('cloud-project-read').getByRole('button').click()
      await page.getByTestId('cloud-project-metadata').getByRole('heading').waitFor()
      await page.locator('li').filter({ has: page.locator('code').filter({ hasText: /^second-project$/ }) }).getByRole('button').click()
      await page.waitForFunction(() => document.querySelector('[data-testid="cloud-project-metadata"]')?.textContent.includes('PRIVATE_CLOUD_Valid_second-project'))
      assert.equal((await page.getByTestId('cloud-project-metadata').innerText()).includes('PRIVATE_CLOUD_Valid_server-project'), false)
    }
    const after = await page.evaluate(async () => {
      const r = {}; for (const store of ['identities', 'accountBindings', 'localProjects', 'localNotes', 'localStages', 'localDocuments', 'inbox', 'outbox', 'ownerHeads', 'cursors', 'projectBindings', 'receipts', 'legacyNoteHistory', 'legacyNoteIntents']) r[store] = await harness.rows(store)
      return r
    })
    assert.deepEqual(after, before)
    await page.getByRole('button', { name: 'Заблокировать ключ', exact: true }).click()
    await page.waitForSelector('[data-status="locked"]')
    assert.equal(await page.getByTestId('cloud-project-read').count(), 0)
    assert.equal((await page.locator('body').innerText()).includes('PRIVATE_CLOUD_'), false)
    await page.getByRole('button', { name: 'Выйти из аккаунта', exact: true }).click()
    await page.waitForSelector('[data-status="logged_out"]')
  }
  const allowed = ['/api/v1/cloud/projects', '/api/v1/cloud/projects/bootstrap', '/api/v2/sync/encrypted/capabilities', '/api/v3/sync/encrypted/pull', '/api/v1/auth/logout']
  assert.deepEqual(pageErrors, [])
  assert.equal(registrations.filter(r => r.method === 'PUT' && r.path.startsWith('/api/v1/sync/devices/')).length, 5)
  assert.equal(registrations.some(r => r.method !== 'GET' && !(r.method === 'PUT' && r.path.startsWith('/api/v1/sync/devices/'))), false)
  assert.equal(reads.some(r => r.method !== 'GET' && r.path !== '/api/v1/auth/logout'), false)
  assert.equal(reads.some(r => !allowed.includes(r.path)), false)
  console.log(JSON.stringify({ pass: true, scenarios: 5, identities, readerRequests: reads.length, readerWrites: 0 }))
} finally { await context.close(); await browser.close() }
