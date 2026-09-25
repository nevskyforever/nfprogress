// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import type { NoteSyncInboxRepository, ReceivedNoteSyncInboxItem } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import type { NoteSyncRemoteApplyRepository, VerifiedNoteSyncRemoteApplyCommand } from '@/infrastructure/sqlite/noteSyncRemoteApplyRepository'
import { sealNoteSyncEvent } from './encryptedSyncProtocol'
import { NoteSyncInboxRemoteApplier } from './noteSyncInboxApply'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const EVENT = '123e4567-e89b-42d3-a456-426614174000'
const TIME = '2026-09-21T00:00:00.000000Z'

function runtime() {
  return new NormalUserAuthRuntime({
    login: vi.fn(async () => ({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 })),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn(async () => ({ id: USER, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: TIME })),
  })
}

function lease(amk: AccountMasterKey): AuthoritativeKeyContextLease {
  return {
    localAccountId: 'local', canonicalUserId: USER, authEpoch: 2, keyContextId: 'context', keyEpoch: 1,
    isCurrent: () => true,
    use: async operation => operation(amk),
  }
}

async function received(amk: AccountMasterKey): Promise<ReceivedNoteSyncInboxItem> {
  const event = { event_id: EVENT, project_id: 'project', entity_id: 'note', entity_type: 'note' as const, operation: 'upsert' as const, revision: 1, updated_at: TIME, deleted_at: null }
  const sealed = await sealNoteSyncEvent(amk, USER, event, null, {
    id: 'note', project_id: 'project', stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null,
    content_format: 'html', title: 'private title', content: '<p>private body</p>', checklist: [], color: 'default', pinned: false,
    archived: false, sort_order: 0, tags: [], created_at: TIME, updated_at: TIME, metadata: {},
  })
  return { ...event, server_sequence: 1, source_device_id: DEVICE, envelope: sealed.object }
}

function inbox(item: ReceivedNoteSyncInboxItem): NoteSyncInboxRepository {
  return { readPullState: vi.fn(), commitInboundPage: vi.fn(), listReceived: vi.fn(async () => [item]) }
}

function bindings(auth: NormalUserAuthRuntime): AuthoritativeAccountBinding {
  return new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
}

describe('C15.7B protected decrypt-to-apply adapter', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('holds the lease through IPC and clears adapter-owned plaintext bytes afterwards', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const item = await received(amk)
    let captured: VerifiedNoteSyncRemoteApplyCommand | undefined
    let entered!: () => void
    const enteredPromise = new Promise<void>(resolve => { entered = resolve })
    let release!: () => void
    const releasePromise = new Promise<void>(resolve => { release = resolve })
    let leaseActive = false
    const drainingLease: AuthoritativeKeyContextLease = {
      ...lease(amk),
      use: async operation => {
        leaseActive = true
        try { return await operation(amk) } finally { leaseActive = false }
      },
    }
    const apply: NoteSyncRemoteApplyRepository = {
      applyVerified: vi.fn(async command => {
        captured = command
        entered()
        await releasePromise
        return 'applied' as const
      }),
    }
    const applier = new NoteSyncInboxRemoteApplier(
      auth, bindings(auth), { leaseForAccount: vi.fn(() => drainingLease) } as unknown as RuntimeKeyContext,
      inbox(item), apply,
    )
    const pass = applier.applyOnce('local', DEVICE)
    await enteredPromise
    expect(leaseActive).toBe(true)
    expect(captured?.canonical_user_id).toBe(USER)
    expect(captured?.plaintext.some(byte => byte !== 0)).toBe(true)
    release()
    await expect(pass).resolves.toEqual({ listed: 1, results: [{ event_id: EVENT, server_sequence: 1, status: 'applied' }] })
    expect(captured?.plaintext.every(byte => byte === 0)).toBe(true)
    expect(captured?.nonce.every(byte => byte === 0)).toBe(true)
    expect(captured?.ciphertext.every(byte => byte === 0)).toBe(true)
    expect(item.envelope.ciphertext.every(byte => byte === 0)).toBe(true)
  })

  it('does not invoke Rust when authenticated decryption fails', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const item = await received(amk); item.envelope.ciphertext[0]! ^= 1
    const apply: NoteSyncRemoteApplyRepository = { applyVerified: vi.fn() }
    const result = await new NoteSyncInboxRemoteApplier(
      auth, bindings(auth), { leaseForAccount: vi.fn(() => lease(amk)) } as unknown as RuntimeKeyContext,
      inbox(item), apply,
    ).applyOnce('local', DEVICE)
    expect(result.results).toEqual([{ event_id: EVENT, server_sequence: 1, status: 'error', error_code: 'decrypt_failed' }])
    expect(apply.applyVerified).not.toHaveBeenCalled()
  })

  it('keeps the Rust conflict classification distinct from an apply failure', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const item = await received(amk)
    const apply: NoteSyncRemoteApplyRepository = {
      applyVerified: vi.fn().mockResolvedValue('conflict'),
    }
    const result = await new NoteSyncInboxRemoteApplier(
      auth, bindings(auth), { leaseForAccount: vi.fn(() => lease(amk)) } as unknown as RuntimeKeyContext,
      inbox(item), apply,
    ).applyOnce('local', DEVICE)
    expect(result).toEqual({
      listed: 1,
      results: [{ event_id: EVENT, server_sequence: 1, status: 'conflict' }],
    })
    expect(apply.applyVerified).toHaveBeenCalledTimes(1)
  })

  it('keeps IPC failures distinct from decrypt failures and clears transient bytes', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const item = await received(amk)
    let captured: VerifiedNoteSyncRemoteApplyCommand | undefined
    const apply: NoteSyncRemoteApplyRepository = {
      applyVerified: vi.fn(async command => {
        captured = command
        throw new Error('IPC unavailable')
      }),
    }
    const result = await new NoteSyncInboxRemoteApplier(
      auth, bindings(auth), { leaseForAccount: vi.fn(() => lease(amk)) } as unknown as RuntimeKeyContext,
      inbox(item), apply,
    ).applyOnce('local', DEVICE)
    expect(result.results).toEqual([{ event_id: EVENT, server_sequence: 1, status: 'error', error_code: 'runtime_unavailable' }])
    expect(captured?.plaintext.every(byte => byte === 0)).toBe(true)
  })
})
