import assert from 'node:assert/strict'
/** Real IDB identity reuse + explicit HTTP; no capabilities/ACK claim. */
export async function acceptDeviceRegistration({ page, scope: originalScope, cases, reopenProfile, requests }) {
  const user = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
  const stores = ['identities','accountBindings','outbox','inbox','cursors','receipts','projectBindings','ownerHeads','localProjects','localNotes','legacyNoteHistory','legacyNoteIntents']
  await page.evaluate(async () => { await meta.keys.dispose(); await session.close() })
  const scope = await page.evaluate(async user => {
    globalThis.session = await c21.openBrowserPersistence(user)
    const id = await session.read(user)
    globalThis.registrationScope = { canonicalUserId: user, accountId: id.local_account_id, deviceId: id.device_id }
    globalThis.registration = await c21.deviceFixture(session, user)
    return registrationScope
  }, user)
  const snapshot = () => page.evaluate(async names => Object.fromEntries(await Promise.all(names.map(async n => [n, await nativeRows(n)]))), stores)
  const before = await snapshot(), start = requests.length
  assert.deepEqual(await page.evaluate(scope => session.sync.readCheckpoint(scope), scope), { pull_cursor: 9, ack_cursor: 0, proven_prefix: 7, next_local_ordinal: 1 })
  let behavior = 'normal'
  // Server registration semantics: insert-or-reuse; existing capabilities and ACK survive repeat.
  const server = { device: scope.deviceId, ack: 19, compression: true, reader: 3 }
  const serverBefore = structuredClone(server)
  async function route() {
    await page.route('**/api/v1/sync/devices/*', async request => {
      assert.equal(request.request().method(), 'PUT')
      assert.equal(request.request().headers().authorization, 'Bearer fixture-device-access')
      assert.equal(request.request().postData(), null)
      assert.equal(decodeURIComponent(new URL(request.request().url()).pathname.split('/').at(-1)), scope.deviceId)
      if (behavior === 'lost') { await request.abort(); return }
      const body = { protocol_version: 1, device_id: server.device, last_ack_cursor: server.ack }
      if (behavior === 'device') body.device_id = 'ffffffff-ffff-4fff-8fff-ffffffffffff'
      if (behavior === 'mode') body.writer_transport_version = 3
      if (behavior === 'capability') body.compression_id1 = true
      if (behavior === 'cursor') body.last_ack_cursor = -1
      if (behavior === 'logout') await page.evaluate(() => registration.auth.logout())
      await request.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
    })
  }
  await route()
  const invoke = () => page.evaluate(() => registration.runtime.registerOnce(registrationScope))
  const reject = async () => assert.equal(await page.evaluate(async () => { try { await registration.runtime.registerOnce(registrationScope); return false } catch { return true } }), true)
  const expected = { deviceId: scope.deviceId, serverAckCursor: 19, ready: false }
  assert.deepEqual(await invoke(), expected); assert.deepEqual(await invoke(), expected)
  assert.deepEqual(server, serverBefore); assert.deepEqual(await snapshot(), before)
  cases.push('explicit authenticated identity-only registration and exact repeat reuse durable UUID; no capabilities, mode, ACK or store writes')
  for (behavior of ['device','mode','capability','cursor']) { await reject(); assert.deepEqual(await snapshot(), before) }
  cases.push('wrong device, unexpected mode/capability and malformed ACK metadata rejected; full durable state unchanged')
  behavior = 'lost'; await reject(); behavior = 'normal'; assert.deepEqual(await invoke(), expected)
  assert.deepEqual(await snapshot(), before)
  cases.push('lost registration response retries same UUID without ACK reset or capability downgrade')
  behavior = 'logout'; await reject(); behavior = 'normal'
  const count = requests.length; await reject(); assert.equal(requests.length, count)
  await page.evaluate(async user => { globalThis.registration = await c21.deviceFixture(session, user) }, user)
  const wrong = await page.evaluate(async scope => {
    const rejected = []
    for (const key of ['canonicalUserId','accountId','deviceId']) {
      try { await registration.runtime.registerOnce({ ...scope, [key]: 'ffffffff-ffff-4fff-8fff-ffffffffffff' }); rejected.push(false) } catch { rejected.push(true) }
    }
    return rejected
  }, scope)
  assert.deepEqual(wrong, [true,true,true]); assert.equal(requests.length, count)
  cases.push('stale auth, wrong user/account/device fail closed before network; logout during response cannot create registration proof')
  await page.reload()
  await page.evaluate(async scope => { globalThis.session = await c21.openBrowserPersistence(scope.canonicalUserId); globalThis.registrationScope = scope; globalThis.registration = await c21.deviceFixture(session, scope.canonicalUserId) }, scope)
  await route(); assert.deepEqual(await invoke(), expected); assert.deepEqual(await snapshot(), before)
  cases.push('reload uses exact durable registration UUID; proven7/ACK0/pull9 and unsupported-family barrier survive')
  page = await reopenProfile()
  await page.evaluate(async scope => { globalThis.session = await c21.openBrowserPersistence(scope.canonicalUserId); globalThis.registrationScope = scope; globalThis.registration = await c21.deviceFixture(session, scope.canonicalUserId) }, scope)
  await route(); assert.deepEqual(await invoke(), expected); assert.deepEqual(await snapshot(), before)
  cases.push('disk-profile reopen repeats exact device registration; all twelve stores byte-equivalent, ready=false, ACK remains blocked')
  assert.equal(requests.length - start, 11)
  await page.unroute('**/api/v1/sync/devices/*')
  await page.evaluate(async scope => { await session.close(); globalThis.session = await c21.openBrowserPersistence(scope.canonicalUserId); globalThis.meta = await c21.metadataFixture(session, scope) }, originalScope)
  return page
}
