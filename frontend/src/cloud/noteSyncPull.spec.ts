import { beforeEach, describe, expect, it, vi } from 'vitest'

const pull = vi.hoisted(() => vi.fn())
vi.mock('@/api/encryptedSync', () => ({ encryptedSyncApi: { pull } }))

import { ApiError } from '@/api/client'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { NoteSyncPuller } from './noteSyncPull'

const USER_ONE = '123e4567-e89b-42d3-a456-426614174099'
const USER_TWO = '123e4567-e89b-42d3-a456-426614174098'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'

function page(sequence = 1) {
  return {
    protocol_version: 1 as const, encrypted_sync_version: 1 as const, next_cursor: sequence, has_more: false,
    items: [{ event: {
      event_id: '123e4567-e89b-42d3-a456-426614174002', device_id: DEVICE, project_id: 'project', entity_id: 'note', entity_type: 'note',
      operation: 'upsert' as const, revision: 1, updated_at: '2026-09-22T00:00:00Z', deleted_at: null, server_sequence: sequence,
    }, object: { crypto_version: 1 as const, aad_version: 1 as const, nonce: new Uint8Array(24), ciphertext: new Uint8Array(16) } }],
  }
}

function runtime() {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn(async username => ({ access_token: username, refresh_token: 'refresh', access_expires_in: 60 })), refresh: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(async token => ({ id: token === 'two' ? USER_TWO : USER_ONE, username: token, email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' })),
  })
  const ensure = vi.fn().mockResolvedValue('validated')
  return { auth, ensure, puller: new NoteSyncPuller(auth, new AuthoritativeAccountBinding(auth, { ensure })) }
}

describe('authenticated read-only encrypted pull', () => {
  beforeEach(() => pull.mockReset())

  it('binds the local account to the normal user and returns one opaque bounded page without persistence', async () => {
    const { auth, ensure, puller } = runtime(); await auth.login('one', 'password')
    pull.mockResolvedValueOnce(page())
    await expect(puller.pullOnce('local-account', DEVICE, 0)).resolves.toMatchObject({ accountId: 'local-account', deviceId: DEVICE, since: 0, nextCursor: 1 })
    expect(ensure).toHaveBeenCalledWith('local-account', USER_ONE)
    expect(pull).toHaveBeenCalledWith('one', DEVICE, 0, 200)
  })

  it('uses the caller cursor only for this request and supports explicit consecutive pages', async () => {
    const { auth, puller } = runtime(); await auth.login('one', 'password')
    pull.mockResolvedValueOnce(page(1)).mockResolvedValueOnce(page(2))
    await expect(puller.pullOnce('local', DEVICE, 0)).resolves.toMatchObject({ nextCursor: 1 })
    await expect(puller.pullOnce('local', DEVICE, 1)).resolves.toMatchObject({ nextCursor: 2 })
    expect(pull.mock.calls.map(call => call[2])).toEqual([0, 1])
  })

  it('discards an in-flight page after logout or account switch', async () => {
    const { auth, puller } = runtime(); await auth.login('one', 'password')
    pull.mockImplementationOnce(async () => { await auth.logout(); return page() })
    await expect(puller.pullOnce('local', DEVICE, 0)).rejects.toBeInstanceOf(StaleAuthContextError)
    await auth.login('one', 'password')
    pull.mockImplementationOnce(async () => { await auth.login('two', 'password'); return page() })
    await expect(puller.pullOnce('local', DEVICE, 0)).rejects.toBeInstanceOf(StaleAuthContextError)
  })

  it('leaves the result unreturned and the auth context invalidated after HTTP 401', async () => {
    const { auth, puller } = runtime(); await auth.login('one', 'password')
    pull.mockRejectedValueOnce(new ApiError(401, 'unauthorized', 'unauthorized'))
    await expect(puller.pullOnce('local', DEVICE, 0)).rejects.toBeInstanceOf(ApiError)
    expect(auth.state).toBe('unauthenticated')
  })
})
