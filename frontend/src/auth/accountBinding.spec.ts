// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import type { UserAuthTransport } from '@/api/userAuth'
import type { CloudAccountBindingRepository } from '@/infrastructure/sqlite/cloudAccountBindingRepository'
import { AuthoritativeAccountBinding } from './accountBinding'
import { NormalUserAuthRuntime } from './userAuth'

const USER_ONE = '00000000-0000-0000-0000-000000000101'
const USER_TWO = '00000000-0000-0000-0000-000000000102'

function transport(): UserAuthTransport {
  return {
    login: vi.fn(async username => ({ access_token: username, refresh_token: `r-${username}`, access_expires_in: 60 })),
    refresh: vi.fn(),
    logout: vi.fn(async () => undefined),
    me: vi.fn(async accessToken => ({ id: accessToken === 'one' ? USER_ONE : USER_TWO, username: accessToken, email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' })),
  }
}

describe('authoritative local account binding', () => {
  it('passes only the canonical authenticated user to persistence', async () => {
    const auth = new NormalUserAuthRuntime(transport())
    await auth.login('one', 'password')
    const repository: CloudAccountBindingRepository = { ensure: vi.fn(async () => 'created' as const) }
    const authority = new AuthoritativeAccountBinding(auth, repository)

    await expect(authority.ensureForCurrentUser('opaque-local-account')).resolves.toMatchObject({ result: 'created' })
    expect(repository.ensure).toHaveBeenCalledWith('opaque-local-account', USER_ONE)
  })

  it('does not silently repair a persisted mismatch', async () => {
    const auth = new NormalUserAuthRuntime(transport())
    await auth.login('one', 'password')
    const repository: CloudAccountBindingRepository = {
      ensure: vi.fn(async () => { throw new Error('Cloud account binding identity mismatch') }),
    }
    const authority = new AuthoritativeAccountBinding(auth, repository)
    await expect(authority.ensureForCurrentUser('opaque-local-account')).rejects.toThrow('identity mismatch')
    expect(repository.ensure).toHaveBeenCalledTimes(1)
  })
})
