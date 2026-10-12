import type { V3Descriptor } from '@/api/encryptedSyncV3'
// @vitest-environment node
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import { sealProjectMetadataEvent, type ProjectMetadataEvent } from '@/cloud/projectMetadataCodec'
import { encodeBase64Url } from '@/api/base64url'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { BrowserImportedMetadataApply } from './importedMetadataApply'
import { validateBrowserMetadataHead, validateBrowserMetadataProof, type BrowserMetadataProof } from './metadataApplyRecords'
import type { BrowserSyncTransaction, BrowserRetainedEncryptedHistory } from './syncDurability'
const scope = { canonicalUserId: '11111111-1111-4111-8111-111111111111', accountId: '22222222-2222-4222-8222-222222222222', deviceId: '33333333-3333-4333-8333-333333333333' }
const peer = '44444444-4444-4444-8444-444444444444', boot = '55555555-5555-4555-8555-555555555555', id = '66666666-6666-4666-8666-666666666666'
const event = (): ProjectMetadataEvent => ({ version: 1, header: { account_id: scope.canonicalUserId, bootstrap_id: boot, device_id: peer, entity_id: 'p', event_id: id, generation: 1, operation: 'create', parent_event_ids: [], project_id: 'p', revision: 1, updated_at: '2026-10-12T00:00:00.000000Z' }, metadata: { name: 'PRIVATE_METADATA_SENTINEL', goal: null, infinite: true, unit: 'symbols', deadline: null, status: 'active', personal_goal: 1, auto_freeze: false, streak_enabled: false, work_method: 'manual', stages_enabled: false, combine_stage_mindmaps: false }, deleted_at: null })
const reference = () => ({ event_id: id, device_id: peer, server_sequence: 1, project_id: 'p', entity_id: 'p', entity_type: 'project_metadata' as const, operation: 'upsert' as const, revision: 1, updated_at: event().header.updated_at, deleted_at: null })
const proof = (): BrowserMetadataProof => ({ record_version: 1, protocol_version: 3, metadata_codec_version: 1, owner_kind: 'project_metadata', account_id: scope.accountId, project_id: 'p', bootstrap_id: boot, event_id: id, source_device_id: peer, server_sequence: 1, operation: 'create', revision: 1, generation: 1, parent_event_ids: [], wire_digest: '0'.repeat(64), reference: reference() })
const head = () => ({ record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, owner_kind: 'project_metadata', owner_id: 'p', bootstrap_id: boot, tip_event_ids: [id], history: [proof()] })
let amk: AccountMasterKey
beforeAll(async () => { amk = await generateAccountMasterKey(); vi.stubGlobal('IDBKeyRange', { bound: (...keys: unknown[]) => keys }) })
afterAll(() => vi.unstubAllGlobals())
async function setup(changeEvent?: (e: ProjectMetadataEvent) => void) {
  const e = event(); changeEvent?.(e)
  const sealed = await sealProjectMetadataEvent(amk, e)
  const wire = { event: reference(), object: { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(sealed.nonce), ciphertext: encodeBase64Url(sealed.ciphertext) } }
  const row = { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, event_id: id, server_sequence: 1, protocol_version: 3, state: 'received', wire_item: JSON.stringify(wire) }
  const auth = new NormalUserAuthRuntime({ login: async () => ({ access_token: 'test-token', refresh_token: 'test-refresh', access_expires_in: 60 }), logout: async () => {}, refresh: vi.fn(), me: async () => ({ id: scope.canonicalUserId, username: 'fixture', email: 'fixture@example.test', email_verified: true, role: 'user', status: 'active', created_at: e.header.updated_at }) })
  await auth.login('fixture', 'fixture')
  const context = auth.requireContext(), bindings = { ensureForCurrentUser: async () => ({ context }) }
  let current = true
  const copies: Uint8Array[] = []
  const lease = { localAccountId: scope.accountId, canonicalUserId: scope.canonicalUserId, authEpoch: context.authEpoch, isCurrent: () => current,
    use: async <T>(action: (key: AccountMasterKey) => Promise<T>) => { const copy = Uint8Array.from(amk) as AccountMasterKey; copies.push(copy); try { return await action(copy) } finally { copy.fill(0) } } }
  const db = { binding: { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, project_id: 'p', bootstrap_id: boot, mode: 'import_remote', phase: 'captured', remote_state: 'active', initial_event_count: 0, initial_local_ordinal_hi: 0, remote_high_water: 0, initial_max_server_sequence: null, blocked_reason: null } as unknown,
    head: undefined as unknown, inbox: [row] as unknown[], outbox: [] as unknown[], receipts: [] as unknown[], cursor: { record_version: 1, account_id: scope.accountId, device_id: scope.deviceId, pull_cursor: 100, next_local_ordinal: 1, ack_cursor: 0, proven_prefix: 0 } }
  // Scheduling contract driver only; real transaction atomicity is checked in Chromium.
  const transaction: BrowserSyncTransaction = (_scope, _stores, _mode, schedule) => new Promise((resolve, reject) => {
    const requests: Array<{ result: unknown; onsuccess: (() => void) | null }> = []
    const read = (value: unknown) => { const request = { result: structuredClone(value), onsuccess: null as (() => void) | null }; requests.push(request); return request }
    let value: unknown, error: unknown
    const pending = structuredClone(db)
    const find = (key: unknown[]) => pending.inbox.find(value => (value as { event_id: string }).event_id === key[1])
    const store = (name: string) => ({
      get: () => read(name === 'projectBindings' ? pending.binding : name === 'ownerHeads' ? pending.head : name === 'cursors' ? pending.cursor : undefined),
      getAll: () => read(name === 'outbox' ? pending.outbox : pending.receipts),
      index: () => ({ get: (key: unknown[]) => read(find(key)) }),
      put: (row: unknown) => {
        if (name === 'ownerHeads') pending.head = structuredClone(row)
        else { const index = pending.inbox.findIndex(value => (value as { event_id: string }).event_id === (row as { event_id: string }).event_id); pending.inbox[index] = structuredClone(row) }
        return read(undefined)
      },
    })
    schedule({ objectStore: store } as unknown as IDBTransaction, result => { value = result }, failure => { error = failure })
    for (let index = 0; index < requests.length && !error; index++) requests[index]!.onsuccess?.()
    if (error) reject(error)
    else { Object.assign(db, pending); resolve(value as never) }
  })
  const history = { readRetainedHistory: vi.fn(async (_scope, references) => references.map((reference: { event_id: string }) => {
    const incoming = db.inbox.find(value => (value as { event_id: string }).event_id === reference.event_id)
    if (!incoming) throw new Error('fixture_missing_history')
    return { reference, inbox: structuredClone(incoming), outbox: null, receipt: null }
  }) as BrowserRetainedEncryptedHistory[]) }
  const runtime = new BrowserImportedMetadataApply(transaction, history as never)
  const prepare = (r: V3Descriptor = reference()) => runtime.prepareVerified(scope, r, auth, bindings as never, { leaseForAccount: () => lease } as never)
  const add = async (operation: 'update' | 'delete' | 'create', parents: string[], revision: number, generation: number, eventId = peer) => {
    const candidate = event(); candidate.header = { ...candidate.header, event_id: eventId, operation, parent_event_ids: parents, revision, generation }
    if (operation === 'delete') { candidate.metadata = null; candidate.deleted_at = candidate.header.updated_at }
    const envelope = await sealProjectMetadataEvent(amk, candidate)
    const descriptor = { ...reference(), event_id: eventId, revision, server_sequence: db.inbox.length + 1, operation: operation === 'delete' ? 'delete' as const : 'upsert' as const, deleted_at: candidate.deleted_at }
    db.inbox.push({ ...row, event_id: eventId, server_sequence: descriptor.server_sequence, wire_item: JSON.stringify({ event: descriptor, object: { crypto_version: 1, aad_version: 1, nonce: encodeBase64Url(envelope.nonce), ciphertext: encodeBase64Url(envelope.ciphertext) } }) })
    return descriptor
  }
  return { runtime, auth, lease, history, wire, row, prepare, add, db, lock: () => { current = false }, copies }
}
describe('imported Metadata verification and opaque authority contract', () => {
  it('commits only authenticated native genesis and exact token replay', async () => {
    const h = await setup(), token = await h.prepare()
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, token)).resolves.toBe('applied')
    const saved = structuredClone(h.db)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, token)).resolves.toBe('already_applied')
    expect(h.db).toEqual(saved)
  })
  it('compares complete authority CAS before applying a stale verified genesis', async () => {
    const h = await setup(), token = await h.prepare(); h.db.head = head()
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, token)).rejects.toMatchObject({ code: 'stale_authority' })
    expect((h.db.inbox[0] as { state: string }).state).toBe('received')
  })
  it('requires exact imported lineage and full expected-old registration snapshot', async () => {
    const h = await setup(), token = await h.prepare()
    h.db.binding = { ...(h.db.binding as object), remote_high_water: 1 }
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, token)).rejects.toMatchObject({ code: 'stale_lineage' })
    h.db.binding = { ...(h.db.binding as object), mode: 'upload_existing', phase: 'registered' }
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, token)).rejects.toMatchObject({ code: 'ineligible_lineage' })
  })
  it('applies causal next event and tombstone while retaining complete encrypted ancestry', async () => {
    const h = await setup(); await h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare())
    const next = await h.add('update', [id], 2, 3)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(next))).resolves.toBe('applied')
    const tombstone = await h.add('delete', [peer], 3, 4, boot)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(tombstone))).resolves.toBe('applied')
    const before = structuredClone(h.db)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare())).resolves.toBe('already_applied')
    expect(h.db).toEqual(before)
    expect(JSON.stringify(h.db.head)).not.toContain('PRIVATE_METADATA_SENTINEL')
  })
  it('leaves concurrent genesis and stale-parent branches received', async () => {
    const h = await setup(); await h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare())
    const concurrent = await h.add('create', [], 1, 1)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(concurrent))).rejects.toMatchObject({ code: 'metadata_conflict' })
    const next = await h.add('update', [id], 2, 2, boot)
    await h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(next))
    const stale = await h.add('update', [id], 2, 3, scope.canonicalUserId)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(stale))).rejects.toMatchObject({ code: 'metadata_conflict' })
  })
  it.each([[2,1],[3,2]])('rejects revision/generation pair %j/%j incompatible with verified parent', async (revision, generation) => {
    const h = await setup(); await h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare())
    const next = await h.add('update', [id], revision, generation)
    const before = structuredClone(h.db)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(next))).rejects.toMatchObject({ code: 'metadata_rejected' })
    expect(h.db).toEqual(before)
  })
  it('cannot manufacture first authority from a non-genesis update', async () => {
    const h = await setup(), next = await h.add('update', [id], 2, 2)
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(next))).rejects.toMatchObject({ code: 'missing_history' })
    expect(h.db.head).toBeUndefined()
  })
  it('refuses an authenticated own source even without conflicting descriptor', async () => {
    const h = await setup(e => { e.header.device_id = scope.deviceId })
    const own = { ...reference(), device_id: scope.deviceId }
    h.db.inbox[0] = { ...h.row, wire_item: JSON.stringify({ ...h.wire, event: own }) }
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare(own))).rejects.toMatchObject({ code: 'self_echo_unavailable' })
  })
  it('mints an opaque plan from actual crypto and stores no decoded payload', async () => {
    const h = await setup(), plan = await h.prepare()
    expect(Object.keys(plan)).toEqual([]); expect(Object.isFrozen(plan)).toBe(true)
    expect(JSON.stringify(plan)).not.toContain('PRIVATE_METADATA_SENTINEL')
    expect(h.copies.every(copy => copy.every(byte => byte === 0))).toBe(true)
  })
  it('rejects a forged clean plan before any write scheduling', async () => {
    const h = await setup()
    expect(() => h.runtime.commitVerifiedImportedMetadataApply(scope, { outcome: 'clean' } as never)).toThrowError(expect.objectContaining({ code: 'metadata_rejected' }))
  })
  it('invalidates prepared proof at logout and rejects stale handlers', async () => {
    const h = await setup(), token = await h.prepare(); await h.auth.logout()
    expect(() => h.runtime.commitVerifiedImportedMetadataApply(scope, token)).toThrowError(expect.objectContaining({ code: 'closed' }))
  })
  it('invalidates proof at key lock', async () => {
    const h = await setup(), token = await h.prepare(); h.lock()
    expect(() => h.runtime.commitVerifiedImportedMetadataApply(scope, token)).toThrowError(expect.objectContaining({ code: 'closed' }))
  })
  it('rejects cross-account and device use of an otherwise verified token', async () => {
    const h = await setup(), token = await h.prepare()
    for (const field of ['accountId','deviceId','canonicalUserId']) expect(() => h.runtime.commitVerifiedImportedMetadataApply({ ...scope, [field]: peer }, token)).toThrowError(expect.objectContaining({ code: 'metadata_rejected' }))
  })
  it('refuses stale auth/key epoch and a missing key before decryption', async () => {
    const h = await setup(); h.lease.authEpoch++
    await expect(h.prepare()).rejects.toMatchObject({ code: 'account_mismatch' })
    await expect(h.runtime.prepareVerified(scope, reference(), h.auth, { ensureForCurrentUser: async () => ({ context: h.auth.requireContext() }) } as never, { leaseForAccount: () => null } as never)).rejects.toMatchObject({ code: 'account_mismatch' })
  })
  it('accepts authenticated codec2 null Cover without requiring blob material', async () => {
    const h = await setup(e => { e.version = 2; e.metadata!.cover_reference = null })
    await expect(h.runtime.commitVerifiedImportedMetadataApply(scope, await h.prepare())).resolves.toBe('applied')
    expect((h.db.head as { history: BrowserMetadataProof[] }).history[0]?.metadata_codec_version).toBe(2)
  })
  it('refuses authenticated non-null Cover reference', async () => {
    const h = await setup(e => { e.version = 2; e.metadata!.cover_reference = { version: 1, blob_id: peer, crypto_version: 1, aad_version: 1, mime_type: 'image/jpeg', plaintext_size: 4, key_fingerprint: '0'.repeat(64), envelope_sha256: '1'.repeat(64) } })
    await expect(h.prepare()).rejects.toMatchObject({ code: 'cover_material_unavailable' })
    expect(h.copies[0]?.every(byte => byte === 0)).toBe(true)
  })
  it.each(['event_id','device_id','entity_id','project_id','revision','updated_at','operation','deleted_at','entity_type'])('does not accept changed descriptor %s as verification', async field => {
    const h = await setup(), r = { ...reference(), [field]: field === 'revision' ? 2 : field === 'deleted_at' ? reference().updated_at : 'changed' }
    h.history.readRetainedHistory.mockResolvedValueOnce([{ reference: r, inbox: h.row, outbox: null, receipt: null }] as never)
    await expect(h.prepare(r as never)).rejects.toMatchObject({ name: 'BrowserPersistenceError' })
  })
  it('authenticates ciphertext and clears lease buffers on failure', async () => {
    const h = await setup(); h.wire.object.ciphertext = encodeBase64Url(new Uint8Array(64).fill(3)); h.row.wire_item = JSON.stringify(h.wire); h.db.inbox[0] = h.row
    await expect(h.prepare()).rejects.toMatchObject({ code: 'metadata_rejected' })
    expect(h.copies[0]?.every(byte => byte === 0)).toBe(true)
  })
  it('rejects a changed AAD version and nonce through frozen crypto', async () => {
    const h = await setup(); h.wire.object.aad_version = 2; h.row.wire_item = JSON.stringify(h.wire); h.db.inbox[0] = h.row
    await expect(h.prepare()).rejects.toMatchObject({ code: 'metadata_rejected' })
  })
  it('retains missing-history rejection instead of inventing empty ancestry', async () => {
    const h = await setup(); h.history.readRetainedHistory.mockRejectedValueOnce(new Error('fixture_missing_history'))
    await expect(h.prepare()).rejects.toThrow('fixture_missing_history')
  })
  it.each([{ record_version: 99 }, { owner_kind: 'note' }, { account_id: peer }, { source_device_id: scope.deviceId }, { revision: 2 }, { generation: 0 }, { server_sequence: 2 }, { parent_event_ids: [id] }, { metadata: { name: 'PRIVATE' } }])('rejects malformed applied proof %j', changed => {
    expect(() => validateBrowserMetadataProof({ ...proof(), ...changed }, scope)).toThrowError(expect.objectContaining({ code: 'corrupt_record' }))
  })
  it('validates complete causal tips and retains all ancestry without latest-sequence selection', () => {
    const h = head(), next = { ...proof(), event_id: peer, source_device_id: peer, operation: 'update' as const, revision: 2, generation: 3, parent_event_ids: [id], reference: { ...reference(), event_id: peer, revision: 2, server_sequence: 2 }, server_sequence: 2 }
    h.history = [next, proof()].sort((a, b) => a.event_id.localeCompare(b.event_id)); h.tip_event_ids = [peer]
    expect(validateBrowserMetadataHead(h, scope).history).toHaveLength(2)
    expect(() => validateBrowserMetadataHead({ ...h, tip_event_ids: [id] }, scope)).toThrow()
  })
  it('rejects ancestry holes, stale generation and duplicate parent/tip ordering', () => {
    const h = head(); expect(() => validateBrowserMetadataHead({ ...h, history: [] }, scope)).toThrow()
    expect(() => validateBrowserMetadataHead({ ...h, tip_event_ids: [id, id] }, scope)).toThrow()
    expect(() => validateBrowserMetadataHead({ ...h, history: [proof(), proof()] }, scope)).toThrow()
  })
  it('preserves multi-tip genesis authority without collapsing a branch', () => {
    const second = { ...proof(), event_id: peer, reference: { ...reference(), event_id: peer, server_sequence: 2 }, server_sequence: 2 }
    const h = { ...head(), history: [second, proof()].sort((a, b) => a.event_id.localeCompare(b.event_id)), tip_event_ids: [peer, id].sort() }
    expect(validateBrowserMetadataHead(h, scope).tip_event_ids).toEqual([peer, id].sort())
  })
})
