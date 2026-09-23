// @vitest-environment node
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import type { AuthoritativeKeyContextLease, RuntimeKeyContext } from '@/auth/keyContext'
import { NormalUserAuthRuntime } from '@/auth/userAuth'
import { generateAccountMasterKey, type AccountMasterKey } from '@/crypto'
import type { NoteSyncInboxRepository, ReceivedNoteSyncInboxItem } from '@/infrastructure/sqlite/noteSyncInboxRepository'
import { sealNoteSyncEvent } from './encryptedSyncProtocol'
import { NoteInboxDecryptError, NoteSyncInboxDecryptor } from './noteSyncInboxDecrypt'

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

function lease(amk: AccountMasterKey, active = () => true): AuthoritativeKeyContextLease {
  return {
    localAccountId: 'local', canonicalUserId: USER, authEpoch: 2, keyContextId: 'context', keyEpoch: 1,
    isCurrent: active,
    use: async operation => operation(amk),
  }
}

async function item(amk: AccountMasterKey, overrides: Partial<ReceivedNoteSyncInboxItem> = {}): Promise<ReceivedNoteSyncInboxItem> {
  const event = { event_id: EVENT, project_id: 'project', entity_id: 'note', entity_type: 'note' as const, operation: 'upsert' as const, revision: 1, updated_at: TIME, deleted_at: null }
  const sealed = await sealNoteSyncEvent(amk, USER, event, null, {
    id: 'note', project_id: 'project', stage_id: null, source_type: 'project', source_map_id: null, source_node_id: null,
    content_format: 'html', title: 'private title', content: '<p>private body</p>', checklist: [], color: 'default', pinned: false,
    archived: false, sort_order: 0, tags: [], created_at: TIME, updated_at: TIME, metadata: {},
  })
  return { ...event, server_sequence: 1, source_device_id: DEVICE, envelope: sealed.object, ...overrides }
}

describe('C15.7A authenticated durable inbox decryption', () => {
  let amk: AccountMasterKey
  beforeAll(async () => { amk = await generateAccountMasterKey() })

  it('decrypts a real sealed durable item into metadata only without writing durable state', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
    const received = await item(amk)
    const repository: NoteSyncInboxRepository = { readPullState: vi.fn(), commitInboundPage: vi.fn(), listReceived: vi.fn(async () => [received]) }
    const keys = { leaseForAccount: vi.fn(() => lease(amk)) } as unknown as RuntimeKeyContext
    const pass = new NoteSyncInboxDecryptor(auth, binding, keys, repository)
    await expect(pass.decryptOnce('local', DEVICE)).resolves.toEqual({ listed: 1, results: [{ event_id: EVENT, server_sequence: 1, status: 'validated' }] })
    expect(repository.commitInboundPage).not.toHaveBeenCalled()
    expect(received.envelope.ciphertext.every(byte => byte === 0)).toBe(true)
  })

  it('keeps malformed ciphertext as a classified result and preserves the reader boundary', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
    const received = await item(amk); received.envelope.ciphertext[0]! ^= 1
    const repository: NoteSyncInboxRepository = { readPullState: vi.fn(), commitInboundPage: vi.fn(), listReceived: vi.fn(async () => [received]) }
    const keys = { leaseForAccount: vi.fn(() => lease(amk)) } as unknown as RuntimeKeyContext
    await expect(new NoteSyncInboxDecryptor(auth, binding, keys, repository).decryptOnce('local', DEVICE)).resolves.toMatchObject({
      results: [{ status: 'error', error_code: 'decrypt_failed' }],
    })
  })

  it('does not start when the AMK is unavailable or auth has gone stale', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
    const repository: NoteSyncInboxRepository = { readPullState: vi.fn(), commitInboundPage: vi.fn(), listReceived: vi.fn() }
    const noKeys = { leaseForAccount: vi.fn(() => null) } as unknown as RuntimeKeyContext
    await expect(new NoteSyncInboxDecryptor(auth, binding, noKeys, repository).decryptOnce('local', DEVICE)).rejects.toEqual(expect.objectContaining({ code: 'key_unavailable' }))
    const staleKeys = { leaseForAccount: vi.fn(() => lease(amk, () => false)) } as unknown as RuntimeKeyContext
    await expect(new NoteSyncInboxDecryptor(auth, binding, staleKeys, repository).decryptOnce('local', DEVICE)).rejects.toBeInstanceOf(NoteInboxDecryptError)
    expect(repository.listReceived).not.toHaveBeenCalled()
  })

  it('honors the existing lease drain boundary when logout races a protected pass', async () => {
    const auth = runtime(); await auth.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn(async () => 'validated' as const) })
    const received = await item(amk)
    let entered!: () => void; const enteredPromise = new Promise<void>(resolve => { entered = resolve })
    let release!: () => void; const releasePromise = new Promise<void>(resolve => { release = resolve })
    const drainingLease = { ...lease(amk), use: async <T>(operation: (key: AccountMasterKey) => Promise<T>) => { entered(); await releasePromise; return operation(amk) } }
    const repository: NoteSyncInboxRepository = { readPullState: vi.fn(), commitInboundPage: vi.fn(), listReceived: vi.fn(async () => [received]) }
    const keys = { leaseForAccount: vi.fn(() => drainingLease) } as unknown as RuntimeKeyContext
    const operation = new NoteSyncInboxDecryptor(auth, binding, keys, repository).decryptOnce('local', DEVICE)
    await enteredPromise
    const logout = auth.logout()
    release()
    await logout
    await expect(operation).resolves.toMatchObject({ results: [{ status: 'validated' }] })
    expect(repository.commitInboundPage).not.toHaveBeenCalled()
  })
})
