import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5174').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'worta-encrypted-workspace-'))
const calls = []
let context
let records

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
    const account = request.headers().authorization?.match(/^Bearer synthetic-access-(one|two)$/)?.[1]
    if (!account) return send({ detail: { code: 'unauthorized' } }, 401)
    if (path === '/api/v1/account/me' && request.method() === 'GET') return send({ id: account === 'one' ? '11111111-1111-4111-8111-111111111111' : '22222222-2222-4222-8222-222222222222', username: account, email: `${account}@example.test`, email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' })
    if (path === '/api/v1/legal/documents/status' && request.method() === 'GET') return send({ documents: [], missing_required_document_ids: [] })
    if (path === '/api/v1/legal/documents/accept' && request.method() === 'POST') return send({ documents: [], missing_required_document_ids: [] })
    if (path === '/api/v1/account/crypto' && request.method() === 'GET') return send(records[account])
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

async function loginAndUnlock(page) {
  await page.locator('input[autocomplete="username"]').fill('one')
  await page.locator('input[autocomplete="current-password"]').fill('account-password')
  await page.getByRole('button', { name: 'Войти в облачный аккаунт' }).click()
  await page.locator('[data-status="authenticated"]').waitFor()
  await page.locator('input[autocomplete="off"]').fill('wrong-encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.getByRole('alert').waitFor()
  await page.locator('[data-status="authenticated"]').waitFor()
  await page.getByLabel('Пароль шифрования').fill('encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.locator('[data-status="unlocked"]').waitFor()
}

try {
  await launch()
  let page = await openPage()
  records = await page.evaluate(() => harness.createRecords())
  await page.evaluate(value => { harness.records = value }, records)
  await loginAndUnlock(page)

  const secondTab = await openPage()
  await secondTab.evaluate(value => { harness.records = value }, records)
  await secondTab.locator('input[autocomplete="username"]').fill('one')
  await secondTab.locator('input[autocomplete="current-password"]').fill('account-password')
  await secondTab.getByRole('button', { name: 'Войти в облачный аккаунт' }).click()
  await secondTab.locator('[role="alert"]').waitFor()
  assert.match(await secondTab.locator('[role="alert"]').textContent(), /Другая вкладка использует защищённое хранилище|Another tab is using secure storage/)
  await secondTab.close()

  await page.getByRole('button', { name: 'Открыть зашифрованное локальное пространство' }).click()
  await page.getByTestId('encrypted-local-workspace').waitFor()
  await page.getByLabel('Название локального проекта').fill('Локальный тестовый проект')
  await page.getByRole('button', { name: 'Создать зашифрованный проект' }).click()
  await page.getByRole('heading', { name: 'Локальный тестовый проект', exact: true }).waitFor()
  await page.getByTestId('encrypted-new-stage').getByRole('textbox').fill('PRIVATE_STAGE_FIRST')
  await page.getByRole('button', { name: 'Добавить этап' }).click()
  await page.getByTestId('encrypted-stage-list').getByText('PRIVATE_STAGE_FIRST').waitFor()
  await page.getByTestId('encrypted-new-stage').getByRole('textbox').fill('PRIVATE_STAGE_SECOND')
  await page.getByRole('button', { name: 'Добавить этап' }).click()
  await page.getByTestId('encrypted-stage-list').getByText('PRIVATE_STAGE_SECOND').waitFor()
  const secondStage = page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_SECOND' })
  await secondStage.getByRole('button', { name: 'Переименовать' }).click()
  await page.getByTestId('encrypted-stage-list').getByRole('textbox').fill('PRIVATE_STAGE_RENAMED')
  await page.getByTestId('encrypted-stage-list').getByRole('button', { name: 'Сохранить' }).click()
  await page.getByTestId('encrypted-stage-list').getByText('PRIVATE_STAGE_RENAMED').waitFor()
  await page.getByRole('button', { name: 'Выше: PRIVATE_STAGE_RENAMED' }).click()
  await page.getByTestId('encrypted-stage-list').locator('li').first().getByText('PRIVATE_STAGE_RENAMED').waitFor()
  assert.match(await page.getByTestId('encrypted-stage-list').locator('li').first().textContent(), /PRIVATE_STAGE_RENAMED/)
  page.once('dialog', dialog => dialog.accept())
  await page.getByTestId('encrypted-stage-list').locator('li').filter({ hasText: 'PRIVATE_STAGE_FIRST' }).getByRole('button', { name: 'Удалить' }).click()
  await page.getByTestId('encrypted-new-project').getByRole('textbox').fill('PRIVATE_SECOND_PROJECT')
  await page.getByTestId('encrypted-new-project').getByRole('button', { name: 'Создать проект' }).click()
  await page.getByRole('heading', { name: 'PRIVATE_SECOND_PROJECT', exact: true }).waitFor()
  await page.getByTestId('encrypted-rename-project').getByRole('textbox').fill('PRIVATE_SECOND_PROJECT_RENAMED')
  await page.getByTestId('encrypted-rename-project').getByRole('button', { name: 'Сохранить' }).click()
  await page.getByRole('heading', { name: 'PRIVATE_SECOND_PROJECT_RENAMED', exact: true }).waitFor()
  await page.getByTestId('encrypted-new-stage').getByRole('textbox').fill('PRIVATE_OTHER_STAGE')
  await page.getByRole('button', { name: 'Добавить этап' }).click()
  await page.getByRole('button', { name: 'Локальный тестовый проект', exact: true }).click()
  await page.getByRole('button', { name: 'Новая заметка' }).click()
  await page.locator('#note-title').fill('PRIVATE_WORKSPACE_TITLE')
  await page.locator('.note-content-editor[contenteditable="true"]').fill('PRIVATE_WORKSPACE_BODY')
  await page.locator('.note-form__autosave').getByText('Изменения сохранены.').waitFor({ timeout: 5000 })
  await page.locator('button[aria-label="Закрыть"]').click()
  await page.getByRole('heading', { name: 'PRIVATE_WORKSPACE_TITLE' }).waitFor()

  const firstIdentity = await page.evaluate(async () => harness.rows('identities'))
  assert.equal(firstIdentity.length, 1)
  const beforeRestart = await page.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes'), stages: await harness.rows('localStages') }))
  assert.equal(beforeRestart.projects.length, 2)
  assert.equal(beforeRestart.notes.length, 1)
  assert.equal(beforeRestart.stages.length, 2)
  assert.ok(beforeRestart.notes[0].envelope.ciphertext)
  for (const plaintext of ['Локальный тестовый проект', 'PRIVATE_WORKSPACE_TITLE', 'PRIVATE_WORKSPACE_BODY', 'PRIVATE_STAGE_RENAMED', 'PRIVATE_SECOND_PROJECT_RENAMED', 'PRIVATE_OTHER_STAGE', 'account-password', 'encryption-password', 'masterKey']) {
    assert.equal(JSON.stringify(beforeRestart).includes(plaintext), false)
  }
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)

  await context.close()
  await launch()
  page = await openPage()
  await page.evaluate(value => { harness.records = value }, records)
  await loginAndUnlock(page)
  await page.getByRole('button', { name: 'Открыть зашифрованное локальное пространство' }).click()
  await page.getByRole('button', { name: 'Локальный тестовый проект', exact: true }).click()
  await page.getByRole('heading', { name: 'Локальный тестовый проект', exact: true }).waitFor()
  assert.match(await page.getByTestId('encrypted-stage-list').textContent(), /PRIVATE_STAGE_RENAMED/)
  assert.doesNotMatch(await page.getByTestId('encrypted-stage-list').textContent(), /PRIVATE_STAGE_FIRST/)
  await page.getByRole('button', { name: 'PRIVATE_SECOND_PROJECT_RENAMED' }).click()
  assert.match(await page.getByTestId('encrypted-stage-list').textContent(), /PRIVATE_OTHER_STAGE/)
  await page.getByRole('button', { name: 'Локальный тестовый проект', exact: true }).click()
  await page.getByRole('heading', { name: 'PRIVATE_WORKSPACE_TITLE' }).waitFor()
  await page.getByRole('button', { name: 'Редактировать заметку' }).click()
  await page.locator('.note-content-editor[contenteditable="true"]').waitFor()
  assert.equal(await page.locator('.note-content-editor').innerText(), 'PRIVATE_WORKSPACE_BODY')

  let closedDuringSave = false
  await page.exposeFunction('closeDuringEncryptedSave', async () => { closedDuringSave = true; await page.close() })
  await page.evaluate(() => {
    const put = IDBObjectStore.prototype.put
    let fired = false
    IDBObjectStore.prototype.put = function (...args) {
      const request = put.apply(this, args)
      if (!fired && this.name === 'localNotes') {
        fired = true
        IDBObjectStore.prototype.put = put
        queueMicrotask(() => { void window.closeDuringEncryptedSave() })
      }
      return request
    }
  })
  const tabClosed = page.waitForEvent('close')
  await page.locator('#note-title').fill('DROPPED_DURING_SAVE').catch(() => undefined)
  await tabClosed
  assert.equal(closedDuringSave, true)

  page = await openPage()
  await page.evaluate(value => { harness.records = value }, records)
  await loginAndUnlock(page)
  await page.getByRole('button', { name: 'Открыть зашифрованное локальное пространство' }).click()
  await page.getByRole('button', { name: 'Локальный тестовый проект', exact: true }).click()
  const recoveredTitle = page.getByRole('heading', { name: /^(PRIVATE_WORKSPACE_TITLE|DROPPED_DURING_SAVE)$/ })
  await recoveredTitle.waitFor()
  const titleAfterInterruptedSave = await recoveredTitle.innerText()
  assert.ok(['PRIVATE_WORKSPACE_TITLE', 'DROPPED_DURING_SAVE'].includes(titleAfterInterruptedSave))
  await page.getByRole('button', { name: 'Редактировать заметку' }).click()
  await page.locator('.note-content-editor[contenteditable="true"]').waitFor()
  assert.equal(await page.locator('.note-content-editor').innerText(), 'PRIVATE_WORKSPACE_BODY')
  await page.getByRole('button', { name: 'Закрыть', exact: true }).click()
  await page.locator('#note-title').waitFor({ state: 'detached' })
  await page.getByRole('button', { name: 'Заблокировать ключ' }).click()
  await page.getByTestId('encrypted-local-workspace').waitFor({ state: 'detached' })
  assert.equal(await page.locator('[data-status]').getAttribute('data-status'), 'locked')

  await page.getByRole('button', { name: 'Выйти из аккаунта' }).click()
  await page.locator('[data-status="logged_out"]').waitFor()
  await page.locator('input[autocomplete="username"]').fill('two')
  await page.locator('input[autocomplete="current-password"]').fill('account-password')
  await page.getByRole('button', { name: 'Войти в облачный аккаунт' }).click()
  await page.locator('[data-status="authenticated"]').waitFor()
  await page.getByLabel('Пароль шифрования').fill('encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.locator('[data-status="unlocked"]').waitFor()
  await page.getByRole('button', { name: 'Открыть зашифрованное локальное пространство' }).click()
  await page.locator('form.encrypted-workspace__create').waitFor()
  assert.equal(await page.getByRole('heading', { name: 'PRIVATE_WORKSPACE_TITLE' }).count(), 0)

  await page.getByRole('button', { name: 'Выйти из аккаунта' }).click()
  await page.locator('[data-status="logged_out"]').waitFor()
  await page.locator('input[autocomplete="username"]').fill('one')
  await page.locator('input[autocomplete="current-password"]').fill('account-password')
  await page.getByRole('button', { name: 'Войти в облачный аккаунт' }).click()
  await page.locator('[data-status="authenticated"]').waitFor()
  await page.getByLabel('Пароль шифрования').fill('encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.locator('[data-status="unlocked"]').waitFor()
  await page.getByRole('button', { name: 'Заблокировать ключ' }).click()
  await page.locator('[data-status="locked"]').waitFor()

  await page.evaluate(async () => {
    const open = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { open.onsuccess = () => resolve(open.result); open.onerror = () => reject(open.error) })
    await new Promise((resolve, reject) => {
      const tx = db.transaction('localNotes', 'readwrite')
      const store = tx.objectStore('localNotes')
      const request = store.getAll()
      request.onsuccess = () => {
        const row = request.result[0]
        row.envelope.ciphertext = `${row.envelope.ciphertext.slice(0, -1)}${row.envelope.ciphertext.endsWith('A') ? 'B' : 'A'}`
        store.put(row)
      }
      tx.oncomplete = resolve
      tx.onabort = () => reject(tx.error)
    })
    db.close()
  })
  await page.getByLabel('Пароль шифрования').fill('encryption-password')
  await page.getByRole('button', { name: 'Разблокировать' }).click()
  await page.locator('[data-status="unlocked"]').waitFor()
  await page.getByRole('button', { name: 'Открыть зашифрованное локальное пространство' }).click()
  await page.getByRole('alert').filter({ hasText: 'Зашифрованная заметка повреждена' }).waitFor()
  assert.equal((await page.evaluate(async () => harness.rows('localNotes'))).length, 1)

  const stored = await page.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }))
  assert.equal(stored.notes.length, 1)
  for (const plaintext of ['Локальный тестовый проект', 'PRIVATE_WORKSPACE_TITLE', 'DROPPED_DURING_SAVE', 'PRIVATE_WORKSPACE_BODY', 'account-password', 'encryption-password', 'masterKey']) {
    assert.equal(JSON.stringify(stored).includes(plaintext), false)
  }
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)
  assert.ok(calls.includes('/api/v1/auth/login') && calls.includes('/api/v1/legal/documents/status') && calls.includes('/api/v1/account/me') && calls.includes('/api/v1/account/crypto'))
  assert.ok(calls.every(path => ['/api/v1/auth/login', '/api/v1/legal/documents/status', '/api/v1/legal/documents/accept', '/api/v1/account/me', '/api/v1/account/crypto', '/api/v1/auth/logout'].includes(path)))
  console.log('Chromium encrypted workspace PASS: two projects, Stage CRUD/order, project rename, Notes, restart, account isolation, lock/logout, rollback, ciphertext storage and no plaintext project/Stage API calls')
} finally {
  await context?.close()
  await rm(directory, { recursive: true, force: true })
}
