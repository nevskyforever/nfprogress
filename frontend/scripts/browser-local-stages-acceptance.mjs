import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const origin = new URL(process.argv[2] || 'http://127.0.0.1:5173').origin
assert.equal(new URL(origin).hostname, '127.0.0.1')
const directory = await mkdtemp(join(tmpdir(), 'worta-local-stages-'))
const corruptDirectory = await mkdtemp(join(tmpdir(), 'worta-local-stages-bad-'))
let context

async function page() {
  const tab = await context.newPage()
  await tab.goto(`${origin}/scripts/browser-cloud-account-harness.html`)
  await tab.waitForFunction(() => !!window.harness)
  return tab
}

try {
  context = await chromium.launchPersistentContext(directory, { headless: true })
  let tab = await page()
  const records = await tab.evaluate(() => harness.createRecords(true))
  const before = await tab.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }))
  assert.equal(before.projects.length, 1)
  assert.equal(before.notes.length, 1)
  for (const value of ['PRIVATE_V10_PROJECT', 'PRIVATE_V10_NOTE', 'PRIVATE_V10_BODY']) assert.equal(JSON.stringify(before).includes(value), false)

  const result = await tab.evaluate(async () => {
    const session = harness.session()
    await session.login('one', 'account-password')
    await session.unlock('encryption-password')
    const repository = session.localNoteRepository(), { scope, source, stages } = repository
    const oldProjects = await source.listProjects(scope)
    const oldSnapshot = await source.readSnapshot(scope, 'v10-private-project')
    const oldSource = await source.withDecryptedSnapshot(scope, oldSnapshot.token, async value => value)
    const secondId = crypto.randomUUID()
    await source.createProject(scope, { id: secondId, name: 'PRIVATE_SECOND_PROJECT', goal: null, infinite: true, unit: 'symbols', status: 'активен', created_at: null, updated_at: null, payload: {} })
    const first = await stages.create(scope, 'v10-private-project', 'PRIVATE_FIRST_STAGE', 'symbols')
    const second = await stages.create(scope, 'v10-private-project', 'PRIVATE_SECOND_STAGE', 'symbols')
    const other = await stages.create(scope, secondId, 'PRIVATE_OTHER_STAGE', 'symbols')
    const renamed = await stages.rename(scope, 'v10-private-project', second.id, 'PRIVATE_RENAMED_STAGE', second.revision)
    const reordered = await stages.list(scope, 'v10-private-project')
    await stages.reorder(scope, 'v10-private-project', [second.id, first.id], Object.fromEntries(reordered.map(stage => [stage.id, stage.revision])))
    const ordered = await stages.list(scope, 'v10-private-project')
    const deletionSnapshot = await source.readSnapshot(scope, 'v10-private-project')
    let projectDeletionBlocked = false
    try { await source.deleteProject(scope, deletionSnapshot.token, '2026-10-26T00:00:00.000000Z') } catch (error) { projectDeletionBlocked = error.code === 'unsupported_local_source' }
    let conflict = false
    try { await stages.rename(scope, 'v10-private-project', second.id, 'SHOULD_NOT_SAVE', renamed.revision) } catch (error) { conflict = error.code === 'stale_source' }
    const rawBeforeRollback = await harness.rows('localStages')
    const put = IDBObjectStore.prototype.put
    let rollback = false
    IDBObjectStore.prototype.put = function (...args) { if (this.name === 'localStages') throw new DOMException('synthetic stage failure', 'QuotaExceededError'); return put.apply(this, args) }
    try { await stages.rename(scope, 'v10-private-project', first.id, 'SHOULD_ROLL_BACK', ordered[1].revision) } catch { rollback = true }
    finally { IDBObjectStore.prototype.put = put }
    const rawAfterRollback = await harness.rows('localStages')
    const firstAfterOrder = ordered.find(stage => stage.id === first.id)
    await stages.remove(scope, 'v10-private-project', first.id, firstAfterOrder.revision)
    const afterRemove = await stages.list(scope, 'v10-private-project')
    const savedStage = (await harness.rows('localStages')).find(row => row.stage_id === second.id)
    const tampered = structuredClone(savedStage)
    tampered.envelope.ciphertext = `${tampered.envelope.ciphertext.slice(0, -1)}${tampered.envelope.ciphertext.endsWith('A') ? 'B' : 'A'}`
    const replace = async row => {
      const request = indexedDB.open('worta-web')
      const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
      try { await new Promise((resolve, reject) => { const tx = db.transaction('localStages', 'readwrite'); tx.objectStore('localStages').put(row); tx.oncomplete = resolve; tx.onabort = () => reject(tx.error) }) }
      finally { db.close() }
    }
    await replace(tampered)
    let corrupt = false
    try { await stages.list(scope, 'v10-private-project') } catch (error) { corrupt = error.code === 'corrupt_record' }
    await replace(savedStage)
    const restored = await stages.list(scope, 'v10-private-project')
    await session.lock()
    let revoked = false
    try { await stages.create(scope, secondId, 'SHOULD_NOT_SAVE', 'symbols') } catch { revoked = true }
    await session.logout()
    const otherSession = harness.session()
    await otherSession.login('two', 'account-password')
    await otherSession.unlock('encryption-password')
    const otherRepository = otherSession.localNoteRepository()
    const foreignProjects = await otherRepository.source.listProjects(otherRepository.scope)
    let isolated = false
    try { await otherRepository.stages.list(otherRepository.scope, secondId) } catch { isolated = true }
    await otherSession.logout()
    return { oldProjects, oldNote: oldSource.notes[0].note.title, secondId, otherName: other.name, orderedNames: ordered.map(stage => stage.name), afterRemove: afterRemove.map(stage => stage.name), restored: restored.map(stage => stage.name), conflict, projectDeletionBlocked, rollback, rollbackSame: JSON.stringify(rawBeforeRollback) === JSON.stringify(rawAfterRollback), corrupt, revoked, foreignCount: foreignProjects.length, isolated }
  })
  assert.equal(result.oldProjects[0].name, 'PRIVATE_V10_PROJECT')
  assert.equal(result.oldNote, 'PRIVATE_V10_NOTE')
  assert.deepEqual(result.orderedNames, ['PRIVATE_RENAMED_STAGE', 'PRIVATE_FIRST_STAGE'])
  assert.deepEqual(result.afterRemove, ['PRIVATE_RENAMED_STAGE'])
  assert.deepEqual(result.restored, ['PRIVATE_RENAMED_STAGE'])
  for (const key of ['conflict', 'projectDeletionBlocked', 'rollback', 'rollbackSame', 'corrupt', 'revoked', 'isolated']) assert.equal(result[key], true, key)
  assert.equal(result.foreignCount, 0)
  const after = await tab.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes'), stages: await harness.rows('localStages') }))
  assert.deepEqual(after.projects.find(row => row.project_id === 'v10-private-project'), before.projects[0])
  assert.deepEqual(after.notes, before.notes)
  assert.equal(after.stages.length, 2)
  for (const value of ['PRIVATE_V10_PROJECT', 'PRIVATE_V10_NOTE', 'PRIVATE_V10_BODY', 'PRIVATE_RENAMED_STAGE', 'PRIVATE_OTHER_STAGE', 'SHOULD_ROLL_BACK']) assert.equal(JSON.stringify(after).includes(value), false)

  await context.close()
  context = await chromium.launchPersistentContext(directory, { headless: true })
  tab = await page()
  await tab.evaluate(value => { harness.records = value }, records)
  const reopened = await tab.evaluate(async id => {
    const session = harness.session()
    await session.login('one', 'account-password')
    await session.unlock('encryption-password')
    const repository = session.localNoteRepository()
    const projects = await repository.source.listProjects(repository.scope)
    const old = await repository.source.readSnapshot(repository.scope, 'v10-private-project')
    const notes = await repository.source.withDecryptedSnapshot(repository.scope, old.token, async value => value.notes)
    const first = await repository.stages.list(repository.scope, 'v10-private-project')
    const second = await repository.stages.list(repository.scope, id)
    await session.logout()
    return { projects: projects.map(project => project.name), note: notes[0].note.title, first: first.map(stage => stage.name), second: second.map(stage => stage.name) }
  }, result.secondId)
  assert.deepEqual(reopened.first, ['PRIVATE_RENAMED_STAGE'])
  assert.deepEqual(reopened.second, ['PRIVATE_OTHER_STAGE'])
  assert.equal(reopened.note, 'PRIVATE_V10_NOTE')
  assert.equal(reopened.projects.length, 2)
  await context.close()
  context = await chromium.launchPersistentContext(corruptDirectory, { headless: true })
  tab = await page()
  await tab.evaluate(() => harness.createRecords(true))
  await tab.evaluate(async () => {
    const request = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    try {
      await new Promise((resolve, reject) => {
        const tx = db.transaction('identities', 'readwrite'), store = tx.objectStore('identities')
        const read = store.get('11111111-1111-4111-8111-111111111111')
        read.onsuccess = () => store.put({ ...read.result, record_version: 99 })
        tx.oncomplete = resolve; tx.onabort = () => reject(tx.error)
      })
    } finally { db.close() }
  })
  const corruptBefore = await tab.evaluate(async () => ({ projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }))
  const rejected = await tab.evaluate(async () => {
    const session = harness.session()
    try { await session.login('one', 'account-password'); return false }
    catch { return true }
    finally { await session.dispose() }
  })
  assert.equal(rejected, true)
  const corruptAfter = await tab.evaluate(async () => {
    const request = indexedDB.open('worta-web')
    const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    const version = db.version; db.close()
    return { version, projects: await harness.rows('localProjects'), notes: await harness.rows('localNotes') }
  })
  assert.equal(corruptAfter.version, 10)
  assert.deepEqual(corruptAfter.projects, corruptBefore.projects)
  assert.deepEqual(corruptAfter.notes, corruptBefore.notes)
  console.log('Chromium local stages PASS: v10 to v12 preservation and atomic refusal, encrypted Stage CRUD/order, two projects, revision conflict, rollback, tamper rejection, lock/logout, account isolation, browser restart')
} finally {
  await context?.close()
  await rm(directory, { recursive: true, force: true })
  await rm(corruptDirectory, { recursive: true, force: true })
}
