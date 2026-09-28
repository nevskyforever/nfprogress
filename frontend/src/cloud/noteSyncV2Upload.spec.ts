import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { AuthoritativeAccountBinding } from '@/auth/accountBinding'
import { NormalUserAuthRuntime, StaleAuthContextError } from '@/auth/userAuth'
import type { CloudIdentityRepository } from '@/infrastructure/sqlite/cloudIdentityRepository'
import type { NoteSyncOutboxRepository, SealedNoteSyncOutboxItem } from './noteSyncOutbox'
import { NoteSyncV2Uploader } from './noteSyncV2Upload'

const USER = '123e4567-e89b-42d3-a456-426614174099'
const DEVICE = '123e4567-e89b-42d3-a456-426614174001'
const id = (n: number) => `123e4567-e89b-42d3-a456-${String(n).padStart(12, '0')}`
const item = (n = 2, operation: 'upsert' | 'delete' = 'upsert', parent: string | null = null): SealedNoteSyncOutboxItem => ({
  event_id: id(n), account_id: 'local', device_id: DEVICE, project_id: 'project', entity_id: 'note', entity_type: 'note',
  operation, revision: 1, parent_event_id: parent, updated_at: '2026-01-01T00:00:00Z',
  deleted_at: operation === 'delete' ? '2026-01-02T00:00:00Z' : null, local_ordinal: n,
  envelope: { crypto_version: 1, aad_version: 1, nonce: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', ciphertext: 'AAAAAAAAAAAAAAAAAAAAAA' },
})

async function setup(items = [item()], mode: 1 | 2 = 2) {
  const auth = new NormalUserAuthRuntime({
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh', access_expires_in: 60 }),
    refresh: vi.fn(), logout: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: USER, username: 'user', email: 'e@example.test', email_verified: true, role: 'user', status: 'active', created_at: 'now' }),
  })
  await auth.login('user', 'password')
  const binding = new AuthoritativeAccountBinding(auth, { ensure: vi.fn().mockResolvedValue('validated') })
  const identity = { read: vi.fn().mockResolvedValue({ local_account_id: 'local', device_id: DEVICE }) } as unknown as CloudIdentityRepository
  const listSealed = vi.fn().mockResolvedValue(items)
  const commitAccepted = vi.fn().mockImplementation((_account, _device, receipts: unknown[]) => Promise.resolve(receipts.map(() => 'accepted')))
  const recordUploadFailure = vi.fn().mockResolvedValue(undefined)
  const outbox: NoteSyncOutboxRepository = { listSealed, commitAccepted, recordUploadFailure }
  const capabilities = vi.fn().mockResolvedValue({ supported_transport_version: 2, writer_transport_version: mode, cutover_epoch: 0 })
  const push = vi.fn().mockImplementation((_token, request) => Promise.resolve({
    protocol_version: 2, encrypted_sync_version: 2,
    results: request.items.map((row: { event: { event_id: string } }, index: number) => ({ event_id: row.event.event_id, server_sequence: index + 1, duplicate: false })),
    current_cursor: request.items.length,
  }))
  const api = { capabilities, push }
  return { auth, binding, identity, listSealed, commitAccepted, recordUploadFailure, api, outbox,
    uploader: () => new NoteSyncV2Uploader(auth, binding, identity, outbox, api) }
}

describe('dormant ordinary v2 Note uploader', () => {
  it.each(['upsert', 'delete'] as const)('uploads an ordinary %s-only batch', async operation => {
    const s = await setup([item(2, operation), item(3, operation)])
    await expect(s.uploader().uploadOnce('local')).resolves.toEqual({ uploaded: 2, deviceId: DEVICE })
    expect(s.api.push.mock.calls[0]![1].items.every((row: { event: { operation: string } }) => row.event.operation === operation)).toBe(true)
  })

  it('uploads sealed upsert/delete bytes and commits exact native receipts', async () => {
    const s = await setup([item(2), item(3, 'delete')])
    await expect(s.uploader().uploadOnce('local')).resolves.toEqual({ uploaded: 2, deviceId: DEVICE })
    expect(s.api.push.mock.calls[0]![1].items.map((x: { event: { operation: string, deleted_at: string | null } }) => [x.event.operation, x.event.deleted_at])).toEqual([
      ['upsert', null], ['delete', '2026-01-02T00:00:00Z'],
    ])
    expect(s.api.push.mock.calls[0]![1].items[0].object).toEqual(item().envelope)
    expect(s.commitAccepted).toHaveBeenCalledWith('local', DEVICE, [
      { event_id: id(2), server_sequence: 1, duplicate: false }, { event_id: id(3), server_sequence: 2, duplicate: false },
    ])
  })

  it('requires durable account/device scope for every listed row before HTTP', async () => {
    const wrongIdentity = await setup()
    wrongIdentity.identity.read = vi.fn().mockResolvedValue({ local_account_id: 'other', device_id: DEVICE })
    await expect(wrongIdentity.uploader().uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(wrongIdentity.api.push).not.toHaveBeenCalled()
    for (const row of [{ ...item(), device_id: id(88) }, { ...item(), account_id: 'other' }]) {
      const s = await setup([item(), row])
      await expect(s.uploader().uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
      expect(s.api.push).not.toHaveBeenCalled()
    }
  })

  it('orders sealed parents before children and bounds the batch at 100 events', async () => {
    const child = item(3, 'upsert', id(2))
    const s = await setup([child, item(2), ...Array.from({ length: 101 }, (_, n) => item(n + 4))])
    await s.uploader().uploadOnce('local')
    const sent = s.api.push.mock.calls[0]![1].items
    expect(sent).toHaveLength(100)
    expect(sent[0].event.event_id).toBe(id(2))
    expect(sent[1].event.event_id).toBe(id(4))
    expect(sent.some((x: { event: { event_id: string } }) => x.event.event_id === id(3))).toBe(false)
  })

  it('stops before an event that exceeds the aggregate ciphertext budget without losing it', async () => {
    const large = 'A'.repeat(11_184_832)
    const first = { ...item(2), envelope: { ...item(2).envelope, ciphertext: large } }
    const later = { ...item(3), envelope: { ...item(3).envelope, ciphertext: large } }
    const s = await setup([first, later])
    await expect(s.uploader().uploadOnce('local')).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
    expect(s.api.push.mock.calls[0]![1].items).toHaveLength(1)
    expect(s.api.push.mock.calls[0]![1].items[0].event.event_id).toBe(first.event_id)
  }, 30_000)

  it('rechecks the same immutable sealed selection immediately before dispatch', async () => {
    const s = await setup()
    s.listSealed.mockResolvedValueOnce([item()]).mockResolvedValueOnce([{ ...item(), envelope: { ...item().envelope, ciphertext: 'AQAAAAAAAAAAAAAAAAAAAA' } }])
    await expect(s.uploader().uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(s.api.push).not.toHaveBeenCalled()
  })

  it('rejects mode 1 and a backend mode flip without acceptance or permanent failure', async () => {
    const modeOne = await setup([item()], 1)
    await expect(modeOne.uploader().uploadOnce('local')).rejects.toMatchObject({ code: 'mode_incompatible' })
    expect(modeOne.api.push).not.toHaveBeenCalled()
    expect(modeOne.commitAccepted).not.toHaveBeenCalled()
    expect(modeOne.recordUploadFailure).not.toHaveBeenCalled()
    const flipped = await setup()
    flipped.api.push.mockRejectedValueOnce(new ApiError(409, 'sync_transport_mode_incompatible', 'changed'))
    await expect(flipped.uploader().uploadOnce('local')).rejects.toMatchObject({ code: 'mode_incompatible' })
    expect(flipped.commitAccepted).not.toHaveBeenCalled()
    expect(flipped.recordUploadFailure).not.toHaveBeenCalled()
  })

  it('checks auth before dispatch and after HTTP before native acceptance', async () => {
    const before = await setup()
    before.listSealed.mockImplementationOnce(async () => { await before.auth.logout(); return [item()] })
    await expect(before.uploader().uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(before.api.push).not.toHaveBeenCalled()
    const after = await setup()
    after.api.push.mockImplementationOnce(async () => { await after.auth.logout(); return { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(2), server_sequence: 1, duplicate: false }], current_cursor: 1 } })
    await expect(after.uploader().uploadOnce('local')).rejects.toBeInstanceOf(StaleAuthContextError)
    expect(after.commitAccepted).not.toHaveBeenCalled()
  })

  it('retries a lost result with the identical sealed envelope and duplicate receipt', async () => {
    const s = await setup()
    s.api.push.mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ protocol_version: 2, encrypted_sync_version: 2,
      results: [{ event_id: id(2), server_sequence: 7, duplicate: true }], current_cursor: 7 })
    const subject = s.uploader()
    await expect(subject.uploadOnce('local')).rejects.toThrow('timeout')
    expect(s.commitAccepted).not.toHaveBeenCalled()
    await expect(subject.uploadOnce('local')).resolves.toEqual({ uploaded: 1, deviceId: DEVICE })
    expect(s.api.push.mock.calls[0]![1].items[0].object).toEqual(s.api.push.mock.calls[1]![1].items[0].object)
    expect(s.commitAccepted.mock.calls[0]![2][0].duplicate).toBe(true)
  })

  it('rejects malformed receipts and leaves native acceptance failures retryable', async () => {
    for (const response of [
      { protocol_version: 2, encrypted_sync_version: 2, results: [], current_cursor: 0 },
      { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(3), server_sequence: 1, duplicate: false }], current_cursor: 1 },
      { protocol_version: 2, encrypted_sync_version: 2, results: [{ event_id: id(2), server_sequence: 2, duplicate: false }], current_cursor: 1 },
    ]) {
      const s = await setup()
      s.api.push.mockResolvedValueOnce(response)
      await expect(s.uploader().uploadOnce('local')).rejects.toMatchObject({ code: 'malformed_receipt' })
      expect(s.commitAccepted).not.toHaveBeenCalled()
    }
    const native = await setup()
    native.commitAccepted.mockRejectedValueOnce(new Error('native failed'))
    await expect(native.uploader().uploadOnce('local')).rejects.toMatchObject({ code: 'local_acceptance_failed' })
    expect(native.recordUploadFailure).toHaveBeenCalledWith(expect.objectContaining({ error_code: 'local_acceptance_failed' }))
  })

  it('joins concurrent uploads in the same auth lifecycle', async () => {
    const s = await setup()
    let release!: () => void
    s.api.push.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve({ protocol_version: 2, encrypted_sync_version: 2,
      results: [{ event_id: id(2), server_sequence: 1, duplicate: false }], current_cursor: 1 }) }))
    const subject = s.uploader()
    const first = subject.uploadOnce('local')
    await vi.waitFor(() => expect(s.api.push).toHaveBeenCalledTimes(1))
    const second = subject.uploadOnce('local')
    release()
    await expect(Promise.all([first, second])).resolves.toEqual([{ uploaded: 1, deviceId: DEVICE }, { uploaded: 1, deviceId: DEVICE }])
    expect(s.api.push).toHaveBeenCalledTimes(1)
  })
})
