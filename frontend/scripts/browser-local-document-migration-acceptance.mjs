import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const baseline = '508a1a98a3da8686e0b4168ba6d6d5b4dfd931a5'
const repoRoot = resolve(process.cwd(), '..')
const historicalFile = resolve('src/platform/web/pinnedV11DocumentAcceptance.ts')
const historical = execFileSync('git', ['show', `${baseline}:frontend/src/platform/web/persistence.ts`], { cwd: repoRoot })
await writeFile(historicalFile, historical)
const directory = await mkdtemp(join(tmpdir(), 'worta-v11-v12-documents-'))
const corruptDirectory = await mkdtemp(join(tmpdir(), 'worta-v11-v12-documents-bad-'))
let context

async function page() {
  const tab = await context.newPage()
  await tab.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
  await tab.waitForFunction(() => !!window.harness)
  return tab
}

async function snapshot(tab) {
  return tab.evaluate(async () => {
    const request = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    try {
      const names = Array.from(db.objectStoreNames).sort(), tx = db.transaction(names)
      const shape = names.map(name => {
        const store = tx.objectStore(name)
        return [name, store.keyPath, Array.from(store.indexNames).map(index => [index, store.index(index).keyPath, store.index(index).unique])]
      })
      const rows = Object.fromEntries(await Promise.all(names.map(async name => [name, await new Promise((resolve, reject) => {
        const read = tx.objectStore(name).getAll()
        read.onsuccess = () => resolve(read.result)
        read.onerror = () => reject(read.error)
      })])))
      return { version: db.version, shape, rows }
    } finally { db.close() }
  })
}

try {
  context = await chromium.launchPersistentContext(directory, { headless: true })
  let tab = await page()
  const records = await tab.evaluate(() => harness.createRecords(true, true))
  const before = await snapshot(tab)
  assert.equal(before.version, 11)
  assert.equal(before.shape.length, 13)
  assert.equal(before.rows.localProjects.length, 1)
  assert.equal(before.rows.localNotes.length, 1)
  assert.equal(before.rows.localStages.length, 1)
  assert.equal(before.rows.cursors.length, 1)
  const upgraded = await tab.evaluate(async () => {
    window.documentSession = harness.session()
    await documentSession.login('one', 'account-password')
    await documentSession.unlock('encryption-password')
    const repo = documentSession.localNoteRepository()
    const projects = await repo.source.listProjects(repo.scope)
    const stage = (await repo.stages.list(repo.scope, 'v10-private-project'))[0]
    const source = await repo.source.readSnapshot(repo.scope, 'v10-private-project')
    const notes = await repo.source.withDecryptedSnapshot(repo.scope, source.token, async value => value.notes)
    const empty = await repo.documents.open(repo.scope, 'v10-private-project', stage.id)
    const saved = await repo.documents.save(repo.scope, 'v10-private-project', stage.id, empty.revision,
      { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'PRIVATE_MIGRATED_STAGE_TEXT' }] }] })
    await documentSession.logout()
    return { projects: projects.map(item => item.name), stage: stage.name, note: notes[0].note.title,
      emptyRevision: empty.revision, savedRevision: saved.revision }
  })
  assert.deepEqual(upgraded.projects, ['PRIVATE_V10_PROJECT'])
  assert.equal(upgraded.stage, 'PRIVATE_V11_STAGE')
  assert.equal(upgraded.note, 'PRIVATE_V10_NOTE')
  assert.equal(upgraded.emptyRevision, 1)
  assert.equal(upgraded.savedRevision, 2)
  const after = await snapshot(tab)
  assert.equal(after.version, 12)
  assert.equal(after.shape.length, 14)
  assert.deepEqual(after.shape.filter(([name]) => name !== 'localDocuments'), before.shape)
  assert.deepEqual(Object.fromEntries(Object.entries(after.rows).filter(([name]) => name !== 'localDocuments')), before.rows)
  assert.equal(after.rows.localDocuments.length, 1)
  assert.equal(JSON.stringify(after).includes('PRIVATE_MIGRATED_STAGE_TEXT'), false)

  const oldRefusal = await tab.evaluate(async () => {
    const old = await import('/src/platform/web/pinnedV11DocumentAcceptance.ts')
    if (old.WEB_DATABASE_VERSION !== 11) throw Error('Pinned baseline is not IndexedDB v11')
    try { const storage = await old.openBrowserPersistence('11111111-1111-4111-8111-111111111111'); await storage.close(); return 'unsafe_open' }
    catch (error) { return error.code ?? 'unknown' }
  })
  assert.equal(oldRefusal, 'unsupported_version')
  assert.deepEqual(await snapshot(tab), after)

  await context.close()
  context = await chromium.launchPersistentContext(directory, { headless: true })
  tab = await page()
  await tab.evaluate(value => { harness.records = value }, records)
  const recovered = await tab.evaluate(async () => {
    const session = harness.session()
    await session.login('one', 'account-password')
    await session.unlock('encryption-password')
    const repo = session.localNoteRepository()
    const stage = (await repo.stages.list(repo.scope, 'v10-private-project'))[0]
    const document = await repo.documents.read(repo.scope, 'v10-private-project', stage.id)
    await session.logout()
    return { stage: stage.name, document }
  })
  assert.equal(recovered.stage, 'PRIVATE_V11_STAGE')
  assert.equal(recovered.document.revision, 2)
  assert.equal(recovered.document.content.content[0].content[0].text, 'PRIVATE_MIGRATED_STAGE_TEXT')
  assert.deepEqual(await snapshot(tab), after)

  await context.close()
  context = await chromium.launchPersistentContext(corruptDirectory, { headless: true })
  tab = await page()
  await tab.evaluate(() => harness.createRecords(true, true))
  await tab.evaluate(async () => {
    const request = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    try { await new Promise((resolve, reject) => {
      const tx = db.transaction('identities', 'readwrite'), store = tx.objectStore('identities')
      const read = store.get('11111111-1111-4111-8111-111111111111')
      read.onsuccess = () => store.put({ ...read.result, record_version: 99 })
      tx.oncomplete = resolve; tx.onabort = () => reject(tx.error)
    }) } finally { db.close() }
  })
  const corruptBefore = await snapshot(tab)
  const refusal = await tab.evaluate(async () => {
    const session = harness.session()
    try { await session.login('one', 'account-password'); return 'unsafe_open' }
    catch (error) { return error.code ?? 'unknown' }
    finally { await session.dispose() }
  })
  assert.equal(refusal, 'corrupt_record')
  assert.deepEqual(await snapshot(tab), corruptBefore)
  assert.equal(corruptBefore.version, 11)
  console.log('Chromium v11→v12 documents migration PASS: exact legacy project, Stage, Note and C21 cursor bytes; atomic corrupt refusal; pinned v11 client refusal; v12 restart/recovery and encrypted manuscript')
} finally {
  await context?.close()
  await rm(directory, { recursive: true, force: true })
  await rm(corruptDirectory, { recursive: true, force: true })
  await rm(historicalFile, { force: true })
}
