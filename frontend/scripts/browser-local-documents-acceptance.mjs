import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'worta-local-documents-'))
const calls = []
const bodies = []
let context
let records
let offline = false

async function launch() {
  context = await chromium.launchPersistentContext(directory, { headless: true, locale: 'ru-RU' })
  await context.route(url => url.pathname.startsWith('/api/'), async route => {
    const request = route.request(), path = new URL(request.url()).pathname
    calls.push(path)
    bodies.push(request.postData() ?? '')
    if (offline) return route.abort('failed')
    const send = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (path === '/api/v1/auth/login' && request.method() === 'POST') {
      const { username, password } = request.postDataJSON()
      if (username !== 'one' || password !== 'account-password') return send({ detail: { code: 'invalid_credentials' } }, 401)
      return send({ access_token: 'synthetic-access-one', refresh_token: 'synthetic-refresh-one', access_expires_in: 60 })
    }
    if (request.headers().authorization !== 'Bearer synthetic-access-one') return send({ detail: { code: 'unauthorized' } }, 401)
    if (path === '/api/v1/account/me' && request.method() === 'GET') return send({ id: '11111111-1111-4111-8111-111111111111', username: 'one', email: 'one@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' })
    if (path === '/api/v1/legal/documents/status' && request.method() === 'GET') return send({ documents: [], missing_required_document_ids: [] })
    if (path === '/api/v1/account/crypto' && request.method() === 'GET') return send(records.one)
    if (path === '/api/v1/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204 })
    return send({ detail: { code: 'unexpected_api' } }, 404)
  })
}

async function openPage() {
  const page = await context.newPage()
  await page.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
  await page.waitForFunction(() => !!window.harness)
  await page.evaluate(() => harness.mountAccountCard())
  return page
}

async function login(page) {
  await page.locator('input[autocomplete="username"]').fill('one')
  await page.locator('input[autocomplete="current-password"]').fill('account-password')
  await page.getByRole('button', { name: 'Войти в облачный аккаунт' }).click()
  await page.locator('[data-status="authenticated"]').waitFor()
  await page.getByLabel('Пароль шифрования').fill('encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.locator('[data-status="unlocked"]').waitFor()
  await page.getByRole('button', { name: 'Открыть локальные тестовые проекты (не синхронизированы)' }).click()
  await page.getByTestId('encrypted-local-workspace').waitFor()
}

async function openDocument(page, label) {
  await page.getByRole('button', { name: label }).click()
  await page.getByTestId('encrypted-document-editor').waitFor()
  await page.locator('.nf-editor-content[contenteditable="true"]').waitFor()
}

async function save(page) {
  await page.getByRole('button', { name: /Сохранить текст|Save text/ }).click()
  await page.getByTestId('encrypted-document-save-status').filter({ hasText: /Сохранено|Saved/ }).waitFor({ timeout: 15000 }).catch(() => undefined)
  const status = await page.getByTestId('encrypted-document-save-status').innerText()
  const revisions = (await page.evaluate(async () => harness.rows('localDocuments'))).map(row => row.revision)
  assert.match(status, /Сохранено|Saved/, `${status}: ${await page.locator('[role="alert"]').allInnerTexts()}; revisions=${revisions}`)
}

try {
  await launch()
  let page = await openPage()
  records = await page.evaluate(() => harness.createRecords())
  await login(page)
  await page.getByLabel('Название локального проекта').first().fill('PRIVATE_MANUSCRIPT_PROJECT')
  await page.getByRole('button', { name: 'Создать зашифрованный проект' }).click()
  await page.getByTestId('encrypted-new-stage').getByRole('textbox').fill('PRIVATE_STAGE_A')
  await page.getByRole('button', { name: 'Добавить этап' }).click()
  await page.getByTestId('encrypted-stage-list').getByText('PRIVATE_STAGE_A').waitFor()
  await page.getByTestId('encrypted-new-stage').getByRole('textbox').fill('PRIVATE_STAGE_B')
  await page.getByRole('button', { name: 'Добавить этап' }).click()
  await page.getByTestId('encrypted-stage-list').getByText('PRIVATE_STAGE_B').waitFor()
  assert.equal(await page.getByRole('button', { name: /Открыть текст проекта|Open project text/ }).count(), 1, await page.getByTestId('encrypted-local-workspace').innerText())

  await openDocument(page, /Открыть текст проекта|Open project text/)
  let editor = page.locator('.nf-editor-content[contenteditable="true"]')
  await editor.fill('PRIVATE_PROJECT_TEXT_РУССКИЙ')
  await editor.press('ControlOrMeta+A')
  await page.getByRole('button', { name: /Полужирный|Bold/ }).click()
  await editor.locator('strong').waitFor()
  await save(page)
  assert.match(await editor.locator('strong').innerText(), /PRIVATE_PROJECT_TEXT/)
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()

  await page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_A' }).getByRole('button', { name: /Открыть текст этапа|Open stage text/ }).click()
  await editor.fill('PRIVATE_STAGE_A_TEXT')
  await editor.press('ControlOrMeta+A')
  await page.getByRole('button', { name: /Курсив|Italic/ }).click()
  await editor.locator('em').waitFor()
  await save(page)
  assert.match(await editor.locator('em').innerText(), /PRIVATE_STAGE_A_TEXT/)
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()

  await page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_B' }).getByRole('button', { name: /Открыть текст этапа|Open stage text/ }).click()
  await editor.fill('PRIVATE_STAGE_B_TEXT')
  await save(page)
  assert.equal(await editor.innerText(), 'PRIVATE_STAGE_B_TEXT')
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()

  const before = await page.evaluate(async () => ({ projects: await harness.rows('localProjects'), stages: await harness.rows('localStages'), notes: await harness.rows('localNotes'), documents: await harness.rows('localDocuments') }))
  assert.equal(before.documents.length, 3)
  for (const value of ['PRIVATE_PROJECT_TEXT', 'PRIVATE_STAGE_A_TEXT', 'PRIVATE_STAGE_B_TEXT', 'PRIVATE_MANUSCRIPT_PROJECT']) assert.equal(JSON.stringify(before).includes(value), false)
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)

  await context.close()
  await launch()
  page = await openPage()
  await page.evaluate(value => { harness.records = value }, records)
  await login(page)
  await openDocument(page, /Открыть текст проекта|Open project text/)
  editor = page.locator('.nf-editor-content[contenteditable="true"]')
  assert.equal(await editor.innerText(), 'PRIVATE_PROJECT_TEXT_РУССКИЙ')
  assert.match(await editor.locator('strong').innerText(), /PRIVATE_PROJECT_TEXT/)
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()
  await page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_A' }).getByRole('button', { name: /Открыть текст этапа|Open stage text/ }).click()
  assert.equal(await editor.innerText(), 'PRIVATE_STAGE_A_TEXT')
  assert.match(await editor.locator('em').innerText(), /PRIVATE_STAGE_A_TEXT/)
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()
  await page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_B' }).getByRole('button', { name: /Открыть текст этапа|Open stage text/ }).click()
  assert.equal(await editor.innerText(), 'PRIVATE_STAGE_B_TEXT')
  await page.evaluate(() => {
    const prototype = harness.realSession().constructor.prototype
    window.originalLocalNoteRepository = prototype.localNoteRepository
    prototype.localNoteRepository = function (...args) {
      const repository = originalLocalNoteRepository.apply(this, args)
      return { ...repository, documents: { ...repository.documents, save: async (...saveArgs) => {
        const committed = await repository.documents.save(...saveArgs)
        await new Promise(resolve => { window.releaseDocumentSave = resolve })
        return committed
      } } }
    }
  })
  await editor.fill('PRIVATE_STAGE_B_FAST_SAVE')
  await page.getByRole('button', { name: /Сохранить текст|Save text/ }).click()
  await page.waitForFunction(() => !!window.releaseDocumentSave)
  await editor.fill('PRIVATE_STAGE_B_TEXT')
  await page.evaluate(() => {
    const prototype = harness.realSession().constructor.prototype
    prototype.localNoteRepository = originalLocalNoteRepository
    delete window.originalLocalNoteRepository
    releaseDocumentSave()
    delete window.releaseDocumentSave
  })
  await page.getByTestId('encrypted-document-save-status').filter({ hasText: /Есть несохранённые изменения|Unsaved changes/ }).waitFor()
  assert.equal(await editor.innerText(), 'PRIVATE_STAGE_B_TEXT')
  await save(page)
  await page.evaluate(() => {
    window.originalDocumentPut = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === 'localDocuments') throw new DOMException('synthetic quota failure', 'QuotaExceededError')
      return originalDocumentPut.apply(this, args)
    }
  })
  await editor.fill('PRIVATE_STAGE_B_UNSAVED')
  await page.getByRole('button', { name: /Сохранить текст|Save text/ }).click()
  await page.getByTestId('encrypted-document-save-status').filter({ hasText: /Ошибка сохранения|Save failed/ }).waitFor()
  assert.equal(await editor.innerText(), 'PRIVATE_STAGE_B_UNSAVED')
  await page.evaluate(() => { IDBObjectStore.prototype.put = originalDocumentPut; delete window.originalDocumentPut })
  await save(page)
  offline = true
  await editor.fill('PRIVATE_STAGE_B_OFFLINE')
  await save(page)
  assert.deepEqual(await page.evaluate(async () => harness.rows('localDocuments')).then(rows => rows.length), 3)
  offline = false
  await page.getByRole('button', { name: /Вернуться к проекту|Back to project/ }).click()
  await page.getByRole('button', { name: 'Выйти из аккаунта' }).click()
  await page.locator('[data-status="logged_out"]').waitFor()

  const repository = await page.evaluate(async value => {
    harness.records = value
    window.documentSession = harness.session()
    await documentSession.login('one', 'account-password')
    await documentSession.unlock('encryption-password')
    const repo = documentSession.localNoteRepository()
    const projects = await repo.source.listProjects(repo.scope)
    const id = projects.find(project => project.name === 'PRIVATE_MANUSCRIPT_PROJECT').id
    const stages = await repo.stages.list(repo.scope, id)
    window.documentScope = { id, stageA: stages.find(stage => stage.name === 'PRIVATE_STAGE_A'), stageB: stages.find(stage => stage.name === 'PRIVATE_STAGE_B') }
    return { projectId: id, stageIds: stages.map(stage => stage.id) }
  }, records)
  assert.equal(repository.stageIds.length, 2)

  const negative = await page.evaluate(async () => {
    const repo = documentSession.localNoteRepository(), { scope, documents, stages, source } = repo
    const { id, stageA, stageB } = documentScope
    const code = async action => { try { await action(); return 'unexpected_success' } catch (error) { return error.code ?? 'unknown' } }
    const initial = await documents.read(scope, id, null)
    const rawBefore = JSON.stringify(await harness.rows('localDocuments'))
    const stale = await code(() => documents.save(scope, id, null, initial.revision - 1, initial.content))
    const unknownStage = await code(() => documents.open(scope, id, 'missing-stage'))
    const wrongProject = await code(() => documents.open(scope, 'missing-project', stageA.id))
    const invalid = await code(() => documents.save(scope, id, null, initial.revision, { type: 'doc', content: [{ type: 'unknown' }] }))
    const oversized = await code(() => documents.save(scope, id, null, initial.revision, { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x'.repeat(1_100_000) }] }] }))
    const stageDelete = await code(() => stages.remove(scope, id, stageA.id, stageA.revision))
    const projectDelete = await code(async () => source.deleteProject(scope, (await source.readSnapshot(scope, id)).token, '2026-10-27T00:00:00.000000Z'))
    const rawAfter = JSON.stringify(await harness.rows('localDocuments'))
    return { stale, unknownStage, wrongProject, invalid, oversized, stageDelete, projectDelete, unchanged: rawBefore === rawAfter,
      project: (await documents.read(scope, id, null)).content, stageA: (await documents.read(scope, id, stageA.id)).content,
      stageB: (await documents.read(scope, id, stageB.id)).content }
  })
  assert.deepEqual([negative.stale, negative.unknownStage, negative.wrongProject, negative.invalid, negative.oversized, negative.stageDelete, negative.projectDelete],
    ['stale_source', 'missing_local_source', 'missing_local_source', 'invalid_local_source', 'source_limit', 'unsupported_local_source', 'unsupported_local_source'])
  assert.equal(negative.unchanged, true)
  assert.notDeepEqual(negative.project, negative.stageA)
  assert.notDeepEqual(negative.stageA, negative.stageB)

  const contention = await context.newPage()
  await contention.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
  await contention.evaluate(value => { harness.records = value }, records)
  assert.equal(await contention.evaluate(async () => {
    const second = harness.session()
    try { await second.login('one', 'account-password'); return 'unexpected_success' }
    catch (error) { return error.code ?? 'unknown' }
    finally { await second.dispose() }
  }), 'writer_busy')
  await contention.close()

  const durability = await page.evaluate(async () => {
    const repo = documentSession.localNoteRepository(), { scope, documents, source } = repo
    const { id, stageA, stageB } = documentScope
    const code = async action => { try { await action(); return 'unexpected_success' } catch (error) { return error.code ?? 'unknown' } }
    const project = await documents.read(scope, id, null)
    const first = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'PRIVATE_CONCURRENT_FIRST' }] }] }
    const second = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'PRIVATE_CONCURRENT_SECOND' }] }] }
    const competing = await Promise.allSettled([documents.save(scope, id, null, project.revision, first), documents.save(scope, id, null, project.revision, second)])
    const concurrent = competing.map(item => item.status === 'fulfilled' ? 'saved' : item.reason.code).sort()
    const afterConcurrent = await documents.read(scope, id, null)
    const beforeQuota = JSON.stringify(await harness.rows('localDocuments'))
    const put = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function (...args) { if (this.name === 'localDocuments') throw new DOMException('synthetic quota failure', 'QuotaExceededError'); return put.apply(this, args) }
    const quota = await code(() => documents.save(scope, id, null, afterConcurrent.revision, first))
    IDBObjectStore.prototype.put = put
    const quotaSame = JSON.stringify(await harness.rows('localDocuments')) === beforeQuota
    const row = (await harness.rows('localDocuments')).find(item => item.scope_key === `stage:${stageB.id}`)
    const tampered = structuredClone(row)
    tampered.envelope.ciphertext = `${tampered.envelope.ciphertext.slice(0, -1)}${tampered.envelope.ciphertext.endsWith('A') ? 'B' : 'A'}`
    const replace = async value => {
      const open = indexedDB.open('worta-web')
      const db = await new Promise((resolve, reject) => { open.onsuccess = () => resolve(open.result); open.onerror = () => reject(open.error) })
      try { await new Promise((resolve, reject) => { const tx = db.transaction('localDocuments', 'readwrite'); tx.objectStore('localDocuments').put(value); tx.oncomplete = resolve; tx.onabort = () => reject(tx.error) }) }
      finally { db.close() }
    }
    await replace(tampered)
    const corrupt = await code(() => documents.read(scope, id, stageB.id))
    await replace(row)
    const restored = (await documents.read(scope, id, stageB.id)).content
    const otherId = crypto.randomUUID()
    await source.createProject(scope, { id: otherId, name: 'PRIVATE_OTHER_PROJECT', goal: null, infinite: true, unit: 'symbols', status: 'активен', created_at: null, updated_at: null, payload: {} })
    const other = await documents.open(scope, otherId, null)
    const foreignStage = await code(() => documents.open(scope, otherId, stageA.id))
    const completedId = crypto.randomUUID()
    await source.createProject(scope, { id: completedId, name: 'PRIVATE_COMPLETED_PROJECT', goal: null, infinite: true, unit: 'symbols', status: 'завершен', created_at: null, updated_at: null, payload: {} })
    const completed = await code(() => documents.open(scope, completedId, null))
    const boundId = crypto.randomUUID()
    await source.createProject(scope, { id: boundId, name: 'PRIVATE_BOUND_PROJECT', goal: null, infinite: true, unit: 'symbols', status: 'активен', created_at: null, updated_at: null, payload: {} })
    const boundDocument = await documents.open(scope, boundId, null)
    const open = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { open.onsuccess = () => resolve(open.result); open.onerror = () => reject(open.error) })
    try { await new Promise((resolve, reject) => { const tx = db.transaction('projectBindings', 'readwrite'); tx.objectStore('projectBindings').add({ account_id: scope.accountId, project_id: boundId, bootstrap_id: crypto.randomUUID() }); tx.oncomplete = resolve; tx.onabort = () => reject(tx.error) }) }
    finally { db.close() }
    const bound = await code(() => documents.save(scope, boundId, null, boundDocument.revision, first))
    return { concurrent, revision: afterConcurrent.revision, quota, quotaSame, corrupt, restored, otherId, otherIdActual: other.project_id, foreignStage, completed, bound }
  })
  assert.deepEqual(durability.concurrent, ['saved', 'stale_source'])
  assert.equal(durability.quota, 'quota_exceeded')
  assert.equal(durability.quotaSame, true)
  assert.equal(durability.corrupt, 'corrupt_record')
  assert.equal(durability.restored.content[0].content[0].text, 'PRIVATE_STAGE_B_OFFLINE')
  assert.equal(durability.otherIdActual, durability.otherId)
  assert.equal(durability.foreignStage, 'missing_local_source')
  assert.equal(durability.completed, 'unsupported_local_source')
  assert.equal(durability.bound, 'unsupported_local_source')

  const lifecycle = await page.evaluate(async () => {
    let repo = documentSession.localNoteRepository(), { scope } = repo
    const oldRepo = repo
    const project = await repo.documents.read(scope, documentScope.id, null)
    const before = JSON.stringify(await harness.rows('localDocuments'))
    const put = IDBObjectStore.prototype.put
    let lockFlight
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === 'localDocuments') lockFlight = documentSession.lock()
      return put.apply(this, args)
    }
    let locked
    try { await repo.documents.save(scope, documentScope.id, null, project.revision, project.content); locked = 'unexpected_success' }
    catch (error) { locked = error.code ?? 'unknown' }
    finally { IDBObjectStore.prototype.put = put }
    await lockFlight
    await documentSession.unlock('encryption-password')
    repo = documentSession.localNoteRepository()
    const after = JSON.stringify(await harness.rows('localDocuments'))
    const readAfter = await repo.documents.read(repo.scope, documentScope.id, null)
    let staleHandle
    try { await oldRepo.documents.read(scope, documentScope.id, null); staleHandle = 'unexpected_success' }
    catch (error) { staleHandle = error.code ?? 'unknown' }
    let logoutFlight
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === 'localDocuments') logoutFlight = documentSession.logout()
      return put.apply(this, args)
    }
    let loggedOut
    try { await repo.documents.save(repo.scope, documentScope.id, null, readAfter.revision, readAfter.content); loggedOut = 'unexpected_success' }
    catch (error) { loggedOut = error.code ?? 'unknown' }
    finally { IDBObjectStore.prototype.put = put }
    await logoutFlight
    const logoutSame = JSON.stringify(await harness.rows('localDocuments')) === after
    await documentSession.login('one', 'account-password')
    await documentSession.unlock('encryption-password')
    const recovered = await documentSession.localNoteRepository().documents.read(documentSession.localNoteRepository().scope, documentScope.id, null)
    await documentSession.logout()
    await documentSession.login('two', 'account-password')
    await documentSession.unlock('encryption-password')
    const foreign = documentSession.localNoteRepository()
    let account
    try { await foreign.documents.read(foreign.scope, documentScope.id, null); account = 'unexpected_success' }
    catch (error) { account = error.code ?? 'unknown' }
    let oldScope
    try { await foreign.documents.read(scope, documentScope.id, null); oldScope = 'unexpected_success' }
    catch (error) { oldScope = error.code ?? 'unknown' }
    await documentSession.logout()
    return { locked, unchanged: before === after, readAfter: readAfter.revision, staleHandle, loggedOut, logoutSame,
      recoveredRevision: recovered.revision, account, oldScope }
  })
  assert.notEqual(lifecycle.locked, 'unexpected_success')
  assert.equal(lifecycle.unchanged, true)
  assert.equal(lifecycle.readAfter, durability.revision)
  assert.equal(lifecycle.staleHandle, 'closed')
  assert.notEqual(lifecycle.loggedOut, 'unexpected_success')
  assert.equal(lifecycle.logoutSame, true)
  assert.equal(lifecycle.recoveredRevision, durability.revision)
  assert.equal(lifecycle.account, 'missing_local_source')
  assert.equal(lifecycle.oldScope, 'account_mismatch')

  assert.ok(calls.includes('/api/v1/legal/documents/status'))
  assert.ok(calls.every(path => ['/api/v1/auth/login', '/api/v1/legal/documents/status', '/api/v1/account/me', '/api/v1/account/crypto', '/api/v1/auth/logout'].includes(path)))
  for (const body of bodies) for (const value of ['PRIVATE_PROJECT_TEXT', 'PRIVATE_STAGE_A_TEXT', 'PRIVATE_STAGE_B_TEXT']) assert.equal(body.includes(value), false)
  console.log('Chromium local documents PASS: existing Tiptap editor, formatting, project/two stage scopes, committed saves, offline edit, restart, ciphertext only, conflict/owner/size/format guards, writer contention and no document API writes')
} finally {
  await context?.close()
  await rm(directory, { recursive: true, force: true })
}
