// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StageStructuralRuntime } from './stageStructuralRuntime'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { encryptedSyncV2Api } from '@/api/encryptedSyncV2'
import { generateAccountMasterKey, encryptObjectBytes, type AccountMasterKey } from '@/crypto'
import { frameStructuralEvent, sealStructuralEvent, type StructuralEvent } from './stageCodec'
import fixture from './__fixtures__/stageCodecV1.json'
import type { StructuralReceived, StructuralPending, StructuralView } from '@/infrastructure/sqlite/stageStructuralRepository'
const event = () => structuredClone(fixture.event) as StructuralEvent
async function setup() {
  const e = event(), user = e.header.account_id, device = e.header.device_id
  const auth = new NormalUserAuthRuntime({ login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(), me: vi.fn().mockResolvedValue({ id: user, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: e.header.updated_at }) })
  await auth.login('u', 'p'); const context = auth.requireContext(), amk = await generateAccountMasterKey()
  const bindings = { ensureForCurrentUser: vi.fn(async () => ({ context })) }
  const identity = { read: vi.fn(async () => ({ local_account_id: 'local', device_id: device })) }
  const keys = { leaseForAccount: vi.fn(() => ({ canonicalUserId: user, authEpoch: context.authEpoch, isCurrent: () => true,
    use: (action: (key: AccountMasterKey) => Promise<unknown>) => action(amk) })) }
  const native = { authority: vi.fn(async () => ({ state: 'structural_local', entities: [], order: [], blockers: [], migration_id: null }) as StructuralView),
    begin: vi.fn(async () => ({ state: 'publication_pending' }) as StructuralView), decide: vi.fn(async () => e.header.event_id),
    pending: vi.fn<() => Promise<StructuralPending[]>>(async () => []), seal: vi.fn(async () => {}), receipt: vi.fn(async () => {}),
    received: vi.fn<() => Promise<StructuralReceived[]>>(async () => []), apply: vi.fn(async () => 'applied'), block: vi.fn(async () => {}), retry: vi.fn(async () => {}) }
  const api = { pushMetadata: vi.fn(async () => ({ results: [{ event_id: e.header.event_id, server_sequence: 2, duplicate: true }] })) }
  vi.spyOn(encryptedSyncV2Api, 'capabilities').mockResolvedValue({ supported_transport_version: 2, writer_transport_version: 3, cutover_epoch: 2 } as never)
  const runtime = new StageStructuralRuntime(auth, bindings as never, identity as never, keys as never, native as never, api as never)
  return { runtime, native, api, e, amk, device, context }
}
function received(e: StructuralEvent, envelope: { nonce: Uint8Array; ciphertext: Uint8Array }): StructuralReceived {
  const h = e.header
  return { event_id: h.event_id, project_id: h.project_id, entity_id: h.entity_id, entity_type: h.entity_type, source_device_id: h.device_id,
    revision: h.revision, updated_at: h.updated_at, operation: 'upsert', deleted_at: null, server_sequence: 2,
    crypto_version: 1, aad_version: 1, nonce: Array.from(envelope.nonce), ciphertext: Array.from(envelope.ciphertext) }
}
afterEach(() => vi.restoreAllMocks())
describe('production structural reader and explicit runtime', () => {
  it('read/apply/retry cannot capture or initiate migration', async () => {
    const h = await setup(); await h.runtime.view('local', h.device, h.e.header.project_id); await h.runtime.applyOnce('local', h.device)
    expect(h.native.begin).not.toHaveBeenCalled(); expect(h.native.decide).not.toHaveBeenCalled()
    await h.runtime.beginStructure('local', h.device, h.e.header.project_id); expect(h.native.begin).toHaveBeenCalledTimes(1)
  })
  it('seals once and uploads exact durable ciphertext after a lost response', async () => {
    const h = await setup(); h.native.pending.mockResolvedValue([{ event: h.e, nonce: null, ciphertext: null }])
    await h.runtime.sealOnce('local', h.device)
    const seal = h.native.seal.mock.calls[0] as unknown as [unknown, string, Uint8Array, Uint8Array, Uint8Array]
    h.native.pending.mockResolvedValue([{ event: h.e, nonce: Array.from(seal[3]), ciphertext: Array.from(seal[4]) }])
    h.api.pushMetadata.mockRejectedValueOnce(new Error('lost response'))
    await expect(h.runtime.uploadOnce('local', h.device)).rejects.toThrow('lost response'); expect(h.native.receipt).not.toHaveBeenCalled()
    await h.runtime.uploadOnce('local', h.device)
    expect(h.api.pushMetadata.mock.calls[0]).toEqual(h.api.pushMetadata.mock.calls[1]); expect(h.native.seal).toHaveBeenCalledTimes(1)
  })
  it.each(['stage', 'stage_order'] as const)('authenticates and dispatches %s while preserving dependencies', async type => {
    const h = await setup(); h.e.header.entity_type = type
    if (type === 'stage_order') { h.e.header.entity_id = 'stage_order'; h.e.stage = null; h.e.stage_ids = []; h.e.stage_heads = {} }
    const envelope = await sealStructuralEvent(h.amk, h.e)
    h.native.received.mockResolvedValueOnce([received(h.e, envelope)]); h.native.apply.mockResolvedValue('orphan')
    const result = await h.runtime.applyOnce('local', h.device)
    expect(result.orphans).toBe(1); expect(result.blocked).toEqual([h.e.header.event_id]); expect(h.native.apply).toHaveBeenCalledTimes(1)
    expect(h.native.begin).not.toHaveBeenCalled()
  })
  it.each(['stage', 'stage_order'] as const)('durably blocks unsupported %s frames, wrong scope/pairing and account-object v2', async type => {
    const h = await setup(); h.e.header.entity_type = type
    if (type === 'stage_order') { h.e.header.entity_id = 'stage_order'; h.e.stage = null; h.e.stage_ids = []; h.e.stage_heads = {} }
    const context = { userId: h.e.header.account_id, projectId: h.e.header.project_id, entityId: h.e.header.entity_id, entityType: type }
    const frames = [10, 8, 9].map(offset => { const frame = frameStructuralEvent(h.e); frame[offset] = 255; return frame })
    frames.push(new TextEncoder().encode('{"version":1,"metadata":{}}'))
    for (const frame of frames) {
      const sealed = await encryptObjectBytes(h.amk, context, frame)
      h.native.received.mockResolvedValueOnce([received(h.e, sealed)])
      expect((await h.runtime.applyOnce('local', h.device)).blocked).toEqual([h.e.header.event_id])
    }
    const sealed = await sealStructuralEvent(h.amk, h.e)
    for (const overrides of [{ project_id: 'wrong-project' }, { aad_version: 2 }, { crypto_version: 2 }, { source_device_id: 'other' }]) {
      h.native.received.mockResolvedValueOnce([{ ...received(h.e, sealed), ...overrides }])
      expect((await h.runtime.applyOnce('local', h.device)).blocked).toEqual([h.e.header.event_id])
    }
    expect(h.native.apply).not.toHaveBeenCalled(); expect(h.native.block).toHaveBeenCalledTimes(8); expect(h.native.begin).not.toHaveBeenCalled()
  })
})
