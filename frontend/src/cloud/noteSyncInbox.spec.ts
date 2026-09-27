import { describe, expect, it, vi } from 'vitest'

const invoke = vi.hoisted(() => vi.fn())
vi.mock('@tauri-apps/api/core', () => ({ invoke }))

import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { SQLiteNoteSyncInboxRepository } from '@/infrastructure/sqlite/noteSyncInboxRepository'
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

  it('adapts a paginated orphan resolution reader without routing it through the v1 decryptor', async () => {
    invoke.mockResolvedValueOnce([{
      event_id: '123e4567-e89b-42d3-a456-426614174098', server_sequence: 7,
      source_device_id: DEVICE, project_id: 'project', entity_id: 'note', entity_type: 'note',
      operation: 'resolution', revision: 4, updated_at: '2026-09-27T00:00:00Z', deleted_at: null,
      envelope: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' },
    }])
    const items = await new SQLiteNoteSyncInboxRepository().listOrphanResolutions('local', DEVICE, USER, 8, 6)
    expect(items).toEqual([expect.objectContaining({ operation: 'resolution', server_sequence: 7, envelope: expect.objectContaining({ crypto_version: 1, aad_version: 1, nonce: new Uint8Array(24), ciphertext: new Uint8Array(16) }) })])
    expect(invoke).toHaveBeenCalledWith('list_orphan_note_resolution_inbox', {
      command: { account_id: 'local', device_id: DEVICE, canonical_user_id: USER, limit: 8, after_server_sequence: 6 },
    })
  })

  it('rejects invalid orphan reader pagination before IPC', async () => {
    const repository = new SQLiteNoteSyncInboxRepository()
    await expect(repository.listOrphanResolutions('local', DEVICE, USER, 0, 0)).rejects.toThrow(RangeError)
    await expect(repository.listOrphanResolutions('local', DEVICE, USER, 1, -1)).rejects.toThrow(RangeError)
    expect(invoke).toHaveBeenCalledTimes(1)
  })
})
