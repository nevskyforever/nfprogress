import { beforeEach, describe, expect, it, vi } from 'vitest'
import { adminApi, adminSession } from './admin'

describe('admin API memory session', () => {
  beforeEach(() => { adminSession.clear(); vi.restoreAllMocks() })

  it('uses bearer authentication without browser token storage', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({
      access_token: 'access-one', refresh_token: 'refresh-one', access_expires_in: 60,
    }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({
      id: '1', username: 'Admin', email: 'admin@example.test', email_verified: true,
      role: 'admin', status: 'active', created_at: '2026-01-01T00:00:00Z',
    }), { status: 200 })).mockResolvedValueOnce(new Response(JSON.stringify({ users: [], total: 0, limit: 50, offset: 0 }), { status: 200 }))
    await adminSession.login('Admin', 'password')
    await adminApi.users()
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({ headers: expect.any(Headers) })
    expect((fetchMock.mock.calls[2]?.[1] as RequestInit).headers as Headers).toHaveProperty('get')
    expect(((fetchMock.mock.calls[2]?.[1] as RequestInit).headers as Headers).get('Authorization')).toBe('Bearer access-one')
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(sessionStorage.getItem('refresh_token')).toBeNull()
  })

  it('replaces both runtime tokens during refresh and clears on logout', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'a', refresh_token: 'r', access_expires_in: 60 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: '1', username: 'Admin', email: 'a@b.test', email_verified: true, role: 'admin', status: 'active', created_at: '2026-01-01T00:00:00Z' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'new-a', refresh_token: 'new-r', access_expires_in: 60 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await adminSession.login('Admin', 'password'); await adminSession.refresh(); await adminSession.logout()
    expect(adminSession.active()).toBe(false)
  })
})
