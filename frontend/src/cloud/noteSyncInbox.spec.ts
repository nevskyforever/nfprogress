import { describe, expect, it, vi } from 'vitest'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { DurableNoteSyncInbox } from './noteSyncInbox'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'

function auth() {
  return new NormalUserAuthRuntime({
    login: vi.fn(async () => ({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 })), refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn(async () => ({ id: USER, username: 'u', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' })),
  })
}

describe('durable encrypted inbox orchestration', () => {
  it('reads the durable cursor and commits the validated page without applying it', async () => {
    const runtime = auth(); await runtime.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(runtime, { ensure: vi.fn().mockResolvedValue('validated') })
    const pullOnce = vi.fn().mockResolvedValue({ accountId: 'local', deviceId: DEVICE, since: 4, nextCursor: 5, hasMore: false, items: [] })
    const repository = { readPullState: vi.fn().mockResolvedValue({ pull_cursor: 4, ack_cursor: 2 }), listReceived: vi.fn(), commitInboundPage: vi.fn().mockResolvedValue({ committed_cursor: 5, new_events: 0, replayed_events: 0, has_more: false }) }
    const inbox = new DurableNoteSyncInbox(runtime, binding, { pullOnce } as never, repository)
    await expect(inbox.pullOnce('local', DEVICE)).resolves.toMatchObject({ committed_cursor: 5 })
    expect(pullOnce).toHaveBeenCalledWith('local', DEVICE, 4)
    expect(repository.commitInboundPage).toHaveBeenCalled()
  })

  it('does not commit after auth invalidation during the pull', async () => {
    const runtime = auth(); await runtime.login('u', 'p')
    const binding = new AuthoritativeAccountBinding(runtime, { ensure: vi.fn().mockResolvedValue('validated') })
    const pullOnce = vi.fn(async () => { await runtime.logout(); return {} })
    const repository = { readPullState: vi.fn().mockResolvedValue({ pull_cursor: 0, ack_cursor: 0 }), listReceived: vi.fn(), commitInboundPage: vi.fn() }
    const inbox = new DurableNoteSyncInbox(runtime, binding, { pullOnce } as never, repository)
    await expect(inbox.pullOnce('local', DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(repository.commitInboundPage).not.toHaveBeenCalled()
  })
})
