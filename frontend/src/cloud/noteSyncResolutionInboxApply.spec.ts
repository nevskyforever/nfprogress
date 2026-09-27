// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import fixture from './__fixtures__/noteSyncPlaintextV2Resolution.json'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { encryptObjectBytes, generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import type { NoteSyncInboxRepository, ReceivedNoteResolutionInboxItem } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import {
  SQLiteNoteSyncRemoteApplyRepository,
  type NoteSyncResolutionRemoteApplyRepository,
  type VerifiedNoteSyncRemoteApplyCommand,
} from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { encodeNoteSyncResolutionV2, type NoteSyncResolutionV2 } from './noteSyncResolutionV2Codec'
import {
  NoteResolutionInboxApplyError,
  NoteSyncResolutionInboxApplier,
} from './noteSyncResolutionInboxApply'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const REMOTE_DEVICE = '123e4567-e89b-42d3-a456-426614174002'
const TIME = '2026-09-21T00:00:00.000000Z'

function runtime() {
  return new NormalUserAuthRuntime({
    login: vi.fn(async () => ({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 })),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn(async () => ({ id: USER, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: TIME })),
  })
}

function lease(amk: AccountMasterKey, overrides: Partial<AuthoritativeKeyContextLease> = {}): AuthoritativeKeyContextLease {
  return {
    localAccountId: 'local', canonicalUserId: USER, authEpoch: 2, keyContextId: 'context', keyEpoch: 1,
    isCurrent: () => true, use: async operation => operation(amk), ...overrides,
  }
}

function bindings(auth: NormalUserAuthRuntime): AuthoritativeAccountBinding {
  return new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
}

function repository(
  received: ReceivedNoteResolutionInboxItem[] = [],
  listOrphans?: NoteSyncInboxRepository['listOrphanResolutions'],
  listReceivedPage?: NoteSyncInboxRepository['listReceivedPage'],
): NoteSyncInboxRepository {
  return {
    readPullState: vi.fn().mockResolvedValue({ pull_cursor: 10, ack_cursor: 4 }),
    listReceived: vi.fn(async () => received),
    ...(listOrphans ? { listOrphanResolutions: listOrphans } : {}),
    ...(listReceivedPage ? { listReceivedPage } : {}),
    commitInboundPage: vi.fn(),
  }
}

function native(): NoteSyncResolutionRemoteApplyRepository {
  return {
    applyVerifiedResolution: vi.fn().mockResolvedValue('applied'),
    reconcileVerifiedResolutionSelfEcho: vi.fn().mockResolvedValue('reconciled'),
  }
}

async function encryptedFixture(
  amk: AccountMasterKey,
  index = 0,
  sourceDeviceId = REMOTE_DEVICE,
  overrides: Partial<ReceivedNoteResolutionInboxItem> = {},
  bytes?: Uint8Array,
): Promise<ReceivedNoteResolutionInboxItem> {
  const payload = structuredClone(fixture.examples[index]!.plaintext) as NoteSyncResolutionV2
  const plaintext = bytes ?? encodeNoteSyncResolutionV2(payload)
  const envelope = await encryptObjectBytes(amk, {
    userId: USER, projectId: payload.header.project_id, entityId: payload.header.entity_id, entityType: 'note',
  }, plaintext)
  return {
    event_id: payload.header.event_id,
    server_sequence: index + 1,
    source_device_id: sourceDeviceId,
    project_id: payload.header.project_id,
    entity_id: payload.header.entity_id,
    entity_type: 'note',
    operation: 'resolution',
    revision: payload.header.revision,
    updated_at: payload.header.updated_at,
    deleted_at: null,
    envelope,
    ...overrides,
  }
}

function applier(
  auth: NormalUserAuthRuntime,
  amk: AccountMasterKey,
  inbox: NoteSyncInboxRepository,
  nativeApply: NoteSyncResolutionRemoteApplyRepository,
  leaseOverride?: AuthoritativeKeyContextLease | null,
) {
  const keys = { leaseForAccount: vi.fn(() => leaseOverride === undefined ? lease(amk) : leaseOverride) } as unknown as RuntimeKeyContext
  return new NoteSyncResolutionInboxApplier(auth, bindings(auth), keys, inbox, nativeApply)
}

describe('C17 D3B authenticated resolution v2 inbox apply', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('decrypts a real frozen v2 fixture inside the lease, binds metadata and dispatches only to peer apply', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const item = await encryptedFixture(amk)
    let captured: VerifiedNoteSyncRemoteApplyCommand | undefined
    let leaseActive = false
    const activeLease = lease(amk, {
      use: async operation => { leaseActive = true; try { return await operation(amk) } finally { leaseActive = false } },
    })
    const nativeApply = native()
    vi.mocked(nativeApply.applyVerifiedResolution).mockImplementation(async command => {
      expect(leaseActive).toBe(true)
      captured = command
      return 'applied'
    })
    const result = await applier(auth, amk, repository([item]), nativeApply, activeLease).applyReceivedOnce('local', DEVICE)
    expect(result).toEqual([{ event_id: item.event_id, server_sequence: 1, status: 'applied' }])
    expect(nativeApply.reconcileVerifiedResolutionSelfEcho).not.toHaveBeenCalled()
    expect(captured).toMatchObject({ account_id: 'local', canonical_user_id: USER, pulling_device_id: DEVICE,
      event_id: item.event_id, source_device_id: REMOTE_DEVICE, crypto_version: 1, aad_version: 1 })
    expect(captured?.plaintext.every(byte => byte === 0)).toBe(true)
    expect(captured?.nonce.every(byte => byte === 0)).toBe(true)
    expect(captured?.ciphertext.every(byte => byte === 0)).toBe(true)
    expect(item.envelope.ciphertext.every(byte => byte === 0)).toBe(true)
  })

  it('routes own-device resolutions only to self-echo reconciliation and preserves both native statuses', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const items = [await encryptedFixture(amk, 0, DEVICE), await encryptedFixture(amk, 1, DEVICE, { server_sequence: 2 })]
    const nativeApply = native()
    vi.mocked(nativeApply.reconcileVerifiedResolutionSelfEcho).mockResolvedValueOnce('reconciled').mockResolvedValueOnce('already_reconciled')
    const result = await applier(auth, amk, repository(items), nativeApply).applyReceivedOnce('local', DEVICE)
    expect(result.map(value => value.status)).toEqual(['reconciled', 'already_reconciled'])
    expect(nativeApply.applyVerifiedResolution).not.toHaveBeenCalled()
  })

  it('never falls back to the other native path after an IPC failure and clears command buffers', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const peer = await encryptedFixture(amk)
    let captured: VerifiedNoteSyncRemoteApplyCommand | undefined
    const nativeApply = native()
    vi.mocked(nativeApply.applyVerifiedResolution).mockImplementation(async command => { captured = command; throw new Error('IPC unavailable') })
    const result = await applier(auth, amk, repository([peer]), nativeApply).applyReceivedOnce('local', DEVICE)
    expect(result).toEqual([{ event_id: peer.event_id, server_sequence: 1, status: 'error', error_code: 'ipc_failure' }])
    expect(nativeApply.reconcileVerifiedResolutionSelfEcho).not.toHaveBeenCalled()
    expect(captured?.plaintext.every(byte => byte === 0)).toBe(true)
  })

  it('rejects unavailable, stale and mismatched authoritative scope before listing inbox items', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const inbox = repository([]); const nativeApply = native()
    await expect(applier(auth, amk, inbox, nativeApply, null).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'key_unavailable' })
    await expect(applier(auth, amk, inbox, nativeApply, lease(amk, { localAccountId: 'other' })).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'invalid_inbox_scope' })
    await expect(applier(auth, amk, inbox, nativeApply, lease(amk, { canonicalUserId: REMOTE_DEVICE })).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'invalid_inbox_scope' })
    await expect(applier(auth, amk, inbox, nativeApply, lease(amk, { authEpoch: 99 })).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'invalid_inbox_scope' })
    const wrongDevice = repository([])
    vi.mocked(wrongDevice.readPullState).mockRejectedValue(new Error('pulling device mismatch'))
    await expect(applier(auth, amk, wrongDevice, nativeApply).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'invalid_inbox_scope' })
    const stale = lease(amk, { isCurrent: () => false })
    await expect(applier(auth, amk, inbox, nativeApply, stale).applyReceivedOnce('local', DEVICE)).rejects.toMatchObject({ code: 'key_unavailable' })
    expect(nativeApply.applyVerifiedResolution).not.toHaveBeenCalled()
  })

  it('classifies decrypt, canonical-v2 and durable metadata failures without v1 or native fallback', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const tampered = await encryptedFixture(amk); tampered.envelope.ciphertext[0]! ^= 1
    const noncanonicalBytes = new TextEncoder().encode(JSON.stringify(fixture.examples[0]!.plaintext))
    const malformed = await encryptedFixture(amk, 0, REMOTE_DEVICE, { server_sequence: 2 }, noncanonicalBytes)
    const mismatch = await encryptedFixture(amk, 0, REMOTE_DEVICE, { server_sequence: 3, updated_at: TIME })
    const nativeApply = native()
    const result = await applier(auth, amk, repository([tampered, malformed, mismatch]), nativeApply).applyReceivedOnce('local', DEVICE)
    expect(result.map(value => value.error_code)).toEqual(['decrypt_failed', 'invalid_resolution_payload', 'metadata_mismatch'])
    expect(nativeApply.applyVerifiedResolution).not.toHaveBeenCalled()
    expect(nativeApply.reconcileVerifiedResolutionSelfEcho).not.toHaveBeenCalled()
    expect([tampered, malformed, mismatch].every(item => item.envelope.ciphertext.every(byte => byte === 0))).toBe(true)
  })

  it('uses at most two strictly-keyset orphan pages and an unresolved orphan does not block later events', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const first = await encryptedFixture(amk, 0, REMOTE_DEVICE, { server_sequence: 1 })
    const second = await encryptedFixture(amk, 1, REMOTE_DEVICE, { server_sequence: 2 })
    const third = await encryptedFixture(amk, 2, REMOTE_DEVICE, { server_sequence: 3 })
    const listOrphans = vi.fn(async (_account: string, _device: string, _user: string, _limit: number, after: number) => after === 0 ? [first, second] : [third])
    const nativeApply = native()
    vi.mocked(nativeApply.applyVerifiedResolution).mockResolvedValueOnce('orphan').mockResolvedValueOnce('applied').mockResolvedValueOnce('already_applied')
    const result = await applier(auth, amk, repository([], listOrphans), nativeApply).retryOrphansOnce('local', DEVICE, 2)
    expect(result).toEqual([
      { event_id: first.event_id, server_sequence: 1, status: 'orphan' },
      { event_id: second.event_id, server_sequence: 2, status: 'applied' },
      { event_id: third.event_id, server_sequence: 3, status: 'already_applied' },
    ])
    expect(listOrphans.mock.calls.map(call => call[4])).toEqual([0, 2])
    expect(nativeApply.applyVerifiedResolution).toHaveBeenCalledTimes(3)
  })

  it('uses the resolution-only page reader and carries orphan progress across bounded passes', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const received = await encryptedFixture(amk, 0, REMOTE_DEVICE, { server_sequence: 6 })
    const receivedPage = vi.fn(async () => [received])
    const first = await encryptedFixture(amk, 1, REMOTE_DEVICE, { server_sequence: 11 })
    const second = await encryptedFixture(amk, 2, REMOTE_DEVICE, { server_sequence: 12 })
    const listOrphans = vi.fn(async (_account: string, _device: string, _user: string, _limit: number, after: number) => after === 10 ? [first] : [second])
    const value = applier(
      auth,
      amk,
      repository([], listOrphans, receivedPage as unknown as NonNullable<NoteSyncInboxRepository['listReceivedPage']>),
      native(),
    )

    await expect(value.applyReceivedPage('local', DEVICE, 4, 5)).resolves.toMatchObject({
      listed: 1, lastServerSequence: 6, errorCount: 0,
      results: [{ server_sequence: 6, status: 'applied' }],
    })
    expect(receivedPage).toHaveBeenCalledWith('local', DEVICE, USER, 'resolution', 4, 5)

    const orphan = await value.retryOrphansFrom('local', DEVICE, 2, 10)
    expect(orphan).toMatchObject({ listed: 1, lastServerSequence: 11, reachedEnd: true, errorCount: 0 })
    expect(listOrphans).toHaveBeenCalledWith('local', DEVICE, USER, 2, 10)
  })

  it('reports an unavailable orphan reader and rejects invalid native statuses without claiming success', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    await expect(applier(auth, amk, repository(), native()).retryOrphansOnce('local', DEVICE)).rejects.toEqual(expect.objectContaining({ code: 'orphan_retry_unavailable' }))
    const pending = await encryptedFixture(amk)
    const pendingNative = native()
    vi.mocked(pendingNative.applyVerifiedResolution).mockResolvedValue('self_echo_pending')
    await expect(applier(auth, amk, repository([pending]), pendingNative).applyReceivedOnce('local', DEVICE)).resolves.toMatchObject([{ status: 'self_echo_pending' }])
    const item = await encryptedFixture(amk)
    const nativeApply = native()
    vi.mocked(nativeApply.applyVerifiedResolution).mockResolvedValue('reconciled' as never)
    const result = await applier(auth, amk, repository([item]), nativeApply).applyReceivedOnce('local', DEVICE)
    expect(result).toEqual([{ event_id: item.event_id, server_sequence: 1, status: 'error', error_code: 'invalid_native_status' }])
    await expect(applier(auth, amk, repository(), native()).retryOrphansOnce('local', DEVICE, 33)).rejects.toBeInstanceOf(RangeError)
  })

  it('uses the exact registered native IPC command names', async () => {
    invoke.mockResolvedValueOnce('applied').mockResolvedValueOnce('reconciled')
    const repository = new SQLiteNoteSyncRemoteApplyRepository()
    const command = { account_id: 'local', canonical_user_id: USER, pulling_device_id: DEVICE,
      event_id: fixture.examples[0]!.plaintext.header.event_id, server_sequence: 1, source_device_id: REMOTE_DEVICE,
      crypto_version: 1, aad_version: 1, nonce: [0], ciphertext: [1], plaintext: [2] }
    await expect(repository.applyVerifiedResolution(command)).resolves.toBe('applied')
    await expect(repository.reconcileVerifiedResolutionSelfEcho(command)).resolves.toBe('reconciled')
    expect(invoke.mock.calls.map(call => call[0])).toEqual([
      'apply_verified_received_resolution_v2', 'reconcile_verified_received_resolution_self_echo',
    ])
  })

  it('exposes only safe typed top-level errors', () => {
    expect(new NoteResolutionInboxApplyError('runtime_unavailable')).toMatchObject({ code: 'runtime_unavailable' })
  })
})
