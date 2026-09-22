// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import type { CurrentUserAccount, UserAuthTransport } from '@/api/userAuth'
import { NormalUserAuthRuntime } from './userAuth'

function user(id: string, username: string): CurrentUserAccount {
  return { id, username, email: `${username}@example.test`, email_verified: true, role: 'user', status: 'active', created_at: 'now' }
}

function transport(accounts: CurrentUserAccount[]): UserAuthTransport {
  let index = 0
  return {
    login: vi.fn(async () => ({ access_token: `access-${index}`, refresh_token: `refresh-${index}`, access_expires_in: 60 })),
    refresh: vi.fn(async () => ({ access_token: `access-r-${index}`, refresh_token: `refresh-r-${index}`, access_expires_in: 60 })),
    me: vi.fn(async () => accounts[index++]!),
    logout: vi.fn(async () => undefined),
  }
}

describe('normal-user authentication runtime', () => {
  it('derives canonical identity from /account/me and invalidates on logout', async () => {
    const api = transport([user('00000000-0000-0000-0000-000000000101', 'one')])
    const auth = new NormalUserAuthRuntime(api)
    const context = await auth.login('caller-name', 'password-not-retained')

    expect(context.userId).toBe('00000000-0000-0000-0000-000000000101')
    expect(auth.state).toBe('authenticated')
    await auth.logout()
    expect(auth.state).toBe('unauthenticated')
    expect(auth.isCurrent(context)).toBe(false)
    expect(api.logout).toHaveBeenCalledWith('access-0')
  })

  it('invalidates the prior generation on account switch and token replacement', async () => {
    const api = transport([
      user('00000000-0000-0000-0000-000000000101', 'one'),
      user('00000000-0000-0000-0000-000000000101', 'one'),
      user('00000000-0000-0000-0000-000000000102', 'two'),
    ])
    const auth = new NormalUserAuthRuntime(api)
    const first = await auth.login('one', 'password')
    const refreshed = await auth.refresh()
    expect(refreshed.authEpoch).toBeGreaterThan(first.authEpoch)
    expect(auth.isCurrent(first)).toBe(false)
    const switched = await auth.login('two', 'password')
    expect(switched.authEpoch).toBeGreaterThan(refreshed.authEpoch)
    expect(switched.userId).toBe('00000000-0000-0000-0000-000000000102')
    expect(auth.isCurrent(refreshed)).toBe(false)
  })

  it.each([401, 403])('fails closed when an authenticated request is rejected with %s', async status => {
    const auth = new NormalUserAuthRuntime(transport([user('00000000-0000-0000-0000-000000000101', 'one')]))
    const context = await auth.login('one', 'password')
    await expect(auth.authorized(async () => {
      throw new ApiError(status, status === 401 ? 'invalid_token' : 'forbidden', 'rejected')
    })).rejects.toBeInstanceOf(ApiError)
    expect(auth.state).toBe(status === 401 ? 'unauthenticated' : 'authenticated')
    expect(auth.isCurrent(context)).toBe(status !== 401)
  })

  it('rejects admin identity in the normal-user runtime', async () => {
    const admin = { ...user('00000000-0000-0000-0000-000000000101', 'admin'), role: 'admin' }
    const auth = new NormalUserAuthRuntime(transport([admin]))
    await expect(auth.login('admin', 'password')).rejects.toThrow()
    expect(auth.state).toBe('unauthenticated')
  })
})
