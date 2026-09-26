import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { NoteSyncResolutionUploadRepository, ResolutionUploadItem } from '@/infrastructure/sqlite/noteSyncResolutionUploadRepository'
import { NoteSyncResolutionUploadError, NoteSyncResolutionUploader } from './noteSyncResolutionUpload'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const id = (number = 2) => `123e4567-e89b-42d3-a456-${String(number).padStart(12, '0')}`
const item = (number = 2, ciphertext = 'AAAAAAAAAAAAAAAAAAAAAA'): ResolutionUploadItem => ({
  event_id: id(number), account_id: 'local', device_id: DEVICE, project_id: 'project', entity_id: 'note',
  entity_type: 'note', operation: 'resolution', revision: 2, updated_at: '2026-01-01T00:00:00.000000Z',
  envelope: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext },
})

async function setup(mode: 1 | 2 = 2) {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'e@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
  await auth.login('user', 'password')
  const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn().mockResolvedValue('validated') })
  const list = vi.fn().mockResolvedValue([item()])
  const commit = vi.fn().mockImplementation(command => Promise.resolve(command.receipts.map(() => 'accepted')))
  const repository: NoteSyncResolutionUploadRepository = { list, commit }
  const capabilities = vi.fn().mockResolvedValue({ supported_transport_version: 2, writer_transport_version: mode, cutover_epoch: 0 })
  const push = vi.fn().mockImplementation((_token, request) => Promise.resolve({
    protocol_version: 2, encrypted_sync_version: 2,
    results: request.items.map((row: { event: { event_id: string } }, index: number) => ({ event_id: row.event.event_id, server_sequence: index + 1, duplicate: false })),
    current_cursor: request.items.length,
  }))
  const identity = { read: vi.fn().mockResolvedValue({ local_account_id: 'local', device_id: DEVICE }) } as unknown as CloudIdentityRepository
  return { auth, binding, list, commit, repository, api: { capabilities, push }, identity }
}

function uploader(s: Awaited<ReturnType<typeof setup>>) {
  return new NoteSyncResolutionUploader(s.auth, s.binding, s.identity, s.repository, s.api)
}

describe('dormant resolution uploader', () => {
  it('stops mode 1 before native selection and preserves authoritative account scope', async () => {
    const s = await setup(1)
    await expect(uploader(s).uploadOnce('local')).resolves.toEqual({ uploaded: 0, deviceId: null })
    expect(s.list).not.toHaveBeenCalled()
    expect(s.api.push).not.toHaveBeenCalled()
    expect(s.api.capabilities).toHaveBeenCalledTimes(1)
  })

  it('rejects a caller account that does not match durable identity', async () => {
    const s = await setup()
    s.identity.read = vi.fn().mockResolvedValue({ local_account_id: 'different', device_id: DEVICE })
    await expect(uploader(s).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(s.list).not.toHaveBeenCalled()
    expect(s.api.push).not.toHaveBeenCalled()
  })

  it('fails closed for malformed capabilities and mode-incompatible push', async () => {
    const malformed = await setup()
    malformed.api.capabilities.mockResolvedValue({ supported_transport_version: 2, writer_transport_version: 2 })
    await expect(uploader(malformed).uploadOnce('local')).rejects.toThrow()
    expect(malformed.list).not.toHaveBeenCalled()

    const changed = await setup()
    changed.api.push.mockRejectedValue(new ApiError(409, 'sync_transport_mode_incompatible', 'changed'))
    await expect(uploader(changed).uploadOnce('local')).rejects.toMatchObject({ code: 'mode_incompatible' } satisfies Partial<NoteSyncResolutionUploadError>)
    expect(changed.commit).not.toHaveBeenCalled()
  })

  it('rechecks the complete immutable ready batch and emits only opaque transport fields', async () => {
    const s = await setup()
    await uploader(s).uploadOnce('local')
    expect(s.list).toHaveBeenCalledTimes(2)
    expect(s.api.push).toHaveBeenCalledTimes(1)
    const wireItem = s.api.push.mock.calls[0]![1].items[0]
    expect(wireItem).toEqual(expect.objectContaining({ event: expect.objectContaining({ operation: 'resolution', deleted_at: null }) }))
    expect(wireItem).not.toHaveProperty('canonical_payload')
    expect(wireItem).not.toHaveProperty('parents')
    expect(JSON.stringify(wireItem)).not.toContain('AMK')
    expect(s.commit).toHaveBeenCalledWith(expect.objectContaining({ account_id: 'local', device_id: DEVICE, canonical_user_id: USER, receipts: expect.any(Array) }))
  })

  it('does not dispatch when fresh readiness disappears, envelope changes, or batch membership changes', async () => {
    for (const fresh of [[], [item(2, 'AAAAAAAAAAAAAAAAAAAAAB')], [item(), item(3)]]) {
      const s = await setup()
      s.list.mockResolvedValueOnce([item()]).mockResolvedValueOnce(fresh)
      await expect(uploader(s).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
      expect(s.api.push).not.toHaveBeenCalled()
      expect(s.commit).not.toHaveBeenCalled()
    }
  })

  it('requires the same ready event order on the second native read', async () => {
    const s = await setup()
    s.list.mockResolvedValueOnce([item(), item(3)]).mockResolvedValueOnce([item(3), item()])
    await expect(uploader(s).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(s.api.push).not.toHaveBeenCalled()
  })

  it('commits exactly one fully validated receipt batch and rejects malformed responses', async () => {
    const success = await setup()
    success.list.mockResolvedValue([item(), item(3)])
    await uploader(success).uploadOnce('local')
    expect(success.commit).toHaveBeenCalledTimes(1)
    expect(success.commit.mock.calls[0]![0].receipts).toHaveLength(2)

    for (const response of [
      { protocol_version: 2, encrypted_sync_version: 2, results: [], current_cursor: 0 },
      { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(), server_sequence: 1, duplicate: false }, { event_id: id(), server_sequence: 2, duplicate: false }], current_cursor: 2 },
      { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(), server_sequence: 2, duplicate: false }], current_cursor: 1 },
    ]) {
      const s = await setup()
      s.api.push.mockResolvedValue(response)
      await expect(uploader(s).uploadOnce('local')).rejects.toThrow()
      expect(s.commit).not.toHaveBeenCalled()
    }
  })

  it('keeps the exact sealed envelope through lost response and duplicate retry', async () => {
    const s = await setup()
    s.api.push.mockRejectedValueOnce(new Error('lost response')).mockResolvedValueOnce({
      protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(), server_sequence: 7, duplicate: true }], current_cursor: 7,
    })
    const subject = uploader(s)
    await expect(subject.uploadOnce('local')).rejects.toThrow('lost response')
    await expect(subject.uploadOnce('local')).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
    expect(s.api.push.mock.calls[0]![1].items[0].object).toEqual(s.api.push.mock.calls[1]![1].items[0].object)
    expect(s.commit.mock.calls[0]![0].receipts[0]).toEqual({ event_id: id(), server_sequence: 7, duplicate: true })
  })

  it('leaves an event sealed when native acceptance fails after a valid server response', async () => {
    const s = await setup()
    s.commit.mockRejectedValue(new Error('native receipt transaction failed'))
    await expect(uploader(s).uploadOnce('local')).rejects.toThrow('native receipt transaction failed')
    expect(s.api.push).toHaveBeenCalledTimes(1)
    expect(s.commit).toHaveBeenCalledTimes(1)
  })

  it('rejects a malformed native acceptance result but lets an already-started scoped commit finish after logout', async () => {
    const malformed = await setup()
    malformed.commit.mockResolvedValue([])
    await expect(uploader(malformed).uploadOnce('local')).rejects.toThrow('Invalid resolution acceptance result.')

    const completing = await setup()
    let release!: () => void
    completing.commit.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve(['accepted']) }))
    const result = uploader(completing).uploadOnce('local')
    await vi.waitFor(() => expect(completing.commit).toHaveBeenCalledTimes(1))
    await completing.auth.logout()
    release()
    await expect(result).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
  })

  it('single-flights matching callers, releases after failure, and never accepts after logout', async () => {
    const s = await setup()
    let release!: () => void
    s.api.push.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve({ protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(), server_sequence: 1, duplicate: false }], current_cursor: 1 }) }))
    const subject = uploader(s)
    const first = subject.uploadOnce('local')
    const second = subject.uploadOnce('local')
    await vi.waitFor(() => expect(s.api.push).toHaveBeenCalledTimes(1))
    release()
    await Promise.all([first, second])
    expect(s.api.push).toHaveBeenCalledTimes(1)

    s.api.push.mockRejectedValueOnce(new Error('retry'))
    await expect(subject.uploadOnce('local')).rejects.toThrow('retry')
    await expect(subject.uploadOnce('local')).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })

    const stale = await setup()
    stale.api.push.mockImplementationOnce(async () => { await stale.auth.logout(); return { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(), server_sequence: 1, duplicate: false }], current_cursor: 1 } })
    await expect(uploader(stale).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(stale.commit).not.toHaveBeenCalled()
  })

  it('does not dispatch after logout before capabilities or after the first native read', async () => {
    const beforeCapabilities = await setup()
    beforeCapabilities.api.capabilities.mockImplementationOnce(async () => { await beforeCapabilities.auth.logout(); return { supported_transport_version: 2, writer_transport_version: 2, cutover_epoch: 0 } })
    await expect(uploader(beforeCapabilities).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(beforeCapabilities.api.push).not.toHaveBeenCalled()

    const afterRead = await setup()
    afterRead.list.mockImplementationOnce(async () => { await afterRead.auth.logout(); return [item()] })
    await expect(uploader(afterRead).uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(afterRead.api.push).not.toHaveBeenCalled()
  })

  it('bounds to one hundred events and fails explicitly when the first envelope exceeds wire limits', async () => {
    const limited = await setup()
    const hundredAndOne = Array.from({ length: 101 }, (_, index) => item(index + 2))
    limited.list.mockResolvedValueOnce(hundredAndOne).mockResolvedValueOnce(hundredAndOne.slice(0, 100))
    await uploader(limited).uploadOnce('local')
    expect(limited.api.push.mock.calls[0]![1].items).toHaveLength(100)

    const oversized = await setup()
    oversized.list.mockResolvedValue([item(2, 'A'.repeat(12_000_000))])
    await expect(uploader(oversized).uploadOnce('local')).rejects.toThrow()
    expect(oversized.api.push).not.toHaveBeenCalled()
  })

  it('selects a stable prefix when the full native batch exceeds aggregate ciphertext limits', async () => {
    const s = await setup()
    const large = 'A'.repeat(8_000_000)
    const nativeBatch = [item(2, large), item(3, large), item(4, large)]
    s.list.mockResolvedValueOnce(nativeBatch).mockResolvedValueOnce(nativeBatch.slice(0, 2))
    await expect(uploader(s).uploadOnce('local')).resolves.toEqual({ uploaded: 2, deviceId: DEVICE })
    expect(s.list.mock.calls[1]![0].limit).toBe(2)
    expect(s.api.push.mock.calls[0]![1].items).toHaveLength(2)
  }, 30_000)
})
