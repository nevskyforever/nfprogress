import { describe, expect, it, vi } from 'vitest'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { NoteSyncAckRepository } from '@/infrastructure/sqlite/noteSyncAckRepository'
import { NoteSyncDeviceAckAdapter } from './noteSyncDeviceAck'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'

function runtime() {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'u@example.test', email_verified: true, role: 'user', status: 'active', created_at: '2026-01-01T00:00:00Z' }),
  })
  return { auth, binding: new AuthoritativeAccountBinding(auth, { ensure: vi.fn().mockResolvedValue('validated') }) }
}

function repository(overrides: Partial<NoteSyncAckRepository> = {}) {
  return {
    prepare: vi.fn().mockResolvedValue({ current_ack_cursor: 2, candidate_cursor: 4 }),
    commit: vi.fn().mockResolvedValue('advanced'),
    ...overrides,
  } as NoteSyncAckRepository & { prepare: ReturnType<typeof vi.fn>, commit: ReturnType<typeof vi.fn> }
}

function transport() {
  return {
    registerDevice: vi.fn().mockResolvedValue({ protocol_version: 1, device_id: DEVICE, last_ack_cursor: 0 }),
    ack: vi.fn().mockResolvedValue(undefined),
  }
}

describe('durable Note device registration and ACK transport', () => {
  it('registers the existing durable device without copying server ACK state', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository(); const api = transport()
    api.registerDevice.mockResolvedValue({ protocol_version: 1, device_id: DEVICE, last_ack_cursor: 99 })
    await expect(new NoteSyncDeviceAckAdapter(auth, binding, store, api).registerOnce('local', DEVICE)).resolves.toEqual({ deviceId: DEVICE, serverAckCursor: 99 })
    expect(store.prepare).toHaveBeenCalledWith('local', DEVICE, USER)
    expect(store.commit).not.toHaveBeenCalled()
    await new NoteSyncDeviceAckAdapter(auth, binding, store, api).registerOnce('local', DEVICE)
    expect(api.registerDevice).toHaveBeenCalledTimes(2)
  })

  it('rejects malformed or lost registration responses without local mutation', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository(); const api = transport()
    api.registerDevice.mockResolvedValueOnce({ protocol_version: 1, device_id: DEVICE.toUpperCase(), last_ack_cursor: 0 })
      .mockRejectedValueOnce(new Error('timeout'))
    const adapter = new NoteSyncDeviceAckAdapter(auth, binding, store, api)
    await expect(adapter.registerOnce('local', DEVICE)).rejects.toThrow('Malformed')
    await expect(adapter.registerOnce('local', DEVICE)).rejects.toThrow('timeout')
    expect(store.commit).not.toHaveBeenCalled()
  })

  it('does not send ACK without a durable contiguous candidate', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository({ prepare: vi.fn().mockResolvedValue({ current_ack_cursor: 2, candidate_cursor: 2 }) }); const api = transport()
    await expect(new NoteSyncDeviceAckAdapter(auth, binding, store, api).ackOnce('local', DEVICE)).resolves.toEqual({ status: 'no_progress', cursor: 2 })
    expect(api.ack).not.toHaveBeenCalled(); expect(store.commit).not.toHaveBeenCalled()
  })

  it('ACKs first, then conditionally commits local cursor and accepts replay outcomes', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository(); const api = transport()
    const adapter = new NoteSyncDeviceAckAdapter(auth, binding, store, api)
    await expect(adapter.ackOnce('local', DEVICE)).resolves.toEqual({ status: 'advanced', cursor: 4 })
    expect(api.ack).toHaveBeenCalledWith('token', { protocol_version: 1, device_id: DEVICE, cursor: 4 })
    expect(store.commit).toHaveBeenCalledWith('local', DEVICE, USER, 2, 4)
    store.commit.mockResolvedValueOnce('already_acknowledged')
    await expect(adapter.ackOnce('local', DEVICE)).resolves.toEqual({ status: 'already_acknowledged', cursor: 4 })
    store.commit.mockResolvedValueOnce('stale')
    await expect(adapter.ackOnce('local', DEVICE)).resolves.toEqual({ status: 'stale', cursor: 4 })
  })

  it('does not commit after a lost ACK response and safely retries after a local post-204 failure', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository(); const api = transport(); const adapter = new NoteSyncDeviceAckAdapter(auth, binding, store, api)
    api.ack.mockRejectedValueOnce(new Error('timeout')).mockResolvedValue(undefined)
    await expect(adapter.ackOnce('local', DEVICE)).rejects.toThrow('timeout')
    expect(store.commit).not.toHaveBeenCalled()
    store.commit.mockRejectedValueOnce(new Error('sqlite unavailable')).mockResolvedValueOnce('advanced')
    await expect(adapter.ackOnce('local', DEVICE)).rejects.toThrow('sqlite unavailable')
    await expect(adapter.ackOnce('local', DEVICE)).resolves.toEqual({ status: 'advanced', cursor: 4 })
    expect(api.ack).toHaveBeenCalledTimes(3)
  })

  it('rejects stale auth during registration, ACK, and before local commit', async () => {
    const { auth, binding } = runtime(); await auth.login('u', 'p')
    const store = repository(); const api = transport()
    api.registerDevice.mockImplementationOnce(async () => { await auth.logout(); return { protocol_version: 1, device_id: DEVICE, last_ack_cursor: 0 } })
    await expect(new NoteSyncDeviceAckAdapter(auth, binding, store, api).registerOnce('local', DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
    await auth.login('u', 'p')
    api.ack.mockImplementationOnce(async () => { await auth.logout() })
    await expect(new NoteSyncDeviceAckAdapter(auth, binding, store, api).ackOnce('local', DEVICE)).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(store.commit).not.toHaveBeenCalled()
  })
})
