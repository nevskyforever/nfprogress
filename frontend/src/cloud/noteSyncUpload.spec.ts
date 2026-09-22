import { beforeEach, describe, expect, it, vi } from 'vitest'

const push = vi.hoisted(() => vi.fn())
vi.mock('@/api/encryptedSync', async importOriginal => ({
  ...(await importOriginal<typeof import('@/api/encryptedSync')>()),
  encryptedSyncApi: { push },
}))

import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { NoteSyncOutboxRepository, SealedNoteSyncOutboxItem } from './noteSyncOutbox'
import { NoteSyncUploader } from './noteSyncUpload'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const event = (id = '123e4567-e89b-42d3-a456-426614174002'): SealedNoteSyncOutboxItem => ({
  event_id: id, account_id: 'local', device_id: DEVICE, project_id: 'project', entity_id: 'note', entity_type: 'note',
  operation: 'upsert', revision: 1, parent_event_id: null, updated_at: '2026-09-22T00:00:00Z', deleted_at: null, local_ordinal: 1,
  envelope: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' },
})

function runtime() {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' }),
  })
  const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn().mockResolvedValue('validated') })
  return { auth, binding }
}

function repository(items: SealedNoteSyncOutboxItem[]): NoteSyncOutboxRepository & { commit: ReturnType<typeof vi.fn>, failure: ReturnType<typeof vi.fn> } {
  const commit = vi.fn().mockResolvedValue(['accepted'])
  const failure = vi.fn().mockResolvedValue(undefined)
  return { listSealed: vi.fn().mockResolvedValue(items), commitAccepted: commit, recordUploadFailure: failure, commit, failure }
}

describe('bounded durable Note upload', () => {
  beforeEach(() => push.mockReset())

  it('uploads only the persisted envelope and atomically acknowledges the complete receipt', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    push.mockResolvedValueOnce({ protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 9, duplicate: false }], current_cursor: 9 })
    await expect(new NoteSyncUploader(auth, binding, outbox).uploadOnce('local')).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
    expect(push.mock.calls[0]![1].items[0].object.nonce).toEqual(new Uint8Array(24))
    expect(outbox.commit).toHaveBeenCalledWith('local', DEVICE, [{ event_id: source.event_id, server_sequence: 9, duplicate: false }])
  })

  it('leaves sealed state unacknowledged after lost response and accepts a duplicate retry', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    push.mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 9, duplicate: true }], current_cursor: 9 })
    const uploader = new NoteSyncUploader(auth, binding, outbox)
    await expect(uploader.uploadOnce('local')).rejects.toThrow('timeout')
    expect(outbox.commit).not.toHaveBeenCalled()
    expect(outbox.failure).toHaveBeenCalledWith(expect.objectContaining({ error_code: 'request_timeout' }))
    await uploader.uploadOnce('local')
    expect(push.mock.calls[0]![1].items[0].object.ciphertext).toEqual(push.mock.calls[1]![1].items[0].object.ciphertext)
    expect(outbox.commit.mock.calls[0]![2][0].duplicate).toBe(true)
  })

  it('joins concurrent passes for the same account/device and releases the guard after failure', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    let release!: () => void
    push.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve({ protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 2, duplicate: false }], current_cursor: 2 }) }))
    const uploader = new NoteSyncUploader(auth, binding, outbox)
    const first = uploader.uploadOnce('local')
    await vi.waitFor(() => expect(push).toHaveBeenCalledTimes(1))
    const second = uploader.uploadOnce('local')
    release()
    await expect(Promise.all([first, second])).resolves.toEqual([{ uploaded: 1, deviceId: DEVICE }, { uploaded: 1, deviceId: DEVICE }])
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('does not persist a failure when logout invalidates an in-flight response', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    push.mockImplementationOnce(async () => { await auth.logout(); return { protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 1, duplicate: false }], current_cursor: 1 } })
    await expect(new NoteSyncUploader(auth, binding, outbox).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(outbox.commit).not.toHaveBeenCalled()
    expect(outbox.failure).not.toHaveBeenCalled()
  })

  it('finishes an already-started account-scoped SQLite acceptance across logout', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    let release!: () => void
    outbox.commit.mockImplementationOnce(() => new Promise<void>(resolve => { release = resolve }))
    push.mockResolvedValueOnce({ protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 1, duplicate: false }], current_cursor: 1 })
    const uploading = new NoteSyncUploader(auth, binding, outbox).uploadOnce('local')
    await vi.waitFor(() => expect(outbox.commit).toHaveBeenCalledTimes(1))
    await auth.logout()
    release()
    await expect(uploading).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
    expect(outbox.failure).not.toHaveBeenCalled()
  })

  it('rejects malformed acknowledgements and an account switch before receipt persistence', async () => {
    const { auth, binding } = runtime(); await auth.login('user', 'password')
    const source = event(); const outbox = repository([source])
    push.mockResolvedValueOnce({ protocol_version: 1, encrypted_sync_version: 1, results: [], current_cursor: 0 })
    await expect(new NoteSyncUploader(auth, binding, outbox).uploadOnce('local')).rejects.toThrow('incomplete')
    expect(outbox.commit).not.toHaveBeenCalled()
    push.mockImplementationOnce(async () => { await auth.logout(); return { protocol_version: 1, encrypted_sync_version: 1, results: [{ event_id: source.event_id, server_sequence: 1, duplicate: false }], current_cursor: 1 } })
    await expect(new NoteSyncUploader(auth, binding, outbox).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(outbox.commit).not.toHaveBeenCalled()
  })
})
