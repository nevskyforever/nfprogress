/** C21.1.10: production local source and v5 upgrade against real IDB, crypto, auth and disk. */
import assert from 'node:assert/strict'
export async function acceptLocalAuthority({ page, scope, otherScope, users, cases, expectCode, tab, reopenProfile }) {
  const oldStores = ['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads']
  const rows = async () => Object.fromEntries(await Promise.all(oldStores.map(async store => [store, await page.evaluate(store => nativeRows(store), store)])))
  const old = await rows()
  const schema = await page.evaluate(async stores => {
    const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = reject })
    try { return stores.map(name => { const s = db.transaction(name).objectStore(name); return { name, keyPath: s.keyPath, indexes: Array.from(s.indexNames, name => { const i = s.index(name); return { name, keyPath: i.keyPath, unique: i.unique } }) } }) } finally { db.close() }
  }, oldStores)
  await page.evaluate(async () => { await meta.keys.dispose(); await session.close() })
  // Disposable fixture only. Production opener must NEVER clear or recreate a database.
  const seedV5 = async corrupt => page.evaluate(async ({ schema, old, corrupt }) => {
    await new Promise((resolve, reject) => { const r = indexedDB.deleteDatabase(c21.WEB_DATABASE_NAME); r.onsuccess = resolve; r.onerror = reject })
    const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME, 5); r.onerror = reject; r.onsuccess = () => resolve(r.result); r.onupgradeneeded = () => { for (const s of schema) { const store = r.result.createObjectStore(s.name, { keyPath: s.keyPath }); for (const i of s.indexes) store.createIndex(i.name, i.keyPath, { unique: i.unique }) } } })
    try { await c21.runBrowserTransaction(db, schema.map(s => s.name), 'readwrite', (tx, result) => { for (const [name, rows] of Object.entries(old)) for (const row of rows) tx.objectStore(name).add(corrupt === name ? { ...row, record_version: 99 } : row); result(undefined) }) } finally { db.close() }
  }, { schema, old, corrupt })
  const inspectSchema = () => page.evaluate(async () => { const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = reject }); const result = { version: db.version, stores: Array.from(db.objectStoreNames) }; db.close(); return result })
  for (const corrupt of ['ownerHeads','inbox','receipts']) {
    await seedV5(corrupt); await expectCode(page, 'c21.openBrowserPersistence(users[0])', 'corrupt_record')
    assert.deepEqual(await inspectSchema(), { version: 5, stores: [...oldStores].sort() })
    for (const name of oldStores.filter(name => name !== corrupt)) assert.deepEqual((await rows())[name], old[name])
  }
  cases.push('v5 applied Metadata/head/receipt corruption aborts upgrade: all eight stores retained, no local source synthesized')
  for (const mode of ['abort','quota']) {
    await seedV5(null)
    const result = await page.evaluate(async mode => {
      const create = IDBDatabase.prototype.createObjectStore
      IDBDatabase.prototype.createObjectStore = function(name, ...args) {
        const store = create.call(this, name, ...args)
        if (name === 'localNotes') { if (mode === 'quota') throw new DOMException('isolated_fixture', 'QuotaExceededError'); store.transaction.abort() }
        return store
      }
      try { await c21.openBrowserPersistence(users[0]); return 'unexpected_success' } catch (e) { return e.code } finally { IDBDatabase.prototype.createObjectStore = create }
    }, mode)
    assert.equal(result, mode === 'quota' ? 'quota_exceeded' : 'storage_failed')
    assert.deepEqual(await inspectSchema(), { version: 5, stores: [...oldStores].sort() }); assert.deepEqual(await rows(), old)
  }
  cases.push('v5 forced versionchange abort and quota roll back both new stores and preserve all eight existing rows/bytes')
  await seedV5(null)
  await page.evaluate(async ({ scope, users }) => { globalThis.users = users; globalThis.scopeA = scope; globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope); globalThis.local = session.localSource.bind(meta.auth, meta.bindings, meta.keys) }, { scope, users })
  assert.deepEqual(await inspectSchema(), { version: 7, stores: [...oldStores,'localProjects','localNotes','legacyNoteHistory'].sort() })
  assert.deepEqual(await rows(), old)
  assert.deepEqual(await page.evaluate(() => nativeRows('localProjects')), []); assert.deepEqual(await page.evaluate(() => nativeRows('localNotes')), [])
  cases.push('real v5 to v6 preserves every applied proof/head, receipt, encrypted wire and all eight stores exactly; local stores empty')
  const initFailure = await page.evaluate(async scope => {
    const add = IDBObjectStore.prototype.add
    IDBObjectStore.prototype.add = function(value, ...args) { if (this.name === 'localNotes') throw new DOMException('fixture', 'QuotaExceededError'); return add.call(this, value, ...args) }
    try {
      const project = { id: 'atomic-init-failed', name: 'PRIVATE_INIT_SENTINEL', goal: null, infinite: true, unit: 'symbols', status: 'active', created_at: null, updated_at: null, payload: {} }
      const note = { id: 'atomic-init-note', project_id: project.id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', title: 'PRIVATE_INIT_NOTE', content: '', checklist: [], color: 'default', pinned: false, archived: false, sort_order: 0, tags: [], created_at: '2026-10-13T00:00:00.000000Z', updated_at: '2026-10-13T00:00:00.000000Z', metadata: {}, revision: 0 }
      await local.initializeProject(scope, { project, notes: [{ state: 'live', note }] }); return 'unexpected_success'
    } catch (e) { return e.code } finally { IDBObjectStore.prototype.add = add }
  }, scope)
  assert.equal(initFailure, 'quota_exceeded'); assert.deepEqual(await page.evaluate(() => nativeRows('localProjects')), []); assert.deepEqual(await page.evaluate(() => nativeRows('localNotes')), [])
  cases.push('complete initialization quota after queued Project write rolls back Project and all Notes; no partial import')
  await page.evaluate(() => {
    const at = '2026-10-13T00:00:00.000000Z'
    globalThis.localAt = at
    globalThis.localProject = { id: 'pre-cloud-project', name: 'PRIVATE_LOCAL_PROJECT_SENTINEL', goal: null, infinite: true, unit: 'symbols', status: 'active', created_at: null, updated_at: null, payload: { personal_goal: 2, custom: { nullable: null, array: [false, 1] } } }
    globalThis.localNote = (id, project_id = localProject.id) => ({ id, project_id, stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null, content_format: 'html', title: 'PRIVATE_LOCAL_TITLE_SENTINEL', content: '<b>PRIVATE_LOCAL_BODY_SENTINEL</b>', checklist: [{ id: 'item', text: 'PRIVATE_CHECKLIST_SENTINEL', checked: false }], color: 'default', pinned: true, archived: false, sort_order: 2, tags: ['tag'], created_at: at, updated_at: at, metadata: { nested: [null, { preserved: true }] }, revision: 0 })
    globalThis.localSnap = () => local.readSnapshot(scopeA, localProject.id)
    globalThis.localRead = async () => local.withDecryptedSnapshot(scopeA, (await localSnap()).token, async data => structuredClone(data))
    globalThis.localRows = async () => ({ projects: await nativeRows('localProjects'), notes: await nativeRows('localNotes') })
    globalThis.localFutureCas = async token => {
      const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = reject })
      try { return await c21.runBrowserTransaction(db, ['localProjects','localNotes','outbox','projectBindings'], 'readwrite', (tx, result, abort) => c21.assertLocalSourceInTransaction(tx, scopeA, token, () => { if (!tx.objectStoreNames.contains('outbox') || !tx.objectStoreNames.contains('projectBindings')) throw Error('different_tx'); result(true) }, abort)) } finally { db.close() }
    }
  })
  const savedGlobals = await page.evaluate(() => ({ localProject, firstNote: localNote('z-note'), localAt }))
  assert.equal(await page.evaluate(() => local.createProject(scopeA, localProject)), 1)
  let durable = await page.evaluate(() => localRows())
  await expectCode(page, 'local.createProject(scopeA, localProject)', 'conflicting_record')
  assert.deepEqual(await page.evaluate(() => localRows()), durable)
  cases.push('pre-cloud canonical project creation needs normal unlocked account but no cloud binding; duplicate creation rejects without rewrite')
  assert.equal(await page.evaluate(async () => { globalThis.beforeNote = await localSnap(); return local.createNote(scopeA, beforeNote.token, localNote('z-note')) }), 2)
  assert.equal(await page.evaluate(async () => local.createNote(scopeA, (await localSnap()).token, localNote('a-note'))), 3)
  await expectCode(page, 'local.assertSnapshot(scopeA, beforeNote.token)', 'stale_source')
  await expectCode(page, 'localFutureCas(beforeNote.token)', 'stale_source')
  assert.deepEqual(await rows(), old)
  cases.push('each Note creation increments source exactly once; post-snapshot mutation invalidates old same-transaction future outbox/binding CAS without sync writes')
  const full = await page.evaluate(async () => { globalThis.currentLocal = await localSnap(); return localRead() })
  assert.equal(full.source_revision, 3); assert.deepEqual(full.notes.map(n => n.note.id), ['a-note','z-note']); assert.deepEqual(full.notes[1].note, savedGlobals.firstNote)
  assert.equal(await page.evaluate(() => localFutureCas(currentLocal.token)), true)
  const transactionReads = await page.evaluate(async () => {
    const transaction = IDBDatabase.prototype.transaction, calls = []
    IDBDatabase.prototype.transaction = function(stores, mode, ...options) { calls.push({ stores: typeof stores === 'string' ? [stores] : Array.from(stores), mode: mode ?? 'readonly' }); return transaction.call(this, stores, mode, ...options) }
    try { await localSnap(); return calls.filter(c => c.stores.includes('localProjects') || c.stores.includes('localNotes')) } finally { IDBDatabase.prototype.transaction = transaction }
  })
  assert.equal(transactionReads.length, 1); assert.equal(transactionReads[0].mode, 'readonly'); assert.equal(transactionReads[0].stores.includes('localProjects') && transactionReads[0].stores.includes('localNotes'), true)
  cases.push('complete deterministic all-field Note snapshot reads project and all membership in ONE readonly transaction; exact current future CAS passes')
  assert.equal(await page.evaluate(async () => local.updateNote(scopeA, (await localSnap()).token, 'a-note', { title: 'UPDATED_PRIVATE_SENTINEL', tags: null, pinned: null }, localAt)), 4)
  const updated = (await page.evaluate(() => localRead())).notes[0].note
  assert.equal(updated.revision, 1); assert.equal(updated.title, 'UPDATED_PRIVATE_SENTINEL'); assert.deepEqual(updated.tags, []); assert.equal(updated.pinned, false); assert.deepEqual(updated.metadata, savedGlobals.firstNote.metadata)
  durable = await page.evaluate(() => localRows())
  await expectCode(page, 'local.updateNote(scopeA, currentLocal.token, "a-note", {title:"stale"}, localAt)', 'stale_source')
  assert.deepEqual(await page.evaluate(() => localRows()), durable)
  cases.push('native Note update preserves routing/creation/metadata, null resets and local revision; stale mutation cannot partially write')
  for (const mode of ['abort','quota','keylock','close']) {
    durable = await page.evaluate(() => localRows())
    const code = await page.evaluate(async mode => {
      const put = IDBObjectStore.prototype.put
      IDBObjectStore.prototype.put = function(value, ...args) {
        if (this.name === 'localNotes' && mode === 'quota') throw new DOMException('isolated_fixture','QuotaExceededError')
        const r = put.call(this, value, ...args)
        if (this.name === 'localNotes') r.addEventListener('success', () => { if (mode === 'abort') this.transaction.abort(); else if (mode === 'keylock') void meta.keys.lock(); else if (mode === 'close') void session.close() }, { once: true })
        return r
      }
      try { await local.updateNote(scopeA, (await localSnap()).token, 'a-note', { content: 'ROLLBACK_PRIVATE_SENTINEL' }, localAt); return 'unexpected_success' } catch (e) { return e.code } finally { IDBObjectStore.prototype.put = put }
    }, mode)
    assert.equal(code, mode === 'quota' ? 'quota_exceeded' : mode === 'abort' ? 'storage_failed' : 'closed')
    assert.deepEqual(await page.evaluate(() => localRows()), durable); assert.deepEqual(await rows(), old)
    if (mode === 'close') await page.evaluate(async () => { globalThis.session = await c21.openBrowserPersistence(users[0]) })
    if (['keylock','close'].includes(mode)) await page.evaluate(async scope => { await meta.keys.dispose(); globalThis.meta = await c21.metadataFixture(session, scope); globalThis.local = session.localSource.bind(meta.auth, meta.bindings, meta.keys) }, scope)
  }
  cases.push('real IDB request success followed by abort/quota/key lock/session close rolls back Note AND project revision; no early mutation success')
  await page.evaluate(async () => { globalThis.beforeDeletion = await localSnap() })
  assert.equal(await page.evaluate(async () => local.tombstoneNote(scopeA, (await localSnap()).token, 'a-note', localAt)), 5)
  const deleted = await page.evaluate(() => localRead())
  assert.equal(deleted.notes[0].state, 'tombstone'); assert.equal(deleted.notes[0].revision, 2); assert.equal('title' in deleted.notes[0].note, false)
  assert.deepEqual(deleted.notes.filter(n => n.state === 'live').map(n => n.note.id), ['z-note'])
  await expectCode(page, 'local.tombstoneNote(scopeA, beforeDeletion.token, "a-note", localAt)', 'stale_source')
  await expectCode(page, 'local.createNote(scopeA, (await localSnap()).token, localNote("a-note"))', 'conflicting_record')
  cases.push('minimal encrypted tombstone retains deletion membership/identity; initial live set excludes never-cloud-visible deletion; no invented delete event')
  await page.evaluate(async () => { globalThis.foreignProject = { ...localProject, id: 'foreign-local' }; await local.initializeProject(scopeA, { project: foreignProject, notes: [{ state: 'live', note: localNote('foreign-note',foreignProject.id) }] }) })
  const beforeRetry = await page.evaluate(() => localRows())
  assert.equal(await page.evaluate(() => local.initializeProject(scopeA, { project: foreignProject, notes: [{ state: 'live', note: localNote('foreign-note',foreignProject.id) }] })), 1)
  assert.deepEqual(await page.evaluate(() => localRows()), beforeRetry)
  await expectCode(page, 'local.initializeProject(scopeA, {project: foreignProject, notes: []})', 'conflicting_record')
  await expectCode(page, 'local.createNote(scopeA, (await local.readSnapshot(scopeA, foreignProject.id)).token, localNote("z-note",foreignProject.id))', 'conflicting_record')
  assert.deepEqual((await page.evaluate(() => localRead())).notes.map(n => n.note.id), ['a-note','z-note'])
  cases.push('explicit complete initialization retry is byte-stable; partial replacement and cross-project duplicate Note IDs rejected; snapshot isolates projects')
  for (const change of [{ stage_id: 'stage' }, { source_type: 'mindmap', source_map_id: 'map', source_node_id: 'node' }, { content_format: 'plain' }]) {
    const code = await page.evaluate(async change => { try { await local.createNote(scopeA, (await localSnap()).token, { ...localNote('ineligible'), ...change }); return 'unexpected_success' } catch (e) { return e.code } }, change)
    assert.equal(['unsupported_local_source','invalid_local_source'].includes(code), true)
  }
  cases.push('stage-linked, map-derived and plain non-Legacy Notes reject without stripping native fields or importing other families')
  await page.evaluate(async () => { await local.createProject(scopeA, { ...localProject, id: 'deleted-local' }); const snapshot = await local.readSnapshot(scopeA, 'deleted-local'); await local.deleteProject(scopeA, snapshot.token, localAt) })
  await expectCode(page, 'local.readSnapshot(scopeA, "deleted-local")', 'deleted_local_source')
  cases.push('deleted local project retains encrypted evidence and fails source snapshot/bootstrap eligibility')
  const missingMember = await page.evaluate(async () => {
    const db = await new Promise((resolve, reject) => { const r = indexedDB.open(c21.WEB_DATABASE_NAME); r.onsuccess = () => resolve(r.result); r.onerror = reject })
    let saved
    try {
      await c21.runBrowserTransaction(db, ['localNotes'], 'readwrite', (tx, result) => { const store = tx.objectStore('localNotes'), r = store.get([scopeA.accountId,localProject.id,'z-note']); r.onsuccess = () => { saved = r.result; store.delete([scopeA.accountId,localProject.id,'z-note']); result(undefined) } })
      try { await localRead(); return 'unexpected_success' } catch (e) { return e.code }
    } finally { if (saved) await c21.runBrowserTransaction(db, ['localNotes'], 'readwrite', (tx, result) => { tx.objectStore('localNotes').add(saved); result(undefined) }); db.close() }
  })
  assert.equal(missingMember, 'corrupt_record')
  cases.push('encrypted complete-membership manifest rejects a missing native Note row; no partial snapshot or absent-row tombstone manufacture')
  const serialized = JSON.stringify(await page.evaluate(() => localRows()))
  for (const marker of ['PRIVATE_','UPDATED_PRIVATE','ROLLBACK_PRIVATE','fixture-access','fixture-refresh','disposable-fixture-passphrase']) assert.equal(serialized.includes(marker), false)
  assert.deepEqual(await rows(), old)
  cases.push('durable IDB contains no project/title/body/checklist plaintext, AMK/passphrase or tokens; outbox/bindings/ACK/proven all unchanged')
  const finalRows = await page.evaluate(() => localRows()), finalDecoded = await page.evaluate(() => localRead())
  // Recreate only harness globals, never production data, across renderer/profile restart.
  const bindAgain = async () => page.evaluate(async ({ scope, users, saved }) => {
    globalThis.users = users; globalThis.scopeA = scope; globalThis.localProject = saved.localProject; globalThis.localAt = saved.localAt
    globalThis.session = await c21.openBrowserPersistence(users[0]); globalThis.meta = await c21.metadataFixture(session, scope); globalThis.local = session.localSource.bind(meta.auth, meta.bindings, meta.keys)
    globalThis.localRows = async () => ({ projects: await nativeRows('localProjects'), notes: await nativeRows('localNotes') })
    globalThis.localRead = async () => local.withDecryptedSnapshot(scopeA, (await local.readSnapshot(scopeA, localProject.id)).token, async data => structuredClone(data))
  }, { scope, users, saved: savedGlobals })
  await page.reload(); await bindAgain(); assert.deepEqual(await page.evaluate(() => localRows()), finalRows); assert.deepEqual(await page.evaluate(() => localRead()), finalDecoded)
  page = await reopenProfile(); await bindAgain(); assert.deepEqual(await page.evaluate(() => localRows()), finalRows); assert.deepEqual(await page.evaluate(() => localRead()), finalDecoded)
  cases.push('local canonical all-field payloads, tombstones and source revision survive renderer reload and full Chromium disk-profile reopen exactly')
  let competing = await tab(); await expectCode(competing, 'c21.openBrowserPersistence(users[0])', 'writer_busy'); await page.close(); page = competing; await bindAgain()
  assert.deepEqual(await page.evaluate(() => localRows()), finalRows)
  cases.push('real Web Locks excludes second tab and transfers intact local source after writer renderer termination')
  await page.evaluate(async () => { globalThis.staleLocal = local; globalThis.staleToken = (await local.readSnapshot(scopeA, localProject.id)).token; await meta.auth.logout(); await session.resetForLogout() })
  await expectCode(page, 'staleLocal.assertSnapshot(scopeA, staleToken)', 'closed')
  await bindAgain()
  for (const field of ['accountId','canonicalUserId','deviceId']) {
    const code = await page.evaluate(async ({ scope, field, otherScope }) => { try { await local.readSnapshot({ ...scope, [field]: otherScope[field] }, localProject.id); return 'unexpected_success' } catch (e) { return e.code } }, { scope, field, otherScope })
    assert.equal(code, 'account_mismatch', field)
  }
  await page.evaluate(async ({ users, otherScope }) => { await meta.keys.dispose(); await session.close(); globalThis.session = await c21.openBrowserPersistence(users[1]); globalThis.meta = await c21.metadataFixture(session, otherScope); globalThis.local = session.localSource.bind(meta.auth, meta.bindings, meta.keys) }, { users, otherScope })
  const hidden = await page.evaluate(async scope => { try { await local.readSnapshot(scope, localProject.id); return 'unexpected_success' } catch (e) { return e.code } }, otherScope)
  assert.equal(hidden, 'missing_local_source')
  await page.evaluate(async () => { await meta.keys.dispose(); await session.close() }); await bindAgain()
  assert.deepEqual(await page.evaluate(() => localRows()), finalRows); assert.deepEqual(await rows(), old)
  cases.push('auth logout/revocation stale proof and wrong account/user/device fail closed; another account cannot read source and original data remains intact')
  return page
}
